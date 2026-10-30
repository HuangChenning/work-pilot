#!/usr/bin/env python3
"""Local work records for the Work Pilot Lite skill.

The script uses the Python standard library and a new SQLite file. It does not
read calendars or send messages.
"""

import argparse
import datetime as dt
import json
import os
import sqlite3
import sys
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

VERSION = "0.1.0"
INTERFACE_VERSION = 1
SCHEMA_VERSION = 1
STATUSES = ("pending", "in_progress", "waiting", "completed", "cancelled", "paused")
PRIORITIES = ("low", "normal", "high", "urgent")
CLOSED = ("completed", "cancelled")
PRIORITY_RANK = {"urgent": 0, "high": 1, "normal": 2, "low": 3}
REASON_RANK = {"overdue": 0, "due_today": 1, "planned_today": 2}


class PilotError(Exception):
    code = "validation"


class Validation(PilotError):
    pass


class NotFound(PilotError):
    code = "not_found"


class Conflict(PilotError):
    code = "conflict"


def default_data_dir():
    if sys.platform == "win32":
        root = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        root = str(Path.home() / "Library" / "Application Support")
    else:
        root = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return str(Path(root) / "work-pilot-lite")


def stamp(value):
    return value.astimezone(dt.timezone.utc).replace(microsecond=0).isoformat()


def parse_rfc3339(value):
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError as exc:
        raise Validation("timestamp must be RFC3339 with a timezone") from exc
    if parsed.tzinfo is None:
        raise Validation("timestamp must include a timezone")
    return parsed


