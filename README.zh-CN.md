# Work Pilot

[English](README.md) · [v0.1.0 安装包](https://github.com/HuangChenning/work-pilot/releases/tag/v0.1.0)

面向 AI Agent 的私人工作助理：通过本地 CLI 保存任务进展、整理每日待办，并持续跟进未完成事项。

## 简介

Work Pilot 由通用 Agent Skill、Go CLI 和本地 SQLite 数据库组成，支持持久化任务与进展、每日安排、总结、Markdown 归档、备份，以及明确配置的日历和提醒集成。同一个人可以跨 Agent 使用同一份本地记录。

**v0.1.0 验证范围：** 已在 macOS Apple Silicon 原生运行，其他四个平台的二进制完成交叉编译。外部日历、真实通知送达、宿主无人值守调度和真实 GitHub 数据交接，仍需授权后的实际验收。

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

从 [v0.1.0](https://github.com/HuangChenning/work-pilot/releases/tag/v0.1.0) 下载对应安装包和 `CHECKSUMS.txt`。每个包包含两份 README、CLI，以及 `skill/` 目录中的配套 Skill、参考文档和嵌套的平台二进制。

| 平台 | 安装包 |
| --- | --- |
| macOS Apple Silicon | `work-pilot-0.1.0-darwin-arm64.tar.gz` |
| macOS Intel | `work-pilot-0.1.0-darwin-amd64.tar.gz` |
| Linux arm64 | `work-pilot-0.1.0-linux-arm64.tar.gz` |
| Linux amd64 | `work-pilot-0.1.0-linux-amd64.tar.gz` |
| Windows amd64 | `work-pilot-0.1.0-windows-amd64.zip` |

### macOS 或 Linux

以下以 macOS arm64 为例，适用于尚无 `work-pilot` Skill 目录的 **Codex 首次安装**：

```sh
shasum -a 256 work-pilot-0.1.0-darwin-arm64.tar.gz
# 与 CHECKSUMS.txt 中的摘要比对一致后再解压。
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

其他平台替换安装包名和 `bin/<platform>/` 路径。Linux 可用 `sha256sum` 计算摘要。其他 Agent 使用各自支持的 Skill 目录，并登记其绝对路径。安装后重新加载 Agent 会话。

### Windows

用 `Get-FileHash -Algorithm SHA256` 与 `CHECKSUMS.txt` 比对，解压 ZIP，再将 `skill/` 复制到 Agent 的 Skill 目录。Codex 首次安装的 PowerShell 示例：

```powershell
Expand-Archive .\work-pilot-0.1.0-windows-amd64.zip .\work-pilot-0.1.0
New-Item -ItemType Directory -Force "$HOME\.codex\skills" | Out-Null
Copy-Item -Recurse .\work-pilot-0.1.0\skill "$HOME\.codex\skills\work-pilot"
$WP_SKILL_DIR = "$HOME\.codex\skills\work-pilot"
$WP_BIN = "$WP_SKILL_DIR\bin\windows-amd64\work-pilot.exe"
& $WP_BIN version
& $WP_BIN install register --path $WP_SKILL_DIR
```

首次使用时确认时区与工作日，可选设置助理称呼。可选日历或通知渠道尚未配置，不会阻塞普通任务记录。默认数据目录为操作系统用户配置目录下的 `work-pilot`；可在命令前传入 `--data-dir PATH` 选择其他数据目录。

## 能力与验收限制

- **本地记录：** 任务、进展日志、状态历史、筛选查询、每日安排与总结，区分日期级和精确时刻的截止时间。Markdown 导出、按完成月份归档、回收与恢复、一致的本地备份与恢复，均已实现并通过本地测试。
- **只读日历：** Google 日历、企业微信应用创建的日历、ICS 文件，以及 macOS 原生辅助程序。企业微信暂不支持重复日程。macOS 需要系统日历权限；Linux 和 Windows 可使用受支持的 ICS 来源，不能直接读取任意日历应用。接口模拟测试已通过，真实账号与原生日历访问仍待授权验收。
- **提醒：** 保存规则、周期事项、免打扰、持久化送达状态和主提醒设备检查。宿主调度需单独配置，保存规则不会自动启用调度。无人值守执行和真实送达待验收。
- **通知：** SMTP 邮件，以及企业微信、飞书、钉钉群机器人 Webhook 已通过接口模拟测试。不支持个人消息投递和签名机器人模式。每个收件目标都需要明确授权；结果未知的发送保留状态，不盲目自动重试。
- **可选 GitHub 备份：** 使用独立私有数据仓库，支持带冲突检查的快照和多设备轮流接续。已通过模拟测试，尚未进行真实远程验收。不自动合并多设备离线修改，交接也不会启用第二台设备的提醒。

失败的日历来源会标为缺失或未核实，不能因为单次查询缺少事件就推断取消。保存提醒规则、宿主调度启用和确认送达是三个不同状态。日程与相关准备任务分别维护状态。

## 升级与参考

```sh
"$WP_BIN" update check
"$WP_BIN" update --version 0.1.0
```

显式升级会检查平台、校验和、兼容性及本地 Skill 修改，再更新 CLI 和已登记的 Skill 位置。已加载旧指令的会话需重新加载。Windows 自更新暂缓，需手工替换安装包并重新登记路径。真实 Release 下载与升级验收，仍与本地升级器测试分开记录。

[命令参考](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/commands.md) 说明准确语法、任务版本、日历配置，以及提醒预览和发送的边界；[配置说明](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/setup.md) 说明授权、调度和恢复。[配置示例](https://github.com/HuangChenning/work-pilot/blob/v0.1.0/skills/work-pilot/references/configuration.md) 提供日历、提醒、通知渠道和交接所需的 JSON。
