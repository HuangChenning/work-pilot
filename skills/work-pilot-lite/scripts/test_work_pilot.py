import datetime as dt
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import work_pilot


def clock(value):
    return lambda: value


class LiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / "records.db")
        self.now = dt.datetime(2026, 10, 30, 2, 0, tzinfo=dt.timezone.utc)
        self.store = work_pilot.Store(self.path, now=clock(self.now))
        self.store.save_config({"timezone": "Asia/Shanghai", "workdays": [1, 2, 3, 4, 5]})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_date_only_deadline_becomes_overdue_the_next_day(self):
        task = self.store.add_task({"title": "Report", "due_date": "2026-10-30"})
        self.assertEqual(task["due_at"], "")
        today = self.store.agenda("2026-10-30")
        self.assertEqual(today["tasks"][0]["reason"], "due_today")
        tomorrow = self.store.agenda("2026-10-31")
        self.assertEqual(tomorrow["tasks"][0]["reason"], "overdue")

    def test_due_at_uses_saved_timezone(self):
        self.store.add_task({"title": "Late", "due_at": "2026-10-29T23:30:00+08:00"})
        self.store.add_task({"title": "Morning", "due_at": "2026-10-30T00:30:00+08:00"})
        reasons = {item["task"]["title"]: item["reason"] for item in self.store.agenda("2026-10-30")["tasks"]}
        self.assertEqual(reasons["Late"], "overdue")
        self.assertEqual(reasons["Morning"], "due_today")

    def test_agenda_keeps_undated_and_paused_work_in_the_backlog(self):
        self.store.add_task({"title": "Someday"})
        paused = self.store.add_task({"title": "Paused", "due_date": "2026-10-01"})
        self.store.update_task(paused["id"], paused["version"], {"status": "paused"})
        agenda = self.store.agenda("2026-10-30")
        self.assertEqual(agenda["tasks"], [])
        self.assertEqual({task["title"] for task in agenda["backlog"]}, {"Someday", "Paused"})

    def test_version_conflict_does_not_write(self):
        task = self.store.add_task({"title": "Report"})
        with self.assertRaises(work_pilot.Conflict):
            self.store.update_task(task["id"], task["version"] + 3, {"title": "Changed"})
        self.assertEqual(self.store.get_task(task["id"])["title"], "Report")
        self.assertEqual(self.store.get_task(task["id"])["version"], 1)

    def test_operation_id_replays_the_same_input_and_rejects_a_different_one(self):
        first = self.store.add_task({"title": "Report", "operation_id": "op-1"})
        second = self.store.add_task({"title": "Report", "operation_id": "op-1"})
        self.assertEqual(first["id"], second["id"])
        with self.assertRaises(work_pilot.Conflict):
            self.store.add_task({"title": "Other", "operation_id": "op-1"})

    def test_summary_uses_recorded_completion_only(self):
        task = self.store.add_task({"title": "Report", "due_date": "2026-10-30"})
        self.store.update_task(task["id"], 1, {"status": "completed", "progress": "Sent"})
        summary = self.store.summary("2026-10-30")
        self.assertEqual([item["title"] for item in summary["completed"]], ["Report"])
        self.assertTrue(any(item["log"]["content"] == "Sent" for item in summary["activities"]))
        self.assertNotIn("calendar", summary)

    def test_check_does_not_ack_and_weekly_create_is_idempotent(self):
        rule = self.store.add_reminder({
            "kind": "weekly",
            "title": "Friday note",
            "timezone": "Asia/Shanghai",
            "start_date": "2026-10-30",
            "time": "09:00",
            "weekdays": [5],
        })
        at = dt.datetime.fromisoformat("2026-10-30T10:00:00+08:00")
        first = self.store.check_reminders(at)
        second = self.store.check_reminders(at)
        self.assertEqual(len(first["created_tasks"]), 1)
        self.assertEqual(first["created_tasks"][0]["plan_date"], "2026-10-30")
        self.assertEqual(second["created_tasks"], [])
        self.assertEqual(len(first["due"]), 1)
        self.assertEqual(len(second["due"]), 1)
        self.assertEqual(first["due"][0]["reason"], "weekly:2026-10-30")
        self.assertEqual(first["due"][0]["task_id"], first["created_tasks"][0]["id"])
        created = first["created_tasks"][0]
        self.store.update_task(created["id"], created["version"], {"status": "completed"})
        self.assertEqual(self.store.check_reminders(at)["due"], [])
        self.store.ack_reminder(rule["id"], "2026-10-30", at)
        self.assertEqual(self.store.check_reminders(at)["due"], [])

    def test_weekly_check_keeps_only_the_latest_eight_and_remembers_older_gaps(self):
        self.store.add_reminder({
            "kind": "weekly",
            "title": "Friday note",
            "timezone": "Asia/Shanghai",
            "start_date": "2026-01-02",
            "time": "09:00",
            "weekdays": [5],
        })
        at = dt.datetime.fromisoformat("2026-10-30T10:00:00+08:00")
        fridays = []
        day = dt.date(2026, 1, 2)
        while day <= dt.date(2026, 10, 30):
            fridays.append(day.isoformat())
            day += dt.timedelta(days=7)
        first = self.store.check_reminders(at)
        self.assertTrue(first["truncated"])
        self.assertEqual(len(first["created_tasks"]), 8)
        self.assertEqual(
            [item["plan_date"] for item in first["created_tasks"]],
            fridays[-8:],
        )
        self.assertEqual([item["date"] for item in first["missed_dates"]], fridays[:-8])
        second = self.store.check_reminders(at)
        self.assertFalse(second["truncated"])
        self.assertEqual(second["missed_dates"], [])
        self.assertEqual(second["created_tasks"], [])
        self.assertEqual(len(self.store.list_tasks(include_closed=True)), 8)

    def test_cli_rejects_a_go_database_and_returns_json(self):
        profile = Path(self.tmp.name) / "go-profile"
        profile.mkdir()
        connection = sqlite3.connect(profile / "records.db")
        connection.execute("PRAGMA user_version=2")
        connection.commit()
        connection.close()
        output = io.StringIO()
        code = work_pilot.run(["--data-dir", str(profile), "config", "show"], output)
        self.assertEqual(code, 1)
        payload = json.loads(output.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "validation")


if __name__ == "__main__":
    unittest.main()
