| name | shanxi-trade-ics-monthly |
| --- | --- |
| description | 从“交易公告”Markdown表同步到年度 ICS（VEVENT），包含月度/上中下旬分时段、结果发布、滚动撮合与发电侧合同转让；保持与历史格式一致，便于订阅与复核。 |
| version | 1.0.0 |

## Shanxi Monthly Trade ICS Sync

将每月的“交易公告”表格转为 iCalendar 事件块（VEVENT），按时间顺序追加到年度 `YYYYtrade.ics` 文件中。

核心原则：严格按公告内容建事件，不擅自添加或改写；字段格式、命名与历史保持一致（含时区、DTSTAMP、UID 规则）。

## Script Directory

当前技能以人工/半自动方式执行，无强制脚本依赖。可选地在 `scripts/` 目录加入自定义工具：

| Script | Purpose |
| --- | --- |
| `scripts/check-uids.ts` | 扫描 ICS，校验 UID 连续性与唯一性 |
| `scripts/validate-ics.ts` | 事件块基本结构校验（BEGIN/END 成对、字段完整） |

## Preferences (EXTEND.md)

支持在以下路径读取扩展配置（从高到低优先级）：

```
# macOS, Linux, WSL, Git Bash
test -f .baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md && echo "project"
test -f "${XDG_CONFIG_HOME:-$HOME/.config}/baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md" && echo "xdg"
test -f "$HOME/.baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md" && echo "user"
```

```
# PowerShell (Windows)
if (Test-Path .baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md) { "project" }
$xdg = if ($env:XDG_CONFIG_HOME) { $env:XDG_CONFIG_HOME } else { "$HOME/.config" }
if (Test-Path "$xdg/baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md") { "xdg" }
if (Test-Path "$HOME/.baoyu-skills/shanxi-trade-ics-monthly/EXTEND.md") { "user" }
```

EXTEND.md 支持（示例）：

| Setting | Values | Default | Description |
| --- | --- | --- | --- |
| `timezone` | IANA TZ | `Asia/Shanghai` | ICS 时区（与历史一致） |
| `base_dtstamp` | UTC `YYYYMMDDThhmmssZ` | `20251229T000000Z` | 统一 DTSTAMP（随年度维护） |
| `uid_prefix` | string | `shanxi` | UID 末尾域标识，如 `@shanxi` |
| `uid_start_seq` | integer | auto | 本批插入起始序号（接续历史最大值） |
| `templates.concentrated_bidding` | multi-line | 三段式默认 | 集中竞价 DESCRIPTION 模板（含 `\n` 换行） |
| `templates.rolling` | string | `交易方式: 滚动撮合` | 滚动撮合 DESCRIPTION 模板 |
| `templates.bilateral` | string | `交易方式: 双边协商` | 双边协商 DESCRIPTION 模板 |
| `templates.listing` | string | `交易方式: 挂牌` | 挂牌 DESCRIPTION 模板 |
| `include_multi_month_sessions` | true/false | false | 是否写入“多月连续交易”类场次（默认不写入，保持与历史一致） |

## Usage

流程分两阶段：先“解析公告”，再“写入 ICS 并校验”。

## Workflow

### Step 1: 读取公告并识别内容

读取目标月份 `交易公告/YYYY-MM.md` 表格，识别字段：

| 列名 | 说明 |
| --- | --- |
| 日期 | 单日或日期范围（例如 `2026年5月6日` / `2026年5月6-15日`） |
| 时间 | 起止时段（如 `09:00-12:00`） |
| 交易方式/环节 | 集中竞价/滚动撮合/挂牌/双边协商/结果发布/预申报/申报/出清等 |
| 交易组织安排 | 用于 ICS `SUMMARY` 的完整事件标题 |

注：当检测到“多月连续交易”类行，是否写入由 `include_multi_month_sessions` 决定（默认跳过）。

### Step 2: 解析并结构化事件

为每一行生成结构化事件：

- 解析日期与时间，形成本地时区 `DTSTART`/`DTEND`（`YYYYMMDDThhmmss`，无秒则用 `00`）。
- `SUMMARY` 取“交易组织安排”。
- `DESCRIPTION`：
  - 集中竞价：使用三段式模板（预申报/申报/出清，使用 `\n` 分隔）。
  - 滚动撮合/挂牌/双边协商：按模板填充“交易方式: …”。
- 不在公告内的补充信息不新增。

### Step 3: 确定插入点与 UID 规则

- 在 `YYYYtrade.ics` 的末尾（上月最后一个 `END:VEVENT` 之后）按时间顺序追加。
- UID 采用：`YYYYMMDDThhmm-序号@{uid_prefix}`；序号延续历史最大值递增。
- `DTSTAMP` 使用统一 `base_dtstamp`（年度内一致）。

### Step 4: 写入 VEVENT 块

每条事件写入：

```
BEGIN:VEVENT
DTSTAMP:{base_dtstamp}
UID:{YYYYMMDDThhmm}-{seq}@{uid_prefix}
DTSTART;TZID={timezone}:{YYYYMMDDThhmm}
DTEND;TZID={timezone}:{YYYYMMDDThhmm}
SUMMARY:{标题}
DESCRIPTION:{可选}
END:VEVENT
```

集中竞价结果发布、滚动撮合（上午/下午）、合同转让（双边/挂牌）需分别建独立事件。

### Step 5: 保存并备份

保存 `YYYYtrade.ics`。如需备份，可将上一次版本另存为 `YYYYtrade.backup-YYYYMMDD-HHMM.ics`。

### Step 6: 校验

- 快速检查：`rg 'YYYYMM' YYYYtrade.ics` 是否覆盖公告全部场次。
- 结构检查：BEGIN/END 成对、字段齐全、时间递增、UID 无重复。
- 历史一致性：时区使用 `Asia/Shanghai`；`DESCRIPTION` 换行使用 `\n`；关键命名与已存在月份一致。

### Step 7: 完成报告

输出本次同步结果（示例模板）：

```
**Sync Complete**

**Month:** 2026-05
**Files:**
- Updated: 2026trade.ics

**Events Added:**
- 月度分时段：X（集中竞价/结果发布/滚动撮合）
- 上旬分时段：X（集中竞价/结果发布/滚动撮合）
- 中旬分时段：X（集中竞价/结果发布/滚动撮合）
- 下旬分时段：X（集中竞价/结果发布/滚动撮合）
- 合同转让（双边/挂牌）：X
- 代理购电/绿色电力：X

**Duplicates Skipped:** 0
**UID Range:** N → M
```

## Notes

- 不修改既有月份与历史事件的内容或顺序。
- `Asia/Shanghai` 为唯一时区；所有 `DTSTART/DTEND` 使用该时区形式。
- 集中竞价 `DESCRIPTION` 使用三行并以 `\n` 分隔：
  - `06:30-09:15 预申报`
  - `09:15-09:25 申报`
  - `09:25-09:30 出清`
- 若公告存在“多月连续交易”，默认不写入（与历史一致）；如需开启请在 EXTEND.md 指定。

## Extension Support

通过 EXTEND.md 可配置模板、时区、UID 规则与纳入范围（如多月连续交易）。建议项目级配置优先，以确保团队成员一致行为。

