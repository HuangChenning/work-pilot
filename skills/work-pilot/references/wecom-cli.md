# Official wecom-cli integration — v0.2.0

This connector is included in Work Pilot v0.2.0. Older v0.1.0 binaries do not support it. Check `version` and capabilities `calendar.wecom_cli` / `notify.wecom_cli` before using these instructions. Existing `wecom` REST calendars and group webhooks remain separate connectors.

## Authorization and environment

Install the official [wecom-cli](https://github.com/WecomTeam/wecom-cli) native executable, version **1.3.4 or newer**, separately. Windows requires the native `.exe`, rather than a `.cmd`/`.bat` shim. Authorize with the official tool yourself, or supply an official access token through your host's secret environment. Work Pilot never installs, initializes, or renews authorization on your behalf; upstream may refresh stored credentials itself.

| Variable | Contract |
| --- | --- |
| `WORK_PILOT_WECOM_CLI_PATH` | Optional absolute executable path; otherwise resolve `wecom-cli` from PATH. |
| `WECOM_CLI_ACCESS_TOKEN` | Optional official Bearer token; takes precedence over stored credentials. An expired environment token must be replaced by its operator. |
| `WECOM_CLI_CONFIG_DIR` | Optional absolute authorized profile directory; defaults to the official `~/.config/wecom`. Use the same profile and OS user that authorized it. |
| `WECOM_CLI_ADDITIONAL_HEADERS` | Optional official JSON object of string-valued request headers. |
| `WECOM_CLI_ADDITIONAL_HEADERS_*` | Optional additional official header objects, using upstream suffix semantics. |

Keep all values in the Agent/scheduler process environment. The same environment must reach unattended dispatch. Work Pilot does not read project `.env` files or accept Bot ID/Secret initialization variables. It excludes other `WECOM_*` variables, including upstream logging/custom endpoint overrides. Store credentials and channel files outside the Skill, repository and backups.

```sh
# Set the optional native executable and an already authorized profile.
export WORK_PILOT_WECOM_CLI_PATH="/absolute/path/to/wecom-cli"
export WECOM_CLI_CONFIG_DIR="$HOME/.config/wecom"
"$WP_BIN" wecom status
```

In PowerShell use `$env:WORK_PILOT_WECOM_CLI_PATH` and `$env:WECOM_CLI_CONFIG_DIR`, then `& $WP_BIN wecom status`. Token mode uses `$env:WECOM_CLI_ACCESS_TOKEN` or the host's secret injection; avoid pasting real tokens into shared transcripts.

`authorized_material: true` only confirms local authorization material exists. `remote_validity: "not_checked"` is deliberate: validate permissions through the requested read. Upstream can migrate legacy credential storage during startup; use a current authorized profile. Work Pilot keeps raw upstream diagnostics and credential values out of its JSON output.

## Read the authorized user's calendar

Save this configuration outside the installation, then query a range within the current time ±30 days. `account_timezone` must be the authorized account's actual IANA timezone because upstream query times are wall-clock values.

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
"$WP_BIN" calendar query --config /absolute/path/calendars.json \
  --from 2026-10-30T00:00:00+08:00 --to 2026-10-31T00:00:00+08:00
```

Dates above are examples; use a currently supported range. Only the authorized user's personal schedule is supported; arbitrary calendar IDs are unavailable. Timed ordinary and recurring occurrences returned by the official list are supported, including weekly and monthly meetings. Each occurrence keeps its returned start/end, title, location and instance-provided participants. Series details supply only missing timezone/participant metadata, never the master start/end. Recurring identities combine the series identity with the occurrence’s UTC start so overlapping queries preserve identity while different weeks stay distinct. Work Pilot never expands rules locally or invents missing/cancelled occurrences; rescheduling and exceptions follow the service response. It does not assert an old/new identity alias when an instance moves without a stable original occurrence identifier. All-day events, ambiguous DST times, duplicate or contradictory instances, incomplete pagination and unrecognized response shapes make the source unavailable/incomplete, rather than silently producing an empty successful calendar. This connector bypasses persistent calendar caching to avoid recovering another account's data after authorization changes. Reads never create tasks or modify external schedules.

## Review a recent message destination

First resolve a unique exact recent conversation name. `group` selects a group conversation; `other` selects a personal conversation. This read does not send a message or grant consent.

```sh
"$WP_BIN" wecom target --name "Reviewed team group" --kind group
```

Copy the returned opaque `authorization_binding` into the selected channel **after** reviewing and authorizing the destination. Both groups and other people require additional authorization. An automatic self-destination shortcut is unavailable.

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

Use `wecom-reviewed` as the saved reminder's `channel_id`. Follow the README's reminder preview/test procedure, then use `reminder dispatch --channels /absolute/path/channels.json --send` only within the authorized plan. Configuring a channel alone does not install a schedule.

Each send re-reads recent sessions and checks the exact name, type, identity and credential binding. Duplicate/missing names fail. Token rotation, credential refresh/reauthorization, profile/header changes or a replaced conversation can invalidate the binding: review the target again and update its binding before another authorized attempt. Never replace consent with a raw saved chat ID.

Messages use Markdown with a maximum of 20,480 UTF-8 bytes, including the subject. Oversized messages fail without splitting or truncation. `sent` means upstream accepted the request; it does not establish delivery or reading. After an unknown/interrupted outcome, investigate before attempting another send. Work Pilot does not automatically replay ambiguous sends.

## Validation

The integration is based on upstream 1.3.4 at commit `55785fa0a5c922279533a5b5a836b44b56f65ce7`, its [CLI reference](https://github.com/WecomTeam/wecom-cli/blob/55785fa0a5c922279533a5b5a836b44b56f65ce7/docs/cli-reference.md), source and published business Skills. Upstream service schemas are supplied dynamically; account-specific permissions and live compatibility require authorized acceptance. Validation includes synthetic CLI subprocesses, calendar fixtures and notification fixtures. On 2026-10-30, the v0.2.0 connector completed one explicitly authorized live message test on macOS arm64: the service accepted it and the recipient confirmed receipt. The isolated test rule and channel authorization were closed afterward. A live non-recurring calendar event was also verified against official details, including identity, title, start/end times, timezone and participants. Live mixed queries containing ordinary, weekly and monthly occurrences now match the official list and details, including stable identities across overlapping ranges. Fixtures cover moved/omitted instances, finite returned instances, master-time mismatch, participant overrides and DST transitions. Real edited/cancelled exceptions have not been separately exercised. All-day normalization remains unsupported; native Linux/Windows execution remains unverified.
