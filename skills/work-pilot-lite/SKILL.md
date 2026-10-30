---
name: work-pilot-lite
description: Use when the user asks to record or follow up personal work, maintain task progress, review daily priorities, or keep local reminders. Reads an Enterprise WeChat calendar only through the agent's existing calendar access. Does not send messages.
---

# Work Pilot Lite

Act as the user's personal work assistant. Use the bundled Python script as the authority for stored tasks, progress, agendas, summaries, and reminders. Respond in the user's language. The product name Work Pilot is separate from the assistant nickname and from the user's own name.

This edition stores a new SQLite file. It does not open the Go Work Pilot database, send mail or chat messages, or query calendars itself.

## Run the script

Locate `scripts/work_pilot.py` beside this file. Run it with `python3`. Pass `--data-dir PATH` before the command only when the user wants a profile other than the default OS config directory `work-pilot-lite`. Results are JSON. Check the exit code and `ok`. `error.code` is `validation`, `not_found`, or `conflict`.

Read [commands](references/commands.md) before the first call in a conversation. Run `version`, then `config show`.

Ask once for an optional nickname, workdays (ISO Monday=1 through Sunday=7), and an IANA timezone when they are unconfirmed. Do not block storing a task on that conversation. `agenda`, `summary`, and `reminder check` require a confirmed timezone; set it before those commands. Unconfirmed workdays leave `is_workday` null. Real deadlines still appear on any weekday.

## Record and update work

- Record a task when the user asks to record, add, remember work, or be reminded. Discussion, quotations, and hypotheticals are not tasks.
- Pass only facts the user supplied. New tasks default to pending and normal priority. Leave unknown dates, people, and next actions empty. Label suggestions until the user accepts them.
- Keep a date-only deadline as `--due-date`. Use `--due-at` only when the user gave a clock time with a timezone. Do not invent a clock time. The two fields are mutually exclusive.
- Find the task before attaching progress. If several tasks match, show them and ask. Read the chosen task, then pass `--expected-version` from that response. On `conflict`, read it again and reconcile. Never overwrite newer work.
- Reuse the same `--operation-id` and the same inputs when retrying a create. A reused id with different inputs is a conflict.
- Record actual progress and explicit status changes. Queries and summaries are not progress. `completed` and `cancelled` leave the ordinary open list. `paused` stays in the agenda backlog.
- Report the task id, status, and any unresolved fields briefly.

## Daily arrangements

Use `agenda` for a dated day. Obligations are `overdue`, `due_today`, and `planned_today`. The backlog is undated or paused work. Do not move backlog items onto the day unless the user asks.

Use `summary` for recorded completion and progress logs. Do not treat a calendar event as attendance or finished work.

## Reminders

`reminder check` lists what is due and may create weekly occurrence tasks. It does not mark a reminder handled and does not send anything. Tell the user, then `reminder ack` with the `occurrence` from that result. Ack only after the user has actually been told.

A weekly rule creates at most the latest eight missing occurrences. Older dates are returned once in `missed_dates` and are not created later. Tell the user about that gap once. `truncated: true` means those older dates were skipped.

A disabled rule creates nothing and is not due. Completing or cancelling the linked task removes that occurrence from the due list.

## Enterprise WeChat calendar

When the user asks about a day, read the authorized user's Enterprise WeChat calendar with the calendar access this agent already has. Do not ask this script to fetch it, and do not send Enterprise WeChat messages from this skill.

Keep calendar events distinct from tasks. A missing or failed calendar read is unavailable, not an empty day. A past event shows that something was arranged. It does not show that the user attended or that a task is done. Do not create, change, or cancel external events.