def parse_date(value):
    if value == "":
        return None
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise Validation("date must be YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise Validation("date must be YYYY-MM-DD")
    return parsed


def parse_clock(value):
    try:
        parsed = dt.datetime.strptime(value, "%H:%M")
    except ValueError as exc:
        raise Validation("clock must be HH:MM") from exc
    if parsed.strftime("%H:%M") != value:
        raise Validation("clock must be HH:MM")
    return value


def load_zone(name):
    if not name or name == "Local":
        raise Validation("timezone must be an IANA timezone")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as exc:
        raise Validation("timezone must be an IANA timezone") from exc


def wall_time(date_text, clock, zone_name):
    zone = load_zone(zone_name)
    naive = dt.datetime.strptime(f"{date_text} {clock}", "%Y-%m-%d %H:%M")
    first = naive.replace(tzinfo=zone, fold=0)
    second = naive.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise Validation(f"ambiguous local time {date_text} {clock} in {zone_name}")
    echoed = first.astimezone(dt.timezone.utc).astimezone(zone).strftime("%Y-%m-%d %H:%M")
    if echoed != f"{date_text} {clock}":
        raise Validation(f"nonexistent local time {date_text} {clock} in {zone_name}")
    return first


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def csv_list(value):
    return [part.strip() for part in value.split(",") if part.strip()]


def blank_config():
    return {
        "assistant_name": "Work Pilot",
        "timezone": "",
        "timezone_confirmed": False,
        "workdays": [],
        "workdays_confirmed": False,
    }


def normalize_task_input(fields):
    return {
        "title": (fields.get("title") or "").strip(),
        "description": fields.get("description") or "",
        "status": fields.get("status") or "pending",
        "priority": fields.get("priority") or "normal",
        "project": fields.get("project") or "",
        "tags": list(fields.get("tags") or []),
        "people": list(fields.get("people") or []),
        "due_date": fields.get("due_date") or "",
        "due_at": fields.get("due_at") or "",
        "plan_date": fields.get("plan_date") or "",
        "progress": fields.get("progress") or "",
        "next_action": fields.get("next_action") or "",
        "operation_id": fields.get("operation_id") or "",
    }


def validate_task_fields(task):
    if not task["title"].strip():
        raise Validation("title is required")
    if task["status"] not in STATUSES:
        raise Validation(f"unknown status {task['status']}")
    if task["priority"] not in PRIORITIES:
        raise Validation(f"unknown priority {task['priority']}")
    parse_date(task["due_date"])
    parse_date(task["plan_date"])
    if task["due_date"] and task["due_at"]:
        raise Validation("due_date and due_at are mutually exclusive")
    if task["due_at"]:
        parse_rfc3339(task["due_at"])
    if not isinstance(task["tags"], list) or not isinstance(task["people"], list):
        raise Validation("tags and people must be lists")


def deadline_on(task, zone_name):
    if task["due_date"]:
        return task["due_date"]
    if task["due_at"]:
        return parse_rfc3339(task["due_at"]).astimezone(load_zone(zone_name)).date().isoformat()
    return ""


def local_day(value, zone_name):
    return parse_rfc3339(value).astimezone(load_zone(zone_name)).date().isoformat()


class Store:
    def __init__(self, path, now=None):
        self.path = str(Path(path))
        self.now = now or (lambda: dt.datetime.now(dt.timezone.utc))
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        os.chmod(Path(self.path).parent, 0o700)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            self._initialize(connection)
        except Exception:
            connection.close()
            raise
        os.chmod(self.path, 0o600)
        self.conn = connection

    def close(self):
        self.conn.close()

    def _initialize(self, connection):
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            raise Validation("database is not a work-pilot-lite record file")
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        if version == 0 and tables:
            raise Validation("database is not a work-pilot-lite record file")
        if version == SCHEMA_VERSION:
            return
        connection.executescript(
            """
            CREATE TABLE config (id INTEGER PRIMARY KEY CHECK (id=1), data TEXT NOT NULL);
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                operation_id TEXT UNIQUE,
                creation_input TEXT NOT NULL,
                data TEXT NOT NULL
            );
            CREATE TABLE logs (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL REFERENCES tasks(id),
                data TEXT NOT NULL
            );
            CREATE TABLE reminders (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE reminder_acks (
                rule_id TEXT NOT NULL,
                occurrence TEXT NOT NULL,
                PRIMARY KEY (rule_id, occurrence)
            );
            CREATE TABLE reminder_skips (
                rule_id TEXT NOT NULL,
                occurrence TEXT NOT NULL,
                PRIMARY KEY (rule_id, occurrence)
            );
            """
        )
        connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
        connection.commit()

    def _write(self):
        self.conn.execute("BEGIN IMMEDIATE")

    def _finish(self):
        self.conn.commit()

    def _abort(self):
        self.conn.rollback()

    def config(self):
        row = self.conn.execute("SELECT data FROM config WHERE id=1").fetchone()
        if row is None:
            return blank_config()
        return json.loads(row["data"])

    def save_config(self, updates):
        current = self.config()
        if "assistant_name" in updates:
            name = (updates["assistant_name"] or "").strip()
            if not name:
                raise Validation("assistant name must not be empty")
            current["assistant_name"] = name
        if "timezone" in updates:
            load_zone(updates["timezone"])
            current["timezone"] = updates["timezone"]
            current["timezone_confirmed"] = True
        if "workdays" in updates:
            days = list(updates["workdays"])
            seen = set()
            for day in days:
                if not isinstance(day, int) or day < 1 or day > 7 or day in seen:
                    raise Validation("workdays must be unique ISO weekdays 1 through 7")
                seen.add(day)
            if not days:
                raise Validation("workdays must not be empty")
            current["workdays"] = days
            current["workdays_confirmed"] = True
        self._write()
        try:
            self.conn.execute(
                "INSERT INTO config(id, data) VALUES(1, ?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                (json.dumps(current, ensure_ascii=False),),
            )
            self._finish()
        except Exception:
            self._abort()
            raise
        return current

    def _require_timezone(self):
        config = self.config()
        if not config["timezone_confirmed"]:
            raise Validation("set a confirmed IANA timezone before dated queries")
        load_zone(config["timezone"])
        return config

    def add_task(self, fields):
        incoming = normalize_task_input(fields)
        validate_task_fields(incoming)
        created = stamp(self.now())
        self._write()
        try:
            if incoming["operation_id"]:
                existing = self.conn.execute(
                    "SELECT data, creation_input FROM tasks WHERE operation_id=?",
                    (incoming["operation_id"],),
                ).fetchone()
                if existing is not None:
                    if existing["creation_input"] != canonical(incoming):
                        raise Conflict("operation_id already used with different task input")
                    self._finish()
                    return json.loads(existing["data"])
            task = {
                "id": os.urandom(16).hex(),
                "title": incoming["title"],
                "description": incoming["description"],
                "status": incoming["status"],
                "priority": incoming["priority"],
                "project": incoming["project"],
                "tags": incoming["tags"],
                "people": incoming["people"],
                "due_date": incoming["due_date"],
                "due_at": incoming["due_at"],
                "plan_date": incoming["plan_date"],
                "progress": incoming["progress"],
                "next_action": incoming["next_action"],
                "created_at": created,
                "updated_at": created,
                "completed_at": created if incoming["status"] == "completed" else "",
                "version": 1,
            }
            self._insert_task(task, incoming["operation_id"], canonical(incoming))
            self._insert_log(task, "", incoming["progress"], "created")
            self._finish()
        except Exception:
            self._abort()
            raise
        return task

    def _insert_task(self, task, operation_id, creation_input):
        self.conn.execute(
            "INSERT INTO tasks(id, version, operation_id, creation_input, data) VALUES(?, ?, ?, ?, ?)",
            (task["id"], task["version"], operation_id or None, creation_input, json.dumps(task, ensure_ascii=False)),
        )

    def _insert_log(self, task, previous, content, reason):
        entry = {
            "id": os.urandom(16).hex(),
            "task_id": task["id"],
            "created_at": task["updated_at"],
            "content": content or "",
            "from_status": previous,
            "to_status": task["status"],
            "reason": reason or "",
        }
        self.conn.execute(
            "INSERT INTO logs(task_id, data) VALUES(?, ?)",
            (task["id"], json.dumps(entry, ensure_ascii=False)),
        )

    def _read_task(self, task_id):
        row = self.conn.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise NotFound("task not found")
        return json.loads(row["data"])

    def get_task(self, task_id):
        return self._read_task(task_id)

    def update_task(self, task_id, expected_version, fields):
        if expected_version < 1:
            raise Validation("expected version must be the version just read")
        changes = dict(fields)
        reason = changes.pop("reason", "")
        self._write()
        try:
            task = self._read_task(task_id)
            if task["version"] != expected_version:
                raise Conflict("task version conflict")
            previous = task["status"]
            for key in ("title", "description", "status", "priority", "project", "due_date", "due_at", "plan_date", "progress", "next_action"):
                if key in changes:
                    task[key] = changes[key] if changes[key] is not None else ""
            for key in ("tags", "people"):
                if key in changes:
                    task[key] = list(changes[key] or [])
            validate_task_fields(task)
            task["updated_at"] = stamp(self.now())
            task["version"] += 1
            if "status" in changes:
                task["completed_at"] = task["updated_at"] if task["status"] == "completed" else ""
            self.conn.execute(
                "UPDATE tasks SET version=?, data=? WHERE id=?",
                (task["version"], json.dumps(task, ensure_ascii=False), task["id"]),
            )
            self._insert_log(task, previous, changes.get("progress", ""), reason)
            self._finish()
        except Exception:
            self._abort()
            raise
        return task

    def list_tasks(self, status="", query="", include_closed=False):
        result = []
        needle = query.lower()
        for task in self._tasks():
            if status and task["status"] != status:
                continue
            if not status and not include_closed and task["status"] in CLOSED:
                continue
            if needle:
                haystack = " ".join([
                    task["title"], task["description"], task["progress"], task["next_action"],
                    task["project"], " ".join(task["tags"]), " ".join(task["people"]),
                ]).lower()
                if needle not in haystack:
                    continue
            result.append(task)
        result.sort(key=lambda item: (item["created_at"], item["id"]))
        return result

    def _tasks(self):
        rows = self.conn.execute("SELECT data FROM tasks").fetchall()
        return [json.loads(row["data"]) for row in rows]

    def logs(self, task_id):
        self._read_task(task_id)
        rows = self.conn.execute("SELECT data FROM logs WHERE task_id=? ORDER BY seq", (task_id,)).fetchall()
        return [json.loads(row["data"]) for row in rows]

    def agenda(self, date):
        config = self._require_timezone()
        parse_date(date)
        items = []
        backlog = []
        for task in self.list_tasks():
            if task["status"] == "paused":
                backlog.append(task)
                continue
            due = deadline_on(task, config["timezone"])
            if due and due < date:
                reason = "overdue"
            elif due == date and due:
                reason = "due_today"
            elif task["plan_date"] == date:
                reason = "planned_today"
            else:
                reason = ""
            if reason:
                items.append({"task": task, "reason": reason})
            else:
                backlog.append(task)
        items.sort(key=lambda item: (
            REASON_RANK[item["reason"]],
            deadline_on(item["task"], config["timezone"]),
            item["task"]["due_at"],
            PRIORITY_RANK[item["task"]["priority"]],
            item["task"]["created_at"],
            item["task"]["id"],
        ))
        backlog.sort(key=lambda item: (item["created_at"], item["id"]))
        workday = None
        if config["workdays_confirmed"]:
            workday = parse_date(date).isoweekday() in config["workdays"]
        return {"date": date, "timezone": config["timezone"], "is_workday": workday, "tasks": items, "backlog": backlog}

    def summary(self, date):
        config = self._require_timezone()
        parse_date(date)
        completed = []
        unfinished = []
        activities = []
        for task in self.list_tasks(include_closed=True):
            if task["status"] == "completed" and task["completed_at"] and local_day(task["completed_at"], config["timezone"]) == date:
                completed.append(task)
            elif task["status"] not in CLOSED:
                unfinished.append(task)
            for entry in self.logs(task["id"]):
                if local_day(entry["created_at"], config["timezone"]) != date:
                    continue
                changed = entry["from_status"] and entry["from_status"] != entry["to_status"]
                if entry["content"] or changed:
                    activities.append({"task": task, "log": entry})
        completed.sort(key=lambda item: item["completed_at"])
        return {"date": date, "timezone": config["timezone"], "completed": completed, "activities": activities, "unfinished": unfinished}

    def add_reminder(self, fields):
        kind = fields.get("kind")
        if kind not in ("once", "weekly"):
            raise Validation("reminder kind must be once or weekly")
        zone_name = fields.get("timezone") or ""
        load_zone(zone_name)
        rule = {
            "id": os.urandom(16).hex(),
            "kind": kind,
            "title": (fields.get("title") or "").strip(),
            "body": fields.get("body") or "",
            "timezone": zone_name,
            "enabled": True if fields.get("enabled") is None else bool(fields.get("enabled")),
            "created_at": stamp(self.now()),
            "at": "",
            "task_id": fields.get("task_id") or "",
            "start_date": fields.get("start_date") or "",
            "time": fields.get("time") or "",
            "weekdays": list(fields.get("weekdays") or []),
            "end_date": fields.get("end_date") or "",
        }
        if kind == "once":
            if not rule["at"] and not fields.get("at"):
                raise Validation("one-shot reminder requires at")
            rule["at"] = stamp(parse_rfc3339(fields["at"]))
            if not rule["title"] and not rule["task_id"]:
                raise Validation("one-shot reminder requires a title or task")
            if rule["task_id"]:
                self._read_task(rule["task_id"])
        else:
            parse_date(rule["start_date"])
            if rule["start_date"] == "":
                raise Validation("weekly reminder requires start_date")
            rule["time"] = parse_clock(rule["time"])
            seen = set()
            for day in rule["weekdays"]:
                if not isinstance(day, int) or day < 1 or day > 7 or day in seen:
                    raise Validation("weekdays must be unique ISO weekdays")
                seen.add(day)
            if not seen:
                raise Validation("weekly reminder requires weekdays")
            if rule["end_date"]:
                parse_date(rule["end_date"])
                if rule["end_date"] < rule["start_date"]:
                    raise Validation("reminder end date is before the start date")
            if not rule["title"]:
                raise Validation("weekly reminder requires a title")
        self._write()
        try:
            self.conn.execute("INSERT INTO reminders(id, data) VALUES(?, ?)", (rule["id"], json.dumps(rule, ensure_ascii=False)))
            self._finish()
        except Exception:
            self._abort()
            raise
        return rule

    def list_reminders(self):
        rules = []
        for row in self.conn.execute("SELECT data FROM reminders ORDER BY id"):
            rule = json.loads(row["data"])
            acks = [item[0] for item in self.conn.execute("SELECT occurrence FROM reminder_acks WHERE rule_id=? ORDER BY occurrence", (rule["id"],))]
            rule["acked"] = acks
            rules.append(rule)
        return rules

    def _rule(self, rule_id):
        row = self.conn.execute("SELECT data FROM reminders WHERE id=?", (rule_id,)).fetchone()
        if row is None:
            raise NotFound("reminder not found")
        return json.loads(row["data"])

    def set_reminder_enabled(self, rule_id, enabled):
        self._write()
        try:
            rule = self._rule(rule_id)
            rule["enabled"] = bool(enabled)
            self.conn.execute("UPDATE reminders SET data=? WHERE id=?", (json.dumps(rule, ensure_ascii=False), rule_id))
            self._finish()
        except Exception:
            self._abort()
            raise
        return rule

    def _acked(self, rule_id, occurrence):
        row = self.conn.execute(
            "SELECT 1 FROM reminder_acks WHERE rule_id=? AND occurrence=?",
            (rule_id, occurrence),
        ).fetchone()
        return row is not None

    def _skipped(self, rule_id, occurrence):
        row = self.conn.execute(
            "SELECT 1 FROM reminder_skips WHERE rule_id=? AND occurrence=?",
            (rule_id, occurrence),
        ).fetchone()
        return row is not None

    def _task_by_operation(self, operation_id):
        row = self.conn.execute("SELECT data FROM tasks WHERE operation_id=?", (operation_id,)).fetchone()
        if row is None:
            return None
        return json.loads(row["data"])

    def check_reminders(self, at):
        if at.tzinfo is None:
            raise Validation("check instant must include a timezone")
        self._require_timezone()
        due = []
        created = []
        missed = []
        truncated = False
        self._write()
        try:
            rules = [json.loads(row["data"]) for row in self.conn.execute("SELECT data FROM reminders")]
            for rule in rules:
                if not rule["enabled"]:
                    continue
                if rule["kind"] == "once":
                    item = self._once_due(rule, at)
                    if item is not None:
                        due.append(item)
                    continue
                made, gaps, flag = self._weekly_check(rule, at)
                created.extend(made)
                missed.extend(gaps)
                truncated = truncated or flag
                due.extend(self._weekly_due(rule, at))
            self._finish()
        except Exception:
            self._abort()
            raise
        due.sort(key=lambda item: (item["reason"], item["rule_id"]))
        return {"due": due, "created_tasks": created, "missed_dates": missed, "truncated": truncated}

    def _once_due(self, rule, at):
        moment = parse_rfc3339(rule["at"])
        if at < moment or self._acked(rule["id"], rule["at"]):
            return None
        if rule["task_id"]:
            task = self._read_task(rule["task_id"])
            if task["status"] in CLOSED:
                return None
        return {
            "rule_id": rule["id"],
            "kind": "once",
            "occurrence": rule["at"],
            "title": rule["title"],
            "body": rule["body"],
            "task_id": rule["task_id"],
            "reason": "once:" + rule["at"],
        }

    def _weekly_passed(self, rule, at):
        local_today = at.astimezone(load_zone(rule["timezone"])).date()
        start = parse_date(rule["start_date"])
        end = local_today
        if rule["end_date"]:
            end = min(end, parse_date(rule["end_date"]))
        dates = []
        day = start
        steps = 0
        while day <= end:
            steps += 1
            if steps > 36600:
                raise Validation("recurrence range exceeds 100 years")
            if day.isoweekday() in rule["weekdays"]:
                moment = wall_time(day.isoformat(), rule["time"], rule["timezone"])
                if moment <= at:
                    dates.append(day.isoformat())
            day += dt.timedelta(days=1)
        return dates

    def _weekly_check(self, rule, at):
        passed = self._weekly_passed(rule, at)
        missing = []
        for day in passed:
            operation = f"reminder:{rule['id']}:{day}"
            if self._task_by_operation(operation) is None and not self._skipped(rule["id"], day):
                missing.append(day)
        chosen = missing[-8:]
        older = missing[:-8]
        created = []
        for day in chosen:
            created.append(self._create_occurrence(rule, day, at))
        gaps = []
        for day in older:
            self.conn.execute(
                "INSERT INTO reminder_skips(rule_id, occurrence) VALUES(?, ?)",
                (rule["id"], day),
            )
            gaps.append({"rule_id": rule["id"], "date": day})
        return created, gaps, bool(older)

    def _create_occurrence(self, rule, day, at):
        operation = f"reminder:{rule['id']}:{day}"
        created_at = stamp(at)
        incoming = normalize_task_input({"title": rule["title"], "plan_date": day, "operation_id": operation})
        task = {
            "id": os.urandom(16).hex(),
            "title": incoming["title"],
            "description": "",
            "status": "pending",
            "priority": "normal",
            "project": "",
            "tags": [],
            "people": [],
            "due_date": "",
            "due_at": "",
            "plan_date": day,
            "progress": "",
            "next_action": "",
            "created_at": created_at,
            "updated_at": created_at,
            "completed_at": "",
            "version": 1,
        }
        self._insert_task(task, operation, canonical(incoming))
        self._insert_log(task, "", "", "created")
        return task

    def _weekly_due(self, rule, at):
        items = []
        for day in self._weekly_passed(rule, at):
            task = self._task_by_operation(f"reminder:{rule['id']}:{day}")
            if task is None or task["status"] in CLOSED or self._acked(rule["id"], day):
                continue
            items.append({
                "rule_id": rule["id"],
                "kind": "weekly",
                "occurrence": day,
                "title": rule["title"],
                "body": rule["body"],
                "task_id": task["id"],
                "reason": "weekly:" + day,
            })
        return items

    def ack_reminder(self, rule_id, occurrence, at):
        if at.tzinfo is None:
            raise Validation("ack instant must include a timezone")
        self._write()
        try:
            rule = self._rule(rule_id)
            key = self._ack_key(rule, occurrence, at)
            self.conn.execute(
                "INSERT INTO reminder_acks(rule_id, occurrence) VALUES(?, ?) ON CONFLICT(rule_id, occurrence) DO NOTHING",
                (rule_id, key),
            )
            self._finish()
        except Exception:
            self._abort()
            raise
        return {"id": rule_id, "occurrence": key, "acked": True}

    def _ack_key(self, rule, occurrence, at):
        if rule["kind"] == "once":
            moment = parse_rfc3339(occurrence)
            if moment != parse_rfc3339(rule["at"]):
                raise NotFound("reminder occurrence not found")
            if moment > at:
                raise Validation("future reminder cannot be acknowledged")
            return rule["at"]
        day = parse_date(occurrence)
        if day is None or day.isoformat() != occurrence:
            raise NotFound("reminder occurrence not found")
        if day.isoweekday() not in rule["weekdays"]:
            raise NotFound("reminder occurrence not found")
        if occurrence < rule["start_date"] or (rule["end_date"] and occurrence > rule["end_date"]):
            raise NotFound("reminder occurrence not found")
        moment = wall_time(occurrence, rule["time"], rule["timezone"])
        if moment > at:
            raise Validation("future reminder cannot be acknowledged")
        return occurrence


def split_global(argv):
    data_dir = None
    rest = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--data-dir":
            if index + 1 >= len(argv):
                raise Validation("--data-dir requires a path")
            data_dir = argv[index + 1]
            index += 2
            continue
        if item.startswith("--data-dir="):
            data_dir = item.split("=", 1)[1]
            index += 1
            continue
        rest.append(item)
        index += 1
    return data_dir, rest


def run(argv, stdout=None):
    output = stdout or sys.stdout
    try:
        data_dir, rest = split_global(argv)
        if not rest or rest[0] in ("help", "-h", "--help"):
            payload = {"usage": "python3 work_pilot.py [--data-dir PATH] COMMAND", "commands": [
                "version", "config show|set", "task add|get|list|update|logs",
                "agenda --date YYYY-MM-DD", "summary --date YYYY-MM-DD",
                "reminder add|list|check|ack|update",
            ]}
            write_ok(output, payload)
            return 0
        if rest[0] == "version":
            write_ok(output, {"version": VERSION, "interface_version": INTERFACE_VERSION, "edition": "lite"})
            return 0
        path = str(Path(data_dir or default_data_dir()) / "records.db")
        store = Store(path)
        try:
            write_ok(output, dispatch(store, rest))
        finally:
            store.close()
        return 0
    except PilotError as exc:
        write_error(output, exc.code, str(exc))
        return 1
    except Exception as exc:
        write_error(output, "validation", str(exc))
        return 1


def dispatch(store, rest):
    command = rest[0]
    if command == "config":
        return config_command(store, rest[1:])
    if command == "task":
        return task_command(store, rest[1:])
    if command == "agenda":
        return dated(store.agenda, rest[1:], "agenda")
    if command == "summary":
        return dated(store.summary, rest[1:], "summary")
    if command == "reminder":
        return reminder_command(store, rest[1:])
    raise Validation(f"unknown command {command}")


def dated(method, args, name):
    parser = argparse.ArgumentParser(prog=name, add_help=False)
    parser.add_argument("--date", required=True)
    parsed = parser.parse_args(args)
    return method(parsed.date)


def config_command(store, args):
    if not args:
        raise Validation("config requires show or set")
    if args[0] == "show" and len(args) == 1:
        return store.config()
    if args[0] != "set":
        raise Validation("config requires show or set")
    parser = argparse.ArgumentParser(prog="config set", add_help=False)
    parser.add_argument("--assistant-name")
    parser.add_argument("--timezone")
    parser.add_argument("--workdays")
    parsed = parser.parse_args(args[1:])
    updates = {}
    if parsed.assistant_name is not None:
        updates["assistant_name"] = parsed.assistant_name
    if parsed.timezone is not None:
        updates["timezone"] = parsed.timezone
    if parsed.workdays is not None:
        try:
            updates["workdays"] = [int(part) for part in csv_list(parsed.workdays)]
        except ValueError as exc:
            raise Validation("workdays must be comma-separated numbers 1 through 7") from exc
    if not updates:
        raise Validation("no configuration changes specified")
    return store.save_config(updates)


def task_command(store, args):
    if not args:
        raise Validation("task requires add, get, list, update, or logs")
    action = args[0]
    if action == "add":
        parser = argparse.ArgumentParser(prog="task add", add_help=False)
        for name in ("title", "description", "status", "priority", "project", "tags", "people", "due-date", "due-at", "plan-date", "progress", "next-action", "operation-id"):
            parser.add_argument("--" + name)
        parsed = parser.parse_args(args[1:])
        fields = {
            "title": parsed.title or "",
            "description": parsed.description or "",
            "status": parsed.status or "",
            "priority": parsed.priority or "",
            "project": parsed.project or "",
            "due_date": getattr(parsed, "due_date") or "",
            "due_at": getattr(parsed, "due_at") or "",
            "plan_date": getattr(parsed, "plan_date") or "",
            "progress": parsed.progress or "",
            "next_action": getattr(parsed, "next_action") or "",
            "operation_id": getattr(parsed, "operation_id") or "",
            "tags": csv_list(parsed.tags or ""),
            "people": csv_list(parsed.people or ""),
        }
        return store.add_task(fields)
    if action == "list":
        parser = argparse.ArgumentParser(prog="task list", add_help=False)
        parser.add_argument("--status", default="")
        parser.add_argument("--query", default="")
        parser.add_argument("--include-closed", action="store_true")
        parsed = parser.parse_args(args[1:])
        return store.list_tasks(parsed.status, parsed.query, parsed.include_closed)
    if action in ("get", "logs"):
        parser = argparse.ArgumentParser(prog="task " + action, add_help=False)
        parser.add_argument("--id", required=True)
        parsed = parser.parse_args(args[1:])
        return store.get_task(parsed.id) if action == "get" else store.logs(parsed.id)
    if action == "update":
        parser = argparse.ArgumentParser(prog="task update", add_help=False)
        parser.add_argument("--id", required=True)
        parser.add_argument("--expected-version", required=True, type=int)
        optional = ("title", "description", "status", "priority", "project", "tags", "people", "due-date", "due-at", "plan-date", "progress", "next-action", "reason")
        for name in optional:
            parser.add_argument("--" + name)
        parsed = parser.parse_args(args[1:])
        fields = {}
        mapping = {
            "title": "title", "description": "description", "status": "status", "priority": "priority",
            "project": "project", "due_date": "due_date", "due_at": "due_at", "plan_date": "plan_date",
            "progress": "progress", "next_action": "next_action", "reason": "reason",
        }
        for attr, key in mapping.items():
            value = getattr(parsed, attr)
            if value is not None:
                fields[key] = value
        if parsed.tags is not None:
            fields["tags"] = csv_list(parsed.tags)
        if parsed.people is not None:
            fields["people"] = csv_list(parsed.people)
        if not any(key != "reason" for key in fields):
            raise Validation("no task changes specified")
        return store.update_task(parsed.id, parsed.expected_version, fields)
    raise Validation(f"unknown task action {action}")


def reminder_command(store, args):
    if not args:
        raise Validation("reminder requires add, list, check, ack, or update")
    action = args[0]
    if action == "list" and len(args) == 1:
        return store.list_reminders()
    if action == "add":
        parser = argparse.ArgumentParser(prog="reminder add", add_help=False)
        parser.add_argument("--kind", required=True)
        parser.add_argument("--title", default="")
        parser.add_argument("--body", default="")
        parser.add_argument("--timezone", required=True)
        parser.add_argument("--at")
        parser.add_argument("--task-id")
        parser.add_argument("--start-date")
        parser.add_argument("--time")
        parser.add_argument("--weekdays")
        parser.add_argument("--end-date")
        parser.add_argument("--disabled", action="store_true")
        parsed = parser.parse_args(args[1:])
        weekdays = []
        if parsed.weekdays is not None:
            try:
                weekdays = [int(part) for part in csv_list(parsed.weekdays)]
            except ValueError as exc:
                raise Validation("weekdays must be comma-separated numbers 1 through 7") from exc
        return store.add_reminder({
            "kind": parsed.kind,
            "title": parsed.title,
            "body": parsed.body,
            "timezone": parsed.timezone,
            "at": parsed.at,
            "task_id": parsed.task_id,
            "start_date": parsed.start_date,
            "time": parsed.time,
            "weekdays": weekdays,
            "end_date": parsed.end_date,
            "enabled": not parsed.disabled,
        })
    if action == "check":
        parser = argparse.ArgumentParser(prog="reminder check", add_help=False)
        parser.add_argument("--at")
        parsed = parser.parse_args(args[1:])
        moment = parse_rfc3339(parsed.at) if parsed.at else dt.datetime.now(dt.timezone.utc)
        return store.check_reminders(moment)
    if action == "ack":
        parser = argparse.ArgumentParser(prog="reminder ack", add_help=False)
        parser.add_argument("--id", required=True)
        parser.add_argument("--occurrence", required=True)
        parser.add_argument("--at")
        parsed = parser.parse_args(args[1:])
        moment = parse_rfc3339(parsed.at) if parsed.at else dt.datetime.now(dt.timezone.utc)
        return store.ack_reminder(parsed.id, parsed.occurrence, moment)
    if action == "update":
        parser = argparse.ArgumentParser(prog="reminder update", add_help=False)
        parser.add_argument("--id", required=True)
        parser.add_argument("--enabled", required=True, choices=("true", "false"))
        parsed = parser.parse_args(args[1:])
        return store.set_reminder_enabled(parsed.id, parsed.enabled == "true")
    raise Validation(f"unknown reminder action {action}")


def write_ok(output, payload):
    json.dump({"ok": True, "data": payload}, output, ensure_ascii=False, indent=2)
    output.write("\n")


def write_error(output, code, message):
    json.dump({"ok": False, "error": {"code": code, "message": message}}, output, ensure_ascii=False, indent=2)
    output.write("\n")


def main(argv):
    sys.exit(run(argv))


if __name__ == "__main__":
    main(sys.argv[1:])
