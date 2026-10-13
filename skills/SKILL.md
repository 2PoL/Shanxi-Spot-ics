---
name: shanxi-trade-ics-monthly
description: 从“交易公告”Markdown 表同步山西电力交易事件到固定订阅文件 trade.ics；用于每月新公告发布后的日历更新。
metadata:
  version: 2.0.0
---

## Shanxi Monthly Trade ICS Sync

把 `交易公告/YYYY-MM.md` 的表 1 转为 VEVENT，追加到订阅文件 `trade.ics`，再用 `scripts/check.py` 校验。

- `trade.ics` 是唯一持续更新的输出；`2025trade.ics` 为归档，不再改动，也不要新建 `YYYYtrade.ics`。
- 严格按公告建事件，不增删、不改写标题；格式与已有事件保持一致。

## Workflow

### 1. 准备公告

公告保存为 `交易公告/YYYY-MM.md`，表 1 为 HTML 表格，列为：日期 / 时间 / 交易方式(环节) / 交易组织安排。

PDF 转换常在跨页处把一行拆成两行（标题被截断、日期单元格为空、`rowspan` 错位）。遇到这种行，以 PDF 原文为准生成事件，不必修改 md。

### 2. 生成事件

| 规则 | 说明 |
| --- | --- |
| 跳过 | 表 2 日滚动交易；标题含“多月连续交易”的场次 |
| 合并 | 同一标题的 `预申报`/`申报`/`出清` 合并为一个事件：开始取首段、结束取末段 |
| 拆分 | 结果发布、滚动撮合上午/下午、合同转让双边/挂牌，各为独立事件 |
| 日期范围 | `2025年12月18日09:00-12月19日12:00` 这类跨日写法，生成一个跨日事件 |
| SUMMARY | 取“交易组织安排”原文，去掉多余空格（如 `发电侧 2026年` → `发电侧2026年`） |

DESCRIPTION 按交易方式选择：

| 交易方式/环节 | DESCRIPTION |
| --- | --- |
| 预申报+申报+出清 | `06:30-09:15 预申报\n09:15-09:25 申报\n09:25-09:30 出清`（按公告实际时段） |
| 滚动撮合 / 双边协商 / 挂牌 / 集中竞价 | `交易方式: {方式}` |
| `/` | `交易方式/环节: /` |
| 结果发布 | 不写 DESCRIPTION |

### 3. 写入 trade.ics

在 `END:VCALENDAR` 之前按 DTSTART 顺序追加，已有事件不改动、不重排。

```
BEGIN:VEVENT
DTSTAMP:20251229T000000Z
UID:{DTSTART}-{seq}@shanxi
DTSTART;TZID=Asia/Shanghai:{YYYYMMDDThhmmss}
DTEND;TZID=Asia/Shanghai:{YYYYMMDDThhmmss}
SUMMARY:{标题}
DESCRIPTION:{见上表}
END:VEVENT
```

- `seq` 接续文件中现有的最大序号递增：`grep -o -- '-[0-9]*@shanxi' trade.ics | tr -dc '0-9\n' | sort -n | tail -1`。
- `DTSTAMP` 固定为 `20251229T000000Z`。
- 时区一律 `Asia/Shanghai`，换行符为 LF，文件以换行结尾。

### 4. 校验

```bash
python3 scripts/check.py YYYY-MM
```

检查内容包括：文件结构（BEGIN/END 是否配对、必填字段是否齐全、UID 是否唯一且与 DTSTART 一致、结束时间是否晚于开始时间、有没有误写入日滚动或多月连续交易），以及该月 md 中的每个场次是否都已写入。

- 结构错误必须修复。
- 报告“缺失”时：若对应行有 `!` 警告（PDF 转换断行），对照 PDF 确认日历已正确写入即可；否则补写事件。

推送到 `main` 后 Cloudflare Pages 自动部署到 `https://shanxi-spot-ics.pages.dev/trade.ics`，构建命令 `python3 scripts/check.py --ics-only` 只校验结构。

### 5. 报告

```
**Month:** YYYY-MM
**Events Added:** N（UID 序号 A → B）
**Skipped:** 日滚动 / 多月连续交易 X 条
**Check:** 通过
```
