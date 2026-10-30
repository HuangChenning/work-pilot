# Work Pilot

[简体中文](README.zh-CN.md) · [v0.2.0 packages](https://github.com/HuangChenning/work-pilot/releases/tag/v0.2.0)

A personal work assistant for AI Agents: keep task history, prepare daily plans, and follow up on unfinished work through a local CLI.

## Overview

Work Pilot combines a portable Agent Skill with a Go CLI and a local SQLite database. It supports persistent tasks and progress, daily agendas, summaries, Markdown archives, backups, and explicitly configured calendar and reminder integrations. One person can use the same local records across Agents.

**v0.2.0 validation:** macOS Apple Silicon has been run natively. Official wecom-cli personal calendar reads (ordinary, weekly and monthly occurrences) and one authorized personal message have passed live acceptance. The other four platform binaries are cross-compiled; other live integrations, unattended scheduling, edited/cancelled calendar exceptions and real GitHub data handoff still need acceptance.

## Example: record a task, then find it in the agenda

Use the `WP_BIN` path from the installation below. This example creates an isolated temporary profile; the date is sample data.

```sh
WP_DEMO_DATA="$(mktemp -d)"
"$WP_BIN" --data-dir "$WP_DEMO_DATA" config set \
  --timezone Asia/Shanghai --workdays 1,2,3,4,5
"$WP_BIN" --data-dir "$WP_DEMO_DATA" task add \
  --title "Prepare project report" \
  --due-date 2026-11-06 --operation-id readme-report
"$WP_BIN" --data-dir "$WP_DEMO_DATA" agenda \
  --date 2026-11-06
```

The agenda includes **Prepare project report** with `reason: "due_today"`. The task stores `due_date: "2026-11-06"` and an empty `due_at`: a date-only deadline keeps its precision. This record-and-query sequence has been smoke-tested on macOS arm64.

In conversation, ask the Agent to record a task, append progress, query today's agenda, or mark an explicitly completed task. Unscheduled work stays in a separate backlog. Commands return JSON; errors return `ok: false` and a nonzero exit code.

## How it works

<!-- diagram-decision: prose-only | reason: A three-row ownership table directly explains the Agent, CLI and storage boundaries; a flow diagram would duplicate that information and obscure the separate authorization of external integrations. -->

| Component | Responsibility |
| --- | --- |
| Agent Skill | Interpret requests, clarify ambiguity, distinguish facts from suggestions, and explain results. |
| Go CLI | Validate explicit inputs, calculate dates, query and update records, and execute configured operations. |
| Local SQLite database | Hold authoritative personal configuration, tasks, progress, and execution state. |

Personal data lives outside the Skill installation. Generated `todo.md` and `archive/YYYY/MM.md` files are regenerable views; edits to them do not write back to the database. Reminders use one-shot checks and dispatch commands invoked by the host scheduler. No separate daemon is included.

## Getting started

Download your archive and `CHECKSUMS.txt` from [v0.2.0](https://github.com/HuangChenning/work-pilot/releases/tag/v0.2.0). Each archive includes both READMEs, a CLI, and a `skill/` directory with the matching Skill, references, and nested platform binary.

| Platform | Archive |
| --- | --- |
| macOS Apple Silicon | `work-pilot-0.2.0-darwin-arm64.tar.gz` |
| macOS Intel | `work-pilot-0.2.0-darwin-amd64.tar.gz` |
| Linux arm64 | `work-pilot-0.2.0-linux-arm64.tar.gz` |
| Linux amd64 | `work-pilot-0.2.0-linux-amd64.tar.gz` |
| Windows amd64 | `work-pilot-0.2.0-windows-amd64.zip` |

### macOS or Linux

For a **new Codex installation** with no existing `work-pilot` Skill directory, the macOS arm64 example is:

```sh
shasum -a 256 work-pilot-0.2.0-darwin-arm64.tar.gz
# Compare the digest with CHECKSUMS.txt before extracting.
mkdir work-pilot-0.2.0
tar -xzf work-pilot-0.2.0-darwin-arm64.tar.gz -C work-pilot-0.2.0
mkdir -p "$HOME/.codex/skills"
cp -R work-pilot-0.2.0/skill "$HOME/.codex/skills/work-pilot"
WP_SKILL_DIR="$HOME/.codex/skills/work-pilot"
WP_BIN="$WP_SKILL_DIR/bin/darwin-arm64/work-pilot"
"$WP_BIN" version
"$WP_BIN" capabilities
"$WP_BIN" install register --path "$WP_SKILL_DIR"
```

Substitute the archive and `bin/<platform>/` path for your platform. Linux can use `sha256sum` for the digest. Other Agents use their own supported Skill directory; register its absolute path. Reload the Agent session after installing the Skill.

### Windows

Compare `Get-FileHash -Algorithm SHA256` with `CHECKSUMS.txt`, extract the ZIP, and copy `skill/` into your Agent's Skill directory. For a new Codex installation in PowerShell:

```powershell
Expand-Archive .\work-pilot-0.2.0-windows-amd64.zip .\work-pilot-0.2.0
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse .\work-pilot-0.2.0\skill "$HOME\.codex\skills\work-pilot"
$WP_SKILL_DIR = "$HOME\.codex\skills\work-pilot"
$WP_BIN = "$WP_SKILL_DIR\bin\windows-amd64\work-pilot.exe"
& $WP_BIN version
& $WP_BIN install register --path $WP_SKILL_DIR
```

On first use, confirm your timezone and working days; optionally name the assistant. Optional calendar or channel setup does not block ordinary task recording. The default profile uses the OS user configuration directory under `work-pilot`; pass `--data-dir PATH` before the command to select another profile.

## Connect external calendars

The examples below use the installed `WP_BIN` and a POSIX shell (macOS/Linux). Keep connection JSON and secrets outside the Skill and this repository. For example:

```sh
WP_CONFIG_DIR="$HOME/.config/work-pilot-connections"
mkdir -p "$WP_CONFIG_DIR"
"$WP_BIN" config set --timezone Asia/Shanghai --workdays 1,2,3,4,5
```

Choose your actual timezone and workdays. On Windows, use an absolute configuration directory, set secrets as `$env:VARIABLE = 'VALUE'`, and invoke the executable with `& $WP_BIN`; the JSON format is identical. Environment variables must reach the process running Work Pilot, including any later scheduler.

<details>
<summary><strong>macOS Calendar: authorize the helper, then select calendars</strong></summary>

At the stable Skill installation path, run the helper matching your Mac:

```sh
WP_BRIDGE="$WP_SKILL_DIR/references/native/darwin-arm64/work-pilot-eventkit"
"$WP_BRIDGE" authorize
"$WP_BRIDGE" list-calendars
```

Intel Macs use `darwin-amd64`. Accept the macOS calendar permission prompt, then choose IDs from the returned metadata. macOS requires calendar access permission; Work Pilot only reads events. If denied, review Calendar access in System Settings → Privacy & Security. The helper is not Developer ID notarized; native authorization still needs acceptance on your machine.

Save this as `calendars.json` in your configuration directory, replacing both placeholders with the **absolute helper path** and chosen calendar ID. JSON does not expand `$HOME` or shell variables.

```json
{
  "sources": [{
    "id": "mac-calendar",
    "kind": "macos",
    "calendar_ids": ["SELECTED_CALENDAR_ID"],
    "bridge_path": "/absolute/skill/path/references/native/darwin-arm64/work-pilot-eventkit"
  }]
}
```

</details>

<details>
<summary><strong>Google Calendar: supply a read-only OAuth access token</strong></summary>

Enable Calendar API in your Google Cloud project, configure OAuth consent/client credentials, and complete user authorization through your own OAuth client. Use an event-reading scope such as:

```text
https://www.googleapis.com/auth/calendar.events.readonly
```

Free/busy-only and calendar-metadata-only scopes cannot read event details. See [Google's scope guide](https://developers.google.com/workspace/calendar/api/auth) and [OAuth setup guide](https://developers.google.com/workspace/guides/configure-oauth-consent).

Set the resulting **access token**, not a client secret, API key or refresh token:

```sh
export WORK_PILOT_GOOGLE_TOKEN='YOUR_OAUTH_ACCESS_TOKEN'
```

Save as `calendars.json`; `primary` selects the authorized account's primary calendar. For another calendar, use its calendar ID from Google Calendar settings and ensure the account can read it.

```json
{
  "sources": [{
    "id": "google-work",
    "kind": "google",
    "calendar_ids": ["primary"],
    "token_env": "WORK_PILOT_GOOGLE_TOKEN"
  }]
}
```

v0.2.0 has no built-in OAuth login or token refresh. Your external OAuth client must refresh expired access tokens and provide the new value to Work Pilot; exporting a token once does not establish unattended access.

</details>

<details>
<summary><strong>Enterprise WeChat calendar: supply an application token and cal_id</strong></summary>

Ask your enterprise administrator to prepare an application with access to the relevant calendar API, obtain its application `access_token` through the enterprise's credential workflow, and provide the selected calendar's `cal_id`. The adapter reads **calendars created by, and accessible to, that application**; it cannot promise access to your ordinary personal calendar. Enterprise WeChat calendar authorization is separate from a group robot Webhook.

```sh
export WORK_PILOT_WECOM_TOKEN='YOUR_APPLICATION_ACCESS_TOKEN'
```

```json
{
  "sources": [{
    "id": "wecom-work",
    "kind": "wecom",
    "calendar_ids": ["APPLICATION_CAL_ID"],
    "token_env": "WORK_PILOT_WECOM_TOKEN"
  }]
}
```

Save as `calendars.json`. Token acquisition/renewal is external; existing Agent/plugin login is not automatically reused. Recurring events and all-day normalization are unsupported in this adapter. If your application lacks the required access, use a supported ICS export instead of assuming an empty result means no events.

</details>

<details>
<summary><strong>Linux/Windows local calendars: read an exported ICS file</strong></summary>

Export the chosen calendar to a local `.ics` file using your calendar application, then save:

```json
{
  "sources": [{
    "id": "local-export",
    "kind": "ics",
    "calendar_ids": ["work"],
    "ics_files": {"work": "/absolute/path/work.ics"}
  }]
}
```

Windows paths can use `C:/Users/YOU/Calendars/work.ics` or escaped backslashes. The exporter must expand recurring events; Work Pilot does not expand ICS recurrence rules or watch calendar applications. Refresh the export when the calendar changes.

</details>

For multiple connections, combine only the configured source objects in one `sources` array, each with a unique `id`. Verify a bounded period containing a known event, using actual dates and timezone offsets:

```sh
"$WP_BIN" calendar query --config "$WP_CONFIG_DIR/calendars.json" \
  --from 2026-11-06T00:00:00+08:00 --to 2026-11-07T00:00:00+08:00
"$WP_BIN" agenda --date 2026-11-06 \
  --calendar-config "$WP_CONFIG_DIR/calendars.json"
```

Check the exit code, `ok`, `incomplete`, and each source's `verified`, `missing` and `synced_at`. Compare a known event's title, time and timezone with the calendar application. An authorization error or unverified cache is not a successful empty-calendar check. These commands do not create, modify or cancel external events.

## Send email or chat reminders

v0.2.0 sends messages through **reminder dispatch**, not a general-purpose `send` command. Start with one explicitly authorized destination and an isolated test profile so that no existing queued reminders are sent accidentally.

### 1. Prepare one channel

For email, obtain your provider's SMTP host/port, permitted sender address and SMTP credentials or app password. OAuth-only SMTP authentication is not implemented. Use STARTTLS (commonly port587) or direct TLS (`tls`, commonly port465), following your provider's settings.

```sh
export WORK_PILOT_SMTP_USER='YOUR_SMTP_USERNAME'
export WORK_PILOT_SMTP_PASSWORD='YOUR_SMTP_APP_PASSWORD'
```

Save `$WP_CONFIG_DIR/channels.json`, replacing the example addresses and server:

```json
{
  "channels": [{
    "id": "test-channel",
    "channel": "email",
    "target": "me@example.com",
    "target_kind": "self",
    "authorized": true,
    "endpoint": "smtp.example.com:587",
    "from": "me@example.com",
    "username_env": "WORK_PILOT_SMTP_USER",
    "password_env": "WORK_PILOT_SMTP_PASSWORD",
    "tls_mode": "starttls"
  }]
}
```

For chat, create a custom group robot in the explicitly selected group and obtain its Webhook. Use this **instead of** the email channel above:

```sh
export WORK_PILOT_CHAT_WEBHOOK='YOUR_GROUP_ROBOT_HTTPS_WEBHOOK'
```

```json
{
  "channels": [{
    "id": "test-channel",
    "channel": "wecom",
    "target": "NAME_OF_AUTHORIZED_GROUP",
    "target_kind": "group",
    "authorized": true,
    "additional_authorization": true,
    "endpoint_env": "WORK_PILOT_CHAT_WEBHOOK"
  }]
}
```

Use `wecom`, `feishu` or `dingtalk` for `channel`, matching that service's Webhook. `target` labels the reviewed group; the actual group is determined by the Webhook, so verify both. For email to someone else, use `target_kind: "other"` with `additional_authorization: true` after obtaining that authorization. Boolean flags record consent; they do not obtain it.

Robot security policies still apply. For example, if an allowed keyword is required, include that keyword in the reminder's title/body; configure any IP allowlist for the actual sending host. Signed Feishu/DingTalk modes are unsupported. If your organization requires signatures or forbids custom robots, that channel is unavailable with v0.2.0. See the official [Feishu robot guide](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot) and [DingTalk robot guide](https://open.dingtalk.com/document/robots/custom-robot-access) for service setup. A calendar token does not authorize robot messages, and robot Webhooks do not read calendars.

### 2. Save a one-shot test rule and preview it

This uses Python3 only to generate a timestamp for immediate testing. Substitute your actual timezone. Keep the printed profile path to inspect the outcome later.

```sh
WP_TEST_DATA="$(mktemp -d)"
printf '%s\n' "$WP_TEST_DATA"
"$WP_BIN" --data-dir "$WP_TEST_DATA" config set \
  --timezone Asia/Shanghai --workdays 1,2,3,4,5 \
  --device-id connection-test --reminder-device-id connection-test
python3 - <<'PYRULE' > "$WP_CONFIG_DIR/test-rule.json"
import datetime, json
print(json.dumps({
    "kind": "once", "title": "Work Pilot connection test",
    "body": "One explicitly authorized connection test.",
    "timezone": "Asia/Shanghai", "channel_id": "test-channel",
    "at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "expires_after_minutes": 10, "authorized": True, "enabled": True
}))
PYRULE
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder save \
  --file "$WP_CONFIG_DIR/test-rule.json"
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch
```

Preview persists due reasons but sends nothing. It does not validate SMTP/Webhook credentials. Inspect the saved rule, selected channel and target before continuing. Change the body if your robot requires a keyword. If more than ten minutes pass, create a new reviewed test rule rather than changing the check clock to force an expired notification.

### 3. Send once, then verify the result

The next command performs a **real external send** to the configured destination:

```sh
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch \
  --channels "$WP_CONFIG_DIR/channels.json" --send
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder deliveries
```

On Windows, create the same JSON files, choose an isolated `$WP_TEST_DATA` directory, and use `& $WP_BIN --data-dir $WP_TEST_DATA ...`. Set SMTP/Webhook environment variables in that PowerShell session before dispatch.

`sent` means the service accepted the message; confirm it in the inbox/group. `failed` means a definite failure; fix credentials, recipient or service policy and explicitly authorize a new test. `unknown` or an interrupted `claimed` delivery needs investigation before another send; do not blindly retry. v0.2.0 has no automatic delivery reconciliation/retry command. An empty `attempts` list is not proof of delivery: inspect rule time, expiry, quiet hours, authorization and reminder-device settings.

After this succeeds, configure reviewed rules in your normal profile. For unattended operation, separately configure the Agent host, launchd, systemd/cron or Windows Task Scheduler to run `reminder dispatch --channels ABSOLUTE_CHANNELS_PATH --send` with the same absolute CLI path, data directory and credentials. Each run checks due rules before dispatch. Saving a rule or setting morning/evening preferences does not install that schedule; the host must be running and tokens must remain valid. See the [full configuration reference](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/configuration.md) for recurring rules, quiet hours and other channel fields.

## Capabilities and acceptance limits

- **Local records:** tasks, progress logs, state history, filtered queries, daily agendas and summaries; date-only and exact-time deadlines stay distinct. Markdown export, monthly completion archives, trash/restore, and consistent local backup/restore are implemented and locally tested.
- **Read-only calendars:** Google Calendar, enterprise WeChat app-created calendars, official wecom-cli personal schedules, ICS files, and a macOS native helper. The official CLI connector reads service-expanded recurring instances; the legacy app-calendar connector does not expand recurrence. macOS requires native calendar permission; Linux and Windows can use supported ICS sources rather than arbitrary calendar apps. Official wecom-cli ordinary/weekly/monthly reads have passed live acceptance; other accounts and native calendar access still need acceptance.
- **Reminders:** saved rules, recurrence, quiet hours, durable delivery states, and designated-device checks. Host scheduling is configured separately; saving a rule does not start a schedule. Official wecom-cli one-shot personal delivery has passed live acceptance; unattended execution and other channels still need acceptance.
- **Notifications:** SMTP email and enterprise WeChat, Feishu, and DingTalk group webhooks are fixture-tested. Official wecom-cli recent-conversation Markdown delivery has passed a live personal-message test. Signed webhook robot modes are unsupported. Each target needs explicit authorization. Unknown send outcomes are preserved without blind automatic retries.
- **Optional GitHub backup:** a separate private data repository supports snapshots and sequential device handoff with conflict checks. Fixture-tested; no real remote acceptance yet. Concurrent offline edits are not automatically merged, and handoff does not enable a second reminder device.

A failed calendar source is reported as missing or unverified; an absent event is not assumed cancelled. A saved rule, an enabled host schedule, and confirmed delivery are separate states. Calendar events and related preparation tasks keep independent statuses.

## Official wecom-cli integration

**v0.2.0** includes personal calendar reads and authorized recent-conversation Markdown messages through official [wecom-cli](https://github.com/WecomTeam/wecom-cli), version **1.3.4 or newer**. Use the installed `WP_BIN`, then check `version` and `capabilities` for `calendar.wecom_cli` and `notify.wecom_cli`. The connector completed one authorized live message test on macOS arm64, with service acceptance and recipient-confirmed receipt. Live read-only acceptance also verified ordinary, weekly and monthly schedule instances, including times, timezone, participants and stable identities across overlapping queries.

### 1. Configure authorization and environment

Install the official native executable separately; Windows requires `.exe`, rather than a `.cmd`/`.bat` wrapper. Choose one authorization method:

- **Authorized directory:** run the official `wecom-cli auth init` yourself, then reuse that profile under the same OS user. The default directory is `~/.config/wecom`.
- **Official token:** inject `WECOM_CLI_ACCESS_TOKEN` through the Agent/scheduler's secret environment. It overrides stored credentials; replace it when it expires.

Work Pilot uses these fixed variable names:

| Variable | Configuration |
| --- | --- |
| `WORK_PILOT_WECOM_CLI_PATH` | Optional absolute path to the official native executable; defaults to `wecom-cli` on PATH. |
| `WECOM_CLI_ACCESS_TOKEN` | Official Bearer token; optional when using an authorized directory. |
| `WECOM_CLI_CONFIG_DIR` | Optional absolute authorized profile directory; defaults to `~/.config/wecom`. |
| `WECOM_CLI_ADDITIONAL_HEADERS` | Optional JSON object of string-valued request headers. |
| `WECOM_CLI_ADDITIONAL_HEADERS_*` | Optional additional header objects using official suffix semantics. |

For an already authorized profile on macOS/Linux:

```sh
export WORK_PILOT_WECOM_CLI_PATH="/absolute/path/to/wecom-cli"
export WECOM_CLI_CONFIG_DIR="$HOME/.config/wecom"
WP_CONFIG_DIR="$HOME/.config/work-pilot-connections"
mkdir -p "$WP_CONFIG_DIR"
"$WP_BIN" wecom status
```

For PowerShell:

```powershell
$env:WORK_PILOT_WECOM_CLI_PATH = 'C:\Tools\wecom-cli.exe'
$env:WECOM_CLI_CONFIG_DIR = "$HOME\.config\wecom"
$WP_CONFIG_DIR = "$HOME\.config\work-pilot-connections"
New-Item -ItemType Directory -Force -Path $WP_CONFIG_DIR | Out-Null
& $WP_BIN wecom status
```

In token mode, inject the token into the same process environment instead of copying it into JSON or shared transcripts. Additional headers are normally unnecessary; if required, their value must be valid JSON such as `{"X-Tenant":"your-tenant"}`. Work Pilot does not read project `.env` files or accept Bot ID/Secret initialization variables. The Agent and any scheduler must inherit the selected environment. Keep credentials and connection files outside this repository and the Skill installation.

`authorized_material: true` confirms local material exists; `remote_validity: "not_checked"` means server validity and permissions still need a requested read. Work Pilot does not initialize authorization automatically; official wecom-cli may refresh stored credentials or migrate legacy profiles during startup.

### 2. Configure the personal calendar

Save as `$WP_CONFIG_DIR/wecom-calendars.json`. Set `account_timezone` to the authorized account's actual IANA timezone:

```json
{
  "sources": [{
    "id": "wecom-personal",
    "kind": "wecom-cli",
    "calendar_ids": ["authorized-user"],
    "account_timezone": "Asia/Shanghai"
  }]
}
```

```sh
"$WP_BIN" calendar query --config "$WP_CONFIG_DIR/wecom-calendars.json" \
  --from 2026-10-30T00:00:00+08:00 --to 2026-10-31T00:00:00+08:00
"$WP_BIN" agenda --date 2026-10-30 \
  --calendar-config "$WP_CONFIG_DIR/wecom-calendars.json"
```

Replace the example dates with a range within the current time ±30 days. Only the authorized user's personal schedule is supported; keep `calendar_ids` exactly `["authorized-user"]`. Timed ordinary and recurring schedules are supported when the official list returns their individual occurrences, including weekly meetings. Work Pilot preserves each returned occurrence’s actual time and assigns a distinct identity; it does not expand recurrence rules again. Missing timezone/participant metadata is read from series details without replacing occurrence times with the series start date. Rescheduled or omitted instances follow the service response. All-day events, ambiguous DST times or incomplete responses make the source unavailable/incomplete. This connector bypasses persistent calendar caching after account changes. It reads schedules without creating tasks or modifying external calendars.

### 3. Review and bind a message destination

Resolve a unique exact recent conversation name; use `group` for a group or `other` for a personal conversation:

```sh
"$WP_BIN" wecom target --name "Reviewed team group" --kind group
```

This command reads recent sessions and returns an opaque `authorization_binding`; it sends nothing and does not grant consent. After reviewing and authorizing the destination, save `$WP_CONFIG_DIR/wecom-channels.json`, replacing the name and binding:

```json
{
  "channels": [{
    "id": "wecom-reviewed",
    "channel": "wecom-cli",
    "target": "Reviewed team group",
    "target_kind": "group",
    "authorized": true,
    "additional_authorization": true,
    "authorization_binding": "REPLACE_WITH_RETURNED_BINDING"
  }]
}
```

Both groups and other people require explicit additional authorization. A self-destination shortcut is unavailable. Each send resolves the conversation again and verifies its identity and credential binding. Duplicate/missing names fail. Token rotation, credential refresh/reauthorization, profile/header changes or a replaced conversation may require reviewing the target again and replacing its binding.

### 4. Preview, send and schedule

Use the one-shot test procedure under **Send email or chat reminders**, changing the rule's `channel_id` from `test-channel` to `wecom-reviewed`. Save it in the isolated `WP_TEST_DATA` profile, then inspect the preview. The command with `--send` below performs a **real external send** and requires an authorized reminder plan:

```sh
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch \
  --channels "$WP_CONFIG_DIR/wecom-channels.json" --send
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder deliveries
```

On Windows use `& $WP_BIN` and the same JSON files. For unattended use, configure the host scheduler separately with the same absolute executable/data/config paths, authorization environment and designated reminder device. Saving a rule or channel does not start a schedule.

Markdown messages are limited to 20,480 UTF-8 bytes including the subject; oversized content fails without splitting. `sent` means service acceptance, so verify actual receipt. Investigate `unknown` or interrupted `claimed` outcomes before another attempt. See the [integration reference](skills/work-pilot/references/wecom-cli.md) for the upstream baseline and detailed limits.

## Updates and reference

```sh
"$WP_BIN" update check
"$WP_BIN" update --version 0.2.0
```

Explicit updates check platform, checksums, compatibility, and local Skill edits, then update the CLI and registered Skill locations. Reload sessions that already loaded old instructions. Windows self-update is deferred to manual installation; replace the installed package manually and register its path again. Existing v0.1.0 installations can use the explicit v0.2.0 update command above to update the CLI and registered Skill together.

See the [command reference](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/commands.md) for exact syntax, task versions, calendar configuration, and reminder preview/send boundaries; see [setup notes](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/setup.md) for authorization, scheduling, and recovery. The [configuration examples](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/configuration.md) cover calendar, reminder, channel, and handoff JSON.
