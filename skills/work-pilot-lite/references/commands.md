# Commands

Run `python3` on `scripts/work_pilot.py`. Put `--data-dir PATH` before the command. The default profile is the OS user config directory plus `work-pilot-lite`, in `records.db`. Output is one JSON object. Failure is `ok: false`, a nonzero exit, and `error.code` of `validation`, `not_found`, or `conflict`.

```text
python3 work_pilot.py version
python3 work_pilot.py config show
python3 work_pilot.py config set --timezone Asia/Shanghai --workdays 1,2,3,4,5
python3 work_pilot.py config set --assistant-name Pilot
python3 work_pilot.py task add --title "Prepare weekly report" --due-date 2026-11-06 --operation-id OPERATION_ID
python3 work_pilot.py task list --query report
python3 work_pilot.py task get --id TASK_ID
python3 work_pilot.py task update --id TASK_ID --expected-version 1 --progress "Draft reviewed"
python3 work_pilot.py task update --id TASK_ID --expected-version 2 --status completed --reason "User confirmed delivery"
python3 work_pilot.py task logs --id TASK_ID
python3 work_pilot.py agenda --date 2026-11-06
python3 work_pilot.py summary --date 2026-11-06
python3 work_pilot.py reminder add --kind once --title "Review the draft" --timezone Asia/Shanghai --at 2026-11-06T09:00:00+08:00
python3 work_pilot.py reminder add --kind weekly --title "Friday note" --timezone Asia/Shanghai --start-date 2026-11-06 --time 09:00 --weekdays 5
python3 work_pilot.py reminder list
python3 work_pilot.py reminder check
python3 work_pilot.py reminder ack --id RULE_ID --occurrence OCCURRENCE
python3 work_pilot.py reminder update --id RULE_ID --enabled false
```

Dates in the examples are not the user's commitments. Task ids and versions come from earlier responses. Workdays are ISO numbers: Monday=1 through Sunday=7.

## Tasks

Statuses: `pending`, `in_progress`, `waiting`, `completed`, `cancelled`, `paused`. Priorities: `low`, `normal`, `high`, `urgent`. Omitted status and priority become `pending` and `normal`.

`--due-date YYYY-MM-DD` and `--due-at` (RFC3339 with a timezone) are mutually exclusive. A date-only deadline is due on that date and overdue on the next calendar date in the saved timezone. `--plan-date` is the day the user intends to do the work.

`task list` hides `completed` and `cancelled` unless `--include-closed` is set or `--status` selects one of them. `--query` is a case-insensitive substring over title, description, progress, next action, project, tags, and people. `--tags` and `--people` are comma-separated.

`task update` requires `--id` and `--expected-version`. Flags that are omitted stay unchanged. An explicit empty value clears a text field. To switch deadline precision, set the new field and clear the old one in the same update.

`--operation-id` retries a create. The same id and the same inputs return the original task. The same id with different inputs returns `conflict`.

`agenda` returns `tasks` with `reason` of `overdue`, `due_today`, or `planned_today`, plus a separate `backlog`. Paused tasks stay in the backlog. `is_workday` is null until workdays are confirmed.

`summary` returns tasks completed on that local date, progress logs from that date, and unfinished tasks. It has no calendar input.

`agenda`, `summary`, and `reminder check` fail with `validation` until `config set --timezone` has been used.

## Reminders

`once` requires `--at` and either `--title` or `--task-id`. `weekly` requires `--title`, `--start-date`, `--time HH:MM`, and `--weekdays`. Optional `--end-date` bounds a weekly rule. `--disabled` stores the rule without making it due.

`reminder check` uses the current time, or `--at` when an explicit RFC3339 instant is required. It can create weekly tasks. It does not ack and does not send. Each created task has `plan_date` set to that occurrence and operation id `reminder:<rule_id>:<YYYY-MM-DD>`.

The check result contains:

- `due`: unacked occurrences. Weekly reasons look like `weekly:YYYY-MM-DD`. One-shot reasons look like `once:<stored at>`.
- `created_tasks`: tasks created by this check only.
- `missed_dates`: `{rule_id, date}` objects for older weekly dates that will not be created. Each date is listed once.
- `truncated`: true when this check recorded any of those older dates.

A weekly check creates at most the latest eight missing occurrences. A completed or cancelled linked task is not due. `reminder ack` copies `occurrence` from `due`. Acking the same occurrence again succeeds. A future or unknown occurrence does not ack.

`reminder update --enabled false` stops new occurrences and removes the rule from `due`. `reminder list` includes an `acked` list of occurrence keys.
