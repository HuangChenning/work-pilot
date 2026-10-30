# CLI contract

Run the platform binary's `help` and `capabilities` to discover current commands. Pass `--data-dir PATH` before the command when using an explicitly selected profile. Output is JSON and `ok: false` accompanies a nonzero exit. Commands below are implemented in v0.2.0; other subsystems are available only when listed by the installed binary.

```text
work-pilot version
work-pilot capabilities
work-pilot config show
work-pilot config set --assistant-name Pilot --timezone Asia/Shanghai --workdays 1,2,3,4,5
work-pilot task add --title "Prepare weekly report" --due-date 2026-11-06 --operation-id OPERATION_ID
work-pilot task list --query report
work-pilot task get --id TASK_ID
work-pilot task update --id TASK_ID --expected-version 1 --progress "Draft reviewed"
work-pilot task update --id TASK_ID --expected-version 2 --status completed --reason "User confirmed delivery"
work-pilot task logs --id TASK_ID
work-pilot agenda --date 2026-11-06
work-pilot summary --date 2026-11-06
work-pilot export --dir VIEW_DIRECTORY
work-pilot backup --dest NEW_SNAPSHOT_PATH
work-pilot restore --source SNAPSHOT_PATH --confirm
work-pilot task delete --id TASK_ID --confirm
work-pilot task restore --id TASK_ID
work-pilot task purge --id TASK_ID --confirm
```

Dates are examples, not user commitments. Task IDs and expected versions come from actual responses. Workdays use ISO numbers: Monday=1 through Sunday=7. Task states are `pending`, `in_progress`, `waiting`, `completed`, `cancelled`, `paused`; priorities are `low`, `normal`, `high`, `urgent`.

`--due-date YYYY-MM-DD` and `--due-at RFC3339` are mutually exclusive. `--plan-date` is the date the user intends to work, separate from a deadline. To change precision, explicitly clear the old field in the same update. Unspecified update flags preserve existing values; an explicit empty value clears a scalar.

Task-list filters include status, project, tag, person, priority, source, keywords, deadline `--from`/`--to`, `--include-closed` and `--include-deleted`. Prefer stable identities after retrieval. A keyword match is not permission to merge tasks.

A task update requires a positive `--expected-version`, preventing an old Agent view from overwriting newer work. An `--operation-id` reused with different input is a conflict. After an uncertain creation response, retry with the same operation ID and original inputs.

Recovery/deletion `--confirm` flags express authorization already obtained from the user's instruction. They do not grant broader deletion or external-send scope.

## Calendars

```text
work-pilot calendar query --config CALENDARS_JSON --from 2026-11-06T00:00:00+08:00 --to 2026-11-07T00:00:00+08:00
work-pilot agenda --date 2026-11-06 --calendar-config CALENDARS_JSON
```

The configuration lists explicit `sources` with `id`, `kind`, `calendar_ids`, and connection details. Google/WeCom use a `token_env` reference; ICS uses an `ics_files` calendar-ID-to-path map; macOS uses an absolute `bridge_path` to the bundled native helper. No token values belong in this file. Known identity aliases use `from`/`to` objects with `source_id`, `calendar_id`, `event_id`.

A partial result has `incomplete: true` and per-source `verified`, `missing`, `synced_at` and error fields. `unverified_events` are not current facts or cancelled events. `possible_duplicates` are suggestions, separate from reliable identity deduplication.

## Reminder rules and one-shot checks

```text
work-pilot config set --device-id DEVICE --reminder-device-id DEVICE
work-pilot reminder save --file REVIEWED_RULE_JSON
work-pilot reminder list
work-pilot reminder check
work-pilot reminder deliveries
work-pilot reminder dispatch
work-pilot reminder dispatch --channels CHANNELS_JSON --send
```

`check` persists due reasons and recurrence instances without sending. `dispatch` defaults to preview; `--send` executes sends only for authorized rules and authorized channel targets on the designated device. These commands do not install a host schedule. `--at RFC3339` intentionally changes the check instant and may generate corresponding period records; use only for an explicitly requested historical/recovery check.

A taskless reminder rule includes its title/body. For example, after user authorization:

```json
{
  "kind": "once",
  "title": "Review the draft",
  "body": "Read the recorded materials",
  "timezone": "Asia/Shanghai",
  "channel_id": "personal-mail",
  "at": "2026-11-06T09:00:00+08:00",
  "authorized": true,
  "enabled": true
}
```

A rule file is a reviewed plan, not proof of consent by itself. Supported rule kinds are once, subscription, due, overdue, stale, followup and recurrence. Read [configuration](configuration.md) before adding complex periodic rules; do not guess required fields.

Channels are stored outside the Skill as a JSON `channels` list. Each entry declares `id`, `channel` (email/wecom/feishu/dingtalk), `target`, `target_kind` (self/group/other), `authorized` and, for groups/other people, `additional_authorization`. Resolve webhook endpoints through `endpoint_env`; SMTP may use an ordinary host:port `endpoint`, `from`, `username_env`, `password_env`, and `tls_mode` (starttls/tls). `timeout_seconds` is optional. Credentials and webhook secrets stay in environment variables. Unknown outcomes stay terminal until reconciled; the CLI does not automatically retry or switch channels.

## Installation registration and online upgrade

```text
work-pilot install register --path INSTALLED_WORK_PILOT_SKILL_DIRECTORY
work-pilot install list
work-pilot update check
work-pilot update check --version 0.2.0
work-pilot update --version 0.2.0
```

Registration records an existing installation; first copy the verified release's Skill folder into the Agent's supported skills location. It does not enable reminders. No version is downloadable until a Release has actually been published. An explicit update refreshes the running CLI and registered Skill locations, subject to compatibility, checksum and local-edit checks. Windows may return a deferred manual-install result while files remain unchanged; report that outcome as deferred, not upgraded.


## Official wecom-cli

Read [wecom-cli integration](wecom-cli.md) before authorization, personal calendar queries or recent-conversation sends. `wecom status` checks local material; `wecom target --name EXACT_NAME --kind group|other` resolves a destination binding without sending. All commands remain subject to installed capabilities.
