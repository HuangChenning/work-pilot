# Integration configuration

Keep these files outside the Skill and program repository. Examples are templates: replace paths, IDs and destinations with explicitly selected values. Setting authorization flags only records consent already obtained from the user.

## Calendars

A calendar file has a `sources` array and optional `aliases`. Each source needs a unique `id`, `kind` and explicit `calendar_ids`. Supported kinds:

| Kind | Connection fields | Boundary |
| --- | --- | --- |
| `google` | `token_env` | Existing access token with calendar read permission; OAuth acquisition/refresh is external. |
| `wecom` | `token_env` | Existing app access token; app-created calendars accessible to that app. Recurrence and all-day normalization are not supported. |
| `macos` | absolute `bridge_path` | macOS 13+, full EventKit calendar consent, selected calendar identifiers. |
| `ics` | `ics_files` mapping identifiers to absolute files | Local exported ICS files on any platform; recurring events must be expanded by the exporter. |

```json
{"sources":[{"id":"local-export","kind":"ics","calendar_ids":["work"],"ics_files":{"work":"/absolute/path/work.ics"}}]}
```

Linux and Windows local calendars currently use ICS exports; direct native application/database adapters are not included. macOS helpers are installed at `references/native/darwin-<arch>/work-pilot-eventkit`. At a stable absolute installation path, explicitly run the selected helper's `authorize` command, accept the system prompt, then `list-calendars` to choose identifiers. Reading calendar metadata does not select calendars automatically. Configure only selected identifiers and the absolute helper path. Helpers are locally signed build artifacts, without Developer ID notarization; distribution/native authorization acceptance remains separate from compilation.

Query with `calendar query --config FILE --from RFC3339 --to RFC3339`. Use `agenda --date YYYY-MM-DD --calendar-config FILE` to combine records. Query failures retain source-labelled unverified results; they never establish cancellation.

## Reminder rule files

All rules require `kind`, explicit IANA `timezone`, `channel_id`, and reviewed `authorized`/`enabled` booleans. Omit `id` for a new rule; use the returned `id` to revise that rule. `revision` and `effective_at` are maintained by the CLI. `Local` is not a portable timezone.

| Kind | Required scheduling fields |
| --- | --- |
| `once` | `at` RFC3339; optionally `task_id`, otherwise `title` or `body`. |
| `subscription` | `title` or `body`, `start_date`, `time`, `frequency`. Does not create tasks. |
| `recurrence` | `start_date`, `time`, `frequency`, `task_template` containing at least `title`. Each occurrence creates a separate task. |
| `due` | Optional `task_id` scope, optional `lead_minutes`; reads task deadlines. |
| `overdue` | Optional `task_id` scope; reads actual unfinished deadlines. |
| `followup` | `task_id` and explicit `follow_up_date` or `at`; optional `time`. |
| `stale` | Positive `stale_days`; stale checking also needs `config set --stale-check-enabled=true`. Periodic reviews may supply recurrence fields. |

`frequency` is `daily`, `weekly` (requires unique ISO `weekdays`, Monday=1) or `monthly` (requires `month_day` 1–31). Date strings are YYYY-MM-DD; clocks are HH:MM. Optional `end_date` bounds recurrence; nonexistent monthly dates are skipped. `task_template` accepts ordinary new-task fields, but excludes fixed dates and operation IDs because each occurrence determines those. Closed template states are invalid.

```json
{"kind":"subscription","title":"Morning review","timezone":"Asia/Shanghai","channel_id":"my-mail","authorized":true,"enabled":true,"start_date":"2026-11-01","time":"09:00","frequency":"weekly","weekdays":[1,2,3,4,5],"quiet_hours":{"start":"22:00","end":"08:00"}}
```

Optional policy fields: `workdays_only`, `quiet_hours` with both `start`/`end`, `expires_at` RFC3339, `expires_after_minutes`, and `bypass_quiet` together with `bypass_quiet_authorized`. Confirm dates and quiet-hour policy with the user. `reminder check` and preview dispatch persist reasons; they do not send or install schedules. Configure a unique `device_id` and matching `reminder_device_id` before dispatch. Unknown/interrupted deliveries are retained and never automatically retried; v0.1 has no automatic reconciliation command for them.

## Delivery channels

An email example (credentials are environment references):

```json
{"channels":[{"id":"my-mail","channel":"email","target":"me@example.com","target_kind":"self","authorized":true,"endpoint":"smtp.example.com:587","from":"me@example.com","username_env":"WORK_PILOT_SMTP_USER","password_env":"WORK_PILOT_SMTP_PASSWORD","tls_mode":"starttls"}]}
```

Group robot example:

```json
{"channels":[{"id":"team-robot","channel":"wecom","target":"Explicitly selected work group","target_kind":"group","authorized":true,"additional_authorization":true,"endpoint_env":"WORK_PILOT_WECOM_WEBHOOK"}]}
```

Other robot `channel` values are `feishu` and `dingtalk`. These are group webhooks, not personal chat connectors; signed Feishu/DingTalk modes are not implemented. Use only a robot configured compatibly with its service security settings. SMTP uses verified STARTTLS or direct `tls`; plaintext is restricted to loopback fixtures. `timeout_seconds` is optional. `sent` means service acceptance, not proof of user reading or inbox arrival. No automatic retry, fallback or multi-channel fan-out is configured by these examples.

## Separate private GitHub data repository

```json
{"owner":"YOUR_ACCOUNT","repository":"YOUR_PRIVATE_DATA_REPO","token_env":"WORK_PILOT_DATA_TOKEN"}
```

The token needs read/write access to this specific private repository. Do not use the program repository. Snapshots are sanitized logical JSON, not encrypted backups; repository readers can read work records. Machine credentials, calendar tokens and channel secrets stay local. Snapshot size is bounded; this is sequential handoff, not concurrent synchronization.

On the first device, set `config set --device-id DEVICE_A`, then `handoff push --config FILE`. Later `push` backs up current records; `pull` refuses divergent state. To switch devices, run `handoff release --config FILE` on the owner. It becomes read-only. On a new, empty data directory, run `handoff acquire --config FILE --device-id DEVICE_B` before saving preferences or tasks. Acquisition restores work but does not transfer reminder authority; explicitly configure the new device afterward. Devices with existing unrelated data are refused rather than overwritten.

Run `handoff status` to inspect local ownership. A network-uncertain transition remains pending/read-only; `handoff reconcile --config FILE` compares durable remote identities. Do not delete state files, force ownership or merge snapshots to bypass a conflict.
