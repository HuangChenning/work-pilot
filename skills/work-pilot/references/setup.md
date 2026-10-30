# Setup and operating boundaries

## Platform and data directory

The Skill folder contains platform binaries under `bin/`. Use the current OS and architecture; do not attempt to run another platform's binary. The default personal data directory uses the operating system's user configuration directory under `work-pilot`; the CLI's global `--data-dir` explicitly selects another profile. It is independent of the Agent, Skill installation and work project.

This v0.2.0 installation exposes its exact capabilities at runtime. Read `capabilities` before provider, reminder, handoff or update operations. Report a missing command honestly; never emulate durable success with conversational memory.

Read [configuration](configuration.md) for calendar, reminder, channel and private data repository JSON and handoff commands.

## Calendar and channel connections

Selected calendar IDs and an authorized account are required. macOS system calendars need native permission; supported Linux/Windows local sources are listed individually, not inferred from an installed calendar application. Google and enterprise WeChat require their own read-only connections. Some enterprise WeChat APIs are restricted to app-created calendars; report the actual scope. Successful fixtures are not proof that a user's calendar is accessible.

Notification connectors require an explicit destination and authorization. Webhook group robots do not establish personal-message support. SMTP/robot endpoint credentials belong in local secret configuration or environment references, not Skill files, Markdown exports or GitHub data snapshots. Connector-specific confirmation requirements remain binding.

For official wecom-cli authorization, personal calendar reads or recent-conversation messages, read [wecom-cli integration](wecom-cli.md) before configuring the connector.

## Automation

Use the host's available scheduler to invoke the installed one-shot check/dispatch command, only after its capabilities and plan are confirmed. Do not invent a schedule command or claim a reminder is running merely because a rule was saved. The host may need to remain running and network-connected. Report the designated reminder device, schedule status, channel authorization and latest send result separately.

## Backups and handoff

`backup` generates a consistent snapshot. `restore` validates it, preserves current data first, and then replaces authoritative records. Work history is retained; daily backup rotation is a separate policy. Exported Markdown is not an alternative source of truth.

An optional private data repository is separate from the program repository. Multi-device use is sequential. Check local/remote snapshot identity and ownership; divergent work stops replacement. Relinquished devices become read-only until explicit takeover, and takeover does not silently enable reminders on a second machine. Unknown send outcomes and delivery history survive ordinary handoff. Never git-merge SQLite files or upload credentials.

## Releases and updates

Skill and CLI share a product Release version, with distinct interface and database versions. Use installed capability discovery for upgrade/installation commands. Install matching binaries and instructions from the same published Release. Windows online replacement is deferred to manual installation.

Before an update, check selected version, OS/architecture, file integrity, local Skill modifications, active executions and database migration needs. Registered Skill paths are updated with the CLI. Report each location's result, including partial failure or deferred platform replacement. Keep local modifications, preserve data before migration, and tell the user to reload any session that has already loaded old instructions. Default behavior does not silently upgrade or run arbitrary third-party plugins.
