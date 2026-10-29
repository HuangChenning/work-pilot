# Work Pilot

[简体中文](README.zh-CN.md) · [v0.1.0 packages](https://github.com/HuangChenning/work-pilot/releases/tag/v0.1.0)

A personal work assistant for AI Agents: keep task history, prepare daily plans, and follow up on unfinished work through a local CLI.

## Overview

Work Pilot combines a portable Agent Skill with a Go CLI and a local SQLite database. It supports persistent tasks and progress, daily agendas, summaries, Markdown archives, backups, and explicitly configured calendar and reminder integrations. One person can use the same local records across Agents.

**v0.1.0 validation:** macOS Apple Silicon has been run natively. The other four platform binaries are cross-compiled. External calendars, notification delivery, unattended host scheduling, and real GitHub data handoff still need authorized live acceptance.

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

Download your archive and `CHECKSUMS.txt` from [v0.1.0](https://github.com/HuangChenning/work-pilot/releases/tag/v0.1.0). Each archive includes both READMEs, a CLI, and a `skill/` directory with the matching Skill, references, and nested platform binary.

| Platform | Archive |
| --- | --- |
| macOS Apple Silicon | `work-pilot-0.1.0-darwin-arm64.tar.gz` |
| macOS Intel | `work-pilot-0.1.0-darwin-amd64.tar.gz` |
| Linux arm64 | `work-pilot-0.1.0-linux-arm64.tar.gz` |
| Linux amd64 | `work-pilot-0.1.0-linux-amd64.tar.gz` |
| Windows amd64 | `work-pilot-0.1.0-windows-amd64.zip` |

### macOS or Linux

For a **new Codex installation** with no existing `work-pilot` Skill directory, the macOS arm64 example is:

```sh
shasum -a 256 work-pilot-0.1.0-darwin-arm64.tar.gz
# Compare the digest with CHECKSUMS.txt before extracting.
mkdir work-pilot-0.1.0
tar -xzf work-pilot-0.1.0-darwin-arm64.tar.gz -C work-pilot-0.1.0
mkdir -p "$HOME/.codex/skills"
cp -R work-pilot-0.1.0/skill "$HOME/.codex/skills/work-pilot"
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
Expand-Archive .\work-pilot-0.1.0-windows-amd64.zip .\work-pilot-0.1.0
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse .\work-pilot-0.1.0\skill "$HOME\.codex\skills\work-pilot"
$WP_SKILL_DIR = "$HOME\.codex\skills\work-pilot"
$WP_BIN = "$WP_SKILL_DIR\bin\windows-amd64\work-pilot.exe"
& $WP_BIN version
& $WP_BIN install register --path $WP_SKILL_DIR
```

On first use, confirm your timezone and working days; optionally name the assistant. Optional calendar or channel setup does not block ordinary task recording. The default profile uses the OS user configuration directory under `work-pilot`; pass `--data-dir PATH` before the command to select another profile.

## Capabilities and acceptance limits

- **Local records:** tasks, progress logs, state history, filtered queries, daily agendas and summaries; date-only and exact-time deadlines stay distinct. Markdown export, monthly completion archives, trash/restore, and consistent local backup/restore are implemented and locally tested.
- **Read-only calendars:** Google Calendar, enterprise WeChat app-created calendars, ICS files, and a macOS native helper. WeChat recurrence is unsupported. macOS requires native calendar permission; Linux and Windows can use supported ICS sources rather than arbitrary calendar apps. Fixtures are tested; actual accounts and native calendar access await authorization and acceptance.
- **Reminders:** saved rules, recurrence, quiet hours, durable delivery states, and designated-device checks. Host scheduling is configured separately; saving a rule does not start a schedule. Unattended execution and delivery await live acceptance.
- **Notifications:** SMTP email and enterprise WeChat, Feishu, and DingTalk group webhooks are fixture-tested. Personal-message delivery and signed robot modes are unsupported. Each target needs explicit authorization. Unknown send outcomes are preserved without blind automatic retries.
- **Optional GitHub backup:** a separate private data repository supports snapshots and sequential device handoff with conflict checks. Fixture-tested; no real remote acceptance yet. Concurrent offline edits are not automatically merged, and handoff does not enable a second reminder device.

A failed calendar source is reported as missing or unverified; an absent event is not assumed cancelled. A saved rule, an enabled host schedule, and confirmed delivery are separate states. Calendar events and related preparation tasks keep independent statuses.

## Updates and reference

```sh
"$WP_BIN" update check
"$WP_BIN" update --version 0.1.0
```

Explicit updates check platform, checksums, compatibility, and local Skill edits, then update the CLI and registered Skill locations. Reload sessions that already loaded old instructions. Windows self-update is deferred to manual installation; replace the installed package manually and register its path again. Real release download/update acceptance remains separate from local updater tests.

See the [command reference](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/commands.md) for exact syntax, task versions, calendar configuration, and reminder preview/send boundaries; see [setup notes](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/setup.md) for authorization, scheduling, and recovery. The [configuration examples](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/configuration.md) cover calendar, reminder, channel, and handoff JSON.
