# Work Pilot

[English](README.md) · [v0.2.0 安装包](https://github.com/HuangChenning/work-pilot/releases/tag/v0.2.0)

面向 AI Agent 的私人工作助理：通过本地 CLI 保存任务进展、整理每日待办，并持续跟进未完成事项。

## 简介

Work Pilot 由通用 Agent Skill、Go CLI 和本地 SQLite 数据库组成，支持持久化任务与进展、每日安排、总结、Markdown 归档、备份，以及明确配置的日历和提醒集成。同一个人可以跨 Agent 使用同一份本地记录。

**v0.2.0 验证范围：** 已在 macOS Apple Silicon 原生运行，官方 wecom-cli 的普通/每周/月度个人日程读取及一次明确授权的个人消息发送已通过真实验收。其他四个平台完成交叉编译；其他真实集成、无人值守调度、日历改期/取消例外及真实 GitHub 数据交接仍待验收。

## 示例：记录任务，再查询当天安排

使用下方安装步骤设置的 `WP_BIN` 路径。此示例创建独立临时数据目录，日期仅为示例。

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

当天安排会包含 **Prepare project report**，原因为 `reason: "due_today"`。任务保存 `due_date: "2026-11-06"`，而 `due_at` 为空：只有日期的截止时间不会被补成某个时刻。这段记录与查询流程已在 macOS arm64 完成冒烟测试。

在对话中，可让 Agent 记录任务、追加进展、查询今日安排，或将明确完成的任务标记为完成。未安排日期的工作留在独立待办池。命令返回 JSON；错误返回 `ok: false` 和非零退出码。

## 工作原理

<!-- diagram-decision: prose-only | reason: 三行职责表即可直接说明 Agent、CLI 与存储的边界；流程图会重复这些内容，还会模糊外部集成需要分别授权这一事实。 -->

| 组件 | 职责 |
| --- | --- |
| Agent Skill | 理解请求、澄清歧义、区分事实与建议，并解释执行结果。 |
| Go CLI | 校验明确输入、计算日期、查询和修改记录，并执行已配置的操作。 |
| 本地 SQLite 数据库 | 保存正式的个人配置、任务、进展和执行状态。 |

个人数据位于 Skill 安装目录之外。生成的 `todo.md` 和 `archive/YYYY/MM.md` 是可重建视图，手工修改不会反向写入数据库。提醒依靠宿主调度器调用单次检查与发送命令，不包含额外常驻服务。

## 开始使用

从 [v0.2.0](https://github.com/HuangChenning/work-pilot/releases/tag/v0.2.0) 下载对应安装包和 `CHECKSUMS.txt`。每个包包含两份 README、CLI，以及 `skill/` 目录中的配套 Skill、参考文档和嵌套的平台二进制。

| 平台 | 安装包 |
| --- | --- |
| macOS Apple Silicon | `work-pilot-0.2.0-darwin-arm64.tar.gz` |
| macOS Intel | `work-pilot-0.2.0-darwin-amd64.tar.gz` |
| Linux arm64 | `work-pilot-0.2.0-linux-arm64.tar.gz` |
| Linux amd64 | `work-pilot-0.2.0-linux-amd64.tar.gz` |
| Windows amd64 | `work-pilot-0.2.0-windows-amd64.zip` |

### macOS 或 Linux

以下以 macOS arm64 为例，适用于尚无 `work-pilot` Skill 目录的 **Codex 首次安装**：

```sh
shasum -a 256 work-pilot-0.2.0-darwin-arm64.tar.gz
# 与 CHECKSUMS.txt 中的摘要比对一致后再解压。
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

其他平台替换安装包名和 `bin/<platform>/` 路径。Linux 可用 `sha256sum` 计算摘要。其他 Agent 使用各自支持的 Skill 目录，并登记其绝对路径。安装后重新加载 Agent 会话。

### Windows

用 `Get-FileHash -Algorithm SHA256` 与 `CHECKSUMS.txt` 比对，解压 ZIP，再将 `skill/` 复制到 Agent 的 Skill 目录。Codex 首次安装的 PowerShell 示例：

```powershell
Expand-Archive .\work-pilot-0.2.0-windows-amd64.zip .\work-pilot-0.2.0
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse .\work-pilot-0.2.0\skill "$HOME\.codex\skills\work-pilot"
$WP_SKILL_DIR = "$HOME\.codex\skills\work-pilot"
$WP_BIN = "$WP_SKILL_DIR\bin\windows-amd64\work-pilot.exe"
& $WP_BIN version
& $WP_BIN install register --path $WP_SKILL_DIR
```

首次使用时确认时区与工作日，可选设置助理称呼。可选日历或通知渠道尚未配置，不会阻塞普通任务记录。默认数据目录为操作系统用户配置目录下的 `work-pilot`；可在命令前传入 `--data-dir PATH` 选择其他数据目录。

## 接入外部日历

下列示例使用已安装的 `WP_BIN` 和 macOS/Linux 的 POSIX Shell。连接配置与密钥应放在 Skill 和本仓库之外，例如：

```sh
WP_CONFIG_DIR="$HOME/.config/work-pilot-connections"
mkdir -p "$WP_CONFIG_DIR"
"$WP_BIN" config set --timezone Asia/Shanghai --workdays 1,2,3,4,5
```

请按实际情况选择时区和工作日。Windows 使用绝对配置目录，通过 `$env:变量名 = '值'` 设置环境变量，以 `& $WP_BIN` 调用程序，JSON 格式相同。环境变量必须传给实际运行 Work Pilot 的进程，包括以后配置的调度器。

<details>
<summary><strong>macOS 系统日历：授权辅助程序，再选择日历</strong></summary>

在固定的 Skill 安装位置，运行与你的 Mac 匹配的辅助程序：

```sh
WP_BRIDGE="$WP_SKILL_DIR/references/native/darwin-arm64/work-pilot-eventkit"
"$WP_BRIDGE" authorize
"$WP_BRIDGE" list-calendars
```

Intel Mac 改用 `darwin-amd64`。接受 macOS 日历权限提示，从返回的日历信息中选择 ID。系统要求授予日历访问权限，Work Pilot 本身只读取事件。若拒绝过授权，可在“系统设置 → 隐私与安全性 → 日历”中检查权限。辅助程序尚无 Developer ID 公证，仍需在你的机器上完成原生授权验收。

将以下内容保存为配置目录中的 `calendars.json`，把占位符替换为**辅助程序的绝对路径**和选定的日历 ID。JSON 不会展开 `$HOME` 或 Shell 变量。

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
<summary><strong>Google 日历：提供只读 OAuth 访问令牌</strong></summary>

在 Google Cloud 项目中启用 Calendar API，配置 OAuth 同意屏幕与客户端凭据，通过你自己的 OAuth 客户端完成用户授权。使用可读取事件的权限，例如：

```text
https://www.googleapis.com/auth/calendar.events.readonly
```

仅忙闲或仅日历元信息权限无法读取事件详情。参见 Google 官方的[权限说明](https://developers.google.com/workspace/calendar/api/auth)和 [OAuth 配置指南](https://developers.google.com/workspace/guides/configure-oauth-consent)。

把得到的 **access token** 放入环境变量，不要填入 client secret、API key 或 refresh token：

```sh
export WORK_PILOT_GOOGLE_TOKEN='YOUR_OAUTH_ACCESS_TOKEN'
```

保存为 `calendars.json`；`primary` 表示已授权账号的主日历。其他日历使用 Google 日历设置中的日历 ID，并确认该账号有读取权限。

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

v0.2.0 没有内置 OAuth 登录和令牌续期。访问令牌过期后，必须由外部 OAuth 客户端刷新，并将新值传给 Work Pilot；设置一次环境变量不代表以后能持续无人值守访问。

</details>

<details>
<summary><strong>企业微信日历：提供应用令牌和 cal_id</strong></summary>

请企业管理员准备具有对应日历 API 访问能力的应用，通过企业的凭据管理流程获取应用 `access_token`，并取得选定日历的 `cal_id`。当前适配器读取的是**由该应用创建、且该应用有权访问的日历**，不能承诺读取普通个人日历。企业微信日历授权与群机器人 Webhook 是两套独立配置。

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

保存为 `calendars.json`。令牌获取与续期需外部完成，不会自动复用其他 Agent 或插件的登录。此适配器暂不支持重复日程与全天事件规范化。应用权限不满足时，可改用受支持的 ICS 导出，不能把访问失败当成没有日程。

</details>

<details>
<summary><strong>Linux/Windows 本地日历：读取导出的 ICS 文件</strong></summary>

在日历应用中将选定日历导出为本地 `.ics` 文件，然后保存配置：

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

Windows 路径可写成 `C:/Users/YOU/Calendars/work.ics`，或使用转义后的反斜杠。导出工具需要将重复日程展开为独立事件；Work Pilot 不展开 ICS 重复规则，也不直接监控日历应用。日历更新后需重新导出。

</details>

同时接入多个来源时，将已配置的来源对象合并到同一个 `sources` 数组，每个 `id` 保持唯一。选择包含已知日程的一小段时间进行验证，替换成实际日期和时区偏移：

```sh
"$WP_BIN" calendar query --config "$WP_CONFIG_DIR/calendars.json" \
  --from 2026-11-06T00:00:00+08:00 --to 2026-11-07T00:00:00+08:00
"$WP_BIN" agenda --date 2026-11-06 \
  --calendar-config "$WP_CONFIG_DIR/calendars.json"
```

检查退出码、`ok`、`incomplete`，以及每个来源的 `verified`、`missing`、`synced_at`。将一条已知日程的标题、时间和时区与原日历对照。授权错误或未核实的缓存不算“成功查询到空日历”。这些命令不会创建、修改或取消外部日程。

## 发送邮件或聊天提醒

v0.2.0 通过**提醒派发**发送消息，没有通用的 `send` 命令。首次验证请选择一个明确授权的目标，并使用独立测试资料，避免误发正常资料中已有的待发提醒。

### 1. 准备一个通知渠道

邮件需要邮箱服务商提供的 SMTP 地址与端口、允许使用的发件地址，以及 SMTP 凭据或应用专用密码。当前未实现仅支持 OAuth 的 SMTP 认证。按服务商配置使用 STARTTLS（通常为587端口）或直连 TLS（`tls`，通常为465端口）。

```sh
export WORK_PILOT_SMTP_USER='YOUR_SMTP_USERNAME'
export WORK_PILOT_SMTP_PASSWORD='YOUR_SMTP_APP_PASSWORD'
```

保存为 `$WP_CONFIG_DIR/channels.json`，替换示例地址和服务器：

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

聊天消息需要在明确选定的群中创建自定义群机器人，取得 Webhook。选择聊天渠道时，用以下配置**替换**上面的邮件配置：

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

`channel` 按实际服务填 `wecom`、`feishu` 或 `dingtalk`，并使用对应平台的 Webhook。`target` 记录核对过的群名称，真正的接收群由 Webhook 决定，两者都要核实。邮件发给其他人时，授权后使用 `target_kind: "other"` 和 `additional_authorization: true`。这些布尔值仅记录已有授权，不会替你取得同意。

机器人自身的安全策略仍然有效。例如要求关键词时，提醒标题或正文必须包含该关键词；IP 白名单应覆盖实际发送主机。当前不支持飞书/钉钉签名模式，若组织强制要求签名或禁止自定义机器人，v0.2.0 无法使用该渠道。平台配置参见官方的[飞书机器人指南](https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot)和[钉钉机器人指南](https://open.dingtalk.com/document/robots/custom-robot-access)。日历令牌不能用于授权机器人发消息，机器人 Webhook 也不能读取日历。

### 2. 保存单次测试规则并预览

以下仅用 Python3 生成即时测试所需的时间。按实际情况替换时区，并保留打印出的测试资料路径，方便稍后核对结果。

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

预览会保存到期原因，但不会发送，也不会验证 SMTP/Webhook 凭据。继续前核对规则、渠道和接收目标；机器人要求关键词时修改正文。超过十分钟后请重新创建经过核对的测试规则，不要修改检查时钟来强行发送已过期通知。

### 3. 发送一次并核对结果

下面的命令会向配置的目标执行**真实外部发送**：

```sh
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch \
  --channels "$WP_CONFIG_DIR/channels.json" --send
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder deliveries
```

Windows 创建相同 JSON 文件，选择独立的 `$WP_TEST_DATA` 目录，并使用 `& $WP_BIN --data-dir $WP_TEST_DATA ...`。派发前，在同一个 PowerShell 会话中设置 SMTP/Webhook 环境变量。

`sent` 表示服务端已接受，仍需到收件箱或群里核对；`failed` 表示明确失败，修正凭据、收件人或平台策略后，再明确授权新的测试。`unknown` 或执行中断留下的 `claimed` 需要先调查，不能盲目重发；v0.2.0 没有自动核对或重试这类发送的命令。`attempts` 为空也不代表已送达，应检查规则时间、有效期、免打扰、授权和提醒设备设置。

验证通过后，再在正常资料中配置经过确认的提醒规则。无人值守运行需单独配置 Agent 宿主、launchd、systemd/cron 或 Windows 任务计划程序，以相同的 CLI 绝对路径、数据目录和凭据运行 `reminder dispatch --channels ABSOLUTE_CHANNELS_PATH --send`。每次派发会先检查到期规则。保存规则或设置早晚偏好不会安装调度；宿主需要运行，令牌也必须持续有效。周期规则、免打扰和其他通知字段参见[完整配置参考](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/configuration.md)。

## 能力与验收限制

- **本地记录：** 任务、进展日志、状态历史、筛选查询、每日安排与总结，区分日期级和精确时刻的截止时间。Markdown 导出、按完成月份归档、回收与恢复、一致的本地备份与恢复，均已实现并通过本地测试。
- **只读日历：** Google 日历、企业微信应用创建的日历、官方 wecom-cli 个人日程、ICS 文件，以及 macOS 原生辅助程序。官方 CLI 接入支持服务端已展开的重复实例；旧应用日历接入不展开重复规则。macOS 需要系统日历权限；Linux 和 Windows 可使用受支持的 ICS 来源，不能直接读取任意日历应用。官方 wecom-cli 的普通/每周/月度日程已通过真实验收，其他账号及原生日历访问仍待验收。
- **提醒：** 保存规则、周期事项、免打扰、持久化送达状态和主提醒设备检查。宿主调度需单独配置，保存规则不会自动启用调度。官方 wecom-cli 一次性个人消息已通过真实验收；无人值守执行和其他渠道仍待验收。
- **通知：** SMTP 邮件，以及企业微信、飞书、钉钉群机器人 Webhook 已通过接口模拟测试。官方 wecom-cli 最近会话的 Markdown 发送已通过真实个人消息验收；Webhook 机器人签名模式暂不支持。每个收件目标都需要明确授权；结果未知的发送保留状态，不盲目自动重试。
- **可选 GitHub 备份：** 使用独立私有数据仓库，支持带冲突检查的快照和多设备轮流接续。已通过模拟测试，尚未进行真实远程验收。不自动合并多设备离线修改，交接也不会启用第二台设备的提醒。

失败的日历来源会标为缺失或未核实，不能因为单次查询缺少事件就推断取消。保存提醒规则、宿主调度启用和确认送达是三个不同状态。日程与相关准备任务分别维护状态。

## 官方 wecom-cli 接入

**v0.2.0** 已包含通过官方 [wecom-cli](https://github.com/WecomTeam/wecom-cli)（最低 **1.3.4**）读取个人日程、向已授权的最近会话发送 Markdown 消息的能力。使用已安装的 `WP_BIN`，通过 `version` 和 `capabilities` 确认存在 `calendar.wecom_cli`、`notify.wecom_cli`。此消息接入已在 macOS arm64 完成一次明确授权的真实发送验收，服务端接受请求且收件人确认收到；普通日程、周会和月度重复日程的只读查询也已完成真实核对，包括时间、时区、参与人，以及重叠查询中的实例身份稳定性。

### 1. 配置授权与环境变量

单独安装官方原生可执行文件；Windows 使用 `.exe`，不使用 `.cmd`/`.bat` 包装脚本。授权方式二选一：

- **已授权目录：** 自行执行官方 `wecom-cli auth init`，再由同一操作系统用户复用该授权目录。默认目录为 `~/.config/wecom`。
- **官方令牌：** 通过 Agent 或调度器的密钥环境注入 `WECOM_CLI_ACCESS_TOKEN`。该变量优先于目录内凭据，过期后需要自行替换。

Work Pilot 固定读取以下变量名称：

| 变量 | 配置内容 |
| --- | --- |
| `WORK_PILOT_WECOM_CLI_PATH` | 可选，官方原生可执行文件的绝对路径；默认从 PATH 查找 `wecom-cli`。 |
| `WECOM_CLI_ACCESS_TOKEN` | 官方 Bearer 令牌；使用已授权目录时可不设置。 |
| `WECOM_CLI_CONFIG_DIR` | 可选，已授权目录的绝对路径；默认 `~/.config/wecom`。 |
| `WECOM_CLI_ADDITIONAL_HEADERS` | 可选，额外请求头，值为字符串键值组成的 JSON 对象。 |
| `WECOM_CLI_ADDITIONAL_HEADERS_*` | 可选，按官方后缀规则提供额外请求头对象。 |

macOS/Linux 复用已授权目录的示例：

```sh
export WORK_PILOT_WECOM_CLI_PATH="/absolute/path/to/wecom-cli"
export WECOM_CLI_CONFIG_DIR="$HOME/.config/wecom"
WP_CONFIG_DIR="$HOME/.config/work-pilot-connections"
mkdir -p "$WP_CONFIG_DIR"
"$WP_BIN" wecom status
```

PowerShell 示例：

```powershell
$env:WORK_PILOT_WECOM_CLI_PATH = 'C:\Tools\wecom-cli.exe'
$env:WECOM_CLI_CONFIG_DIR = "$HOME\.config\wecom"
$WP_CONFIG_DIR = "$HOME\.config\work-pilot-connections"
New-Item -ItemType Directory -Force -Path $WP_CONFIG_DIR | Out-Null
& $WP_BIN wecom status
```

令牌模式通过同一进程的环境注入令牌，不写入 JSON 文件或共享对话。额外请求头通常无需配置；确有需要时，值应为合法 JSON，例如 `{"X-Tenant":"your-tenant"}`。Work Pilot 不读取项目 `.env` 文件，也不接受 Bot ID/Secret 初始化变量。Agent 和后续调度器都必须继承选定的环境变量。凭据及连接配置文件应放在本仓库和 Skill 安装目录之外。

`authorized_material: true` 只表示本地存在授权材料；`remote_validity: "not_checked"` 表示服务端有效性和权限仍需通过实际请求的读取操作验证。Work Pilot 不会自动初始化授权；官方 wecom-cli 可能自行刷新目录内凭据，或在启动时迁移旧版授权目录。

### 2. 配置个人日历

保存为 `$WP_CONFIG_DIR/wecom-calendars.json`，将 `account_timezone` 改为授权账号实际使用的 IANA 时区：

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

示例日期需要替换为当前时间前后 30 天内的范围。仅支持授权用户的个人日程，`calendar_ids` 必须保持为 `["authorized-user"]`。支持有明确起止时间的普通日程，以及官方列表已展开的周会等重复日程。Work Pilot 保留每次实例的实际时间并分配独立身份，不再次展开重复规则；缺失的时区和参与人字段从系列详情补齐，不会用系列最初的日期覆盖某次实例。改期或未返回的实例以服务端结果为准。全天日程、夏令时歧义或不完整响应仍会标记为来源不可用/结果不完整。此接入不复用持久化日历缓存，以避免切换账号后混入旧账号数据。读取不会创建任务或修改外部日历。

### 3. 确认并绑定消息目标

按最近会话的精确名称查询，名称必须唯一；群聊使用 `group`，个人会话使用 `other`：

```sh
"$WP_BIN" wecom target --name "Reviewed team group" --kind group
```

此命令读取最近会话并返回不透明的 `authorization_binding`，不会发送消息，也不代表用户同意发送。确认并授权目标后，保存 `$WP_CONFIG_DIR/wecom-channels.json`，替换会话名称与绑定值：

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

群聊和其他个人均需要明确的额外授权，暂不支持自动识别“发给自己”。每次发送都会重新查询会话，并核对其身份及凭据绑定；名称重复或目标缺失时拒绝发送。令牌轮换、凭据刷新/重新授权、目录/请求头变化或会话被替换后，可能需要重新确认目标并更新绑定值。

### 4. 预览、发送与定时运行

按上方“发送邮件或聊天提醒”的一次性测试步骤，将提醒规则的 `channel_id` 从 `test-channel` 改为 `wecom-reviewed`，保存到独立的 `WP_TEST_DATA` 测试配置后检查预览。下面带 `--send` 的命令会执行**真实外部发送**，需要已有授权的提醒计划：

```sh
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder dispatch \
  --channels "$WP_CONFIG_DIR/wecom-channels.json" --send
"$WP_BIN" --data-dir "$WP_TEST_DATA" reminder deliveries
```

Windows 使用 `& $WP_BIN` 调用，JSON 格式相同。无人值守运行需要另外配置宿主调度器，并使用相同的可执行文件/数据/配置绝对路径、授权环境和指定提醒设备。保存规则或渠道不会自动启动定时任务。

Markdown 消息连同标题最多 20,480 个 UTF-8 字节，超限直接失败，不会自动拆分。`sent` 表示服务接受请求，仍需核实实际收到；`unknown` 或中断后保留的 `claimed` 应先调查再决定是否重试。上游版本基线及完整限制见[接入参考](skills/work-pilot/references/wecom-cli.md)。

## 升级与参考

```sh
"$WP_BIN" update check
"$WP_BIN" update --version 0.2.0
```

显式升级会检查平台、校验和、兼容性及本地 Skill 修改，再更新 CLI 和已登记的 Skill 位置。已加载旧指令的会话需重新加载。Windows 自更新暂缓，需手工替换安装包并重新登记路径。现有 v0.1.0 安装可使用上方显式 v0.2.0 升级命令，一并更新 CLI 和已登记的 Skill。

[命令参考](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/commands.md) 说明准确语法、任务版本、日历配置，以及提醒预览和发送的边界；[配置说明](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/setup.md) 说明授权、调度和恢复。[配置示例](https://github.com/HuangChenning/work-pilot/blob/v0.2.0/skills/work-pilot/references/configuration.md) 提供日历、提醒、通知渠道和交接所需的 JSON。
