# 山西电力市场交易日历

把山西电力交易中心每月发布的交易时间安排整理为 iCalendar 订阅文件，通过 Cloudflare Pages 托管：

```
https://shanxi-spot-ics.pages.dev/trade.ics
```

| 路径 | 说明 |
| --- | --- |
| `trade.ics` | 订阅文件，每月追加新事件 |
| `2025trade.ics` | 2025 年归档，不再更新 |
| `交易公告/YYYY-MM.md` | 每月公告（由 PDF 转换的 Markdown） |
| `skills/SKILL.md` | 月度同步流程与事件规则 |
| `scripts/check.py` | 校验 `trade.ics` 结构及与公告的一致性 |
| `_headers` | Pages 响应头：`.ics` 以 `text/calendar` 返回，缓存 5 分钟 |

## 每月更新

1. 把新公告存为 `交易公告/YYYY-MM.md`。
2. 按 [skills/SKILL.md](skills/SKILL.md) 把事件追加到 `trade.ics`。
3. 运行 `python3 scripts/check.py YYYY-MM` 核对，确认无误后推送到 `main`，Pages 自动部署。

## Cloudflare Pages 配置

| 设置 | 值 |
| --- | --- |
| 生产分支 | `main` |
| 构建命令 | `python3 scripts/check.py --ics-only` |
| 构建输出目录 | `.` |

构建时只校验 `trade.ics` 结构：文件损坏则构建失败，线上保留上一次成功的版本。与公告的核对只在本地第 3 步进行，不阻塞发布。

日历中不包含日滚动交易和多月连续交易。
