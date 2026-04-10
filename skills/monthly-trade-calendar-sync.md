# Skill: Monthly Trade Calendar Sync

## 触发场景
当有新的“交易公告”Markdown表格发布，需要把公告中的所有场次同步到 `2026trade.ics`（或未来对应年份）里。

## 操作步骤
1. **梳理公告**：阅读目标月份的 Markdown 表格，记录每条交易的日期、时间段、交易方式/环节、名称；注意同一天的多场次、集中竞价的三段流程（预申报/申报/出清）及结果发布、滚动撮合的时间块，以及发电侧合同转让。
2. **准备插入点**：在 `2026trade.ics` 中找到前一个月的末尾 `END:VEVENT`，确认新事件将按时间顺序追加，并延续 UID 序号（格式 `YYYYMMDDThhmm-序号@shanxi`）。
3. **写入事件**：为每条交易创建 `BEGIN:VEVENT` 块，设置 `DTSTAMP`（沿用文件头统一时间）、`UID`、`DTSTART`、`DTEND`、`SUMMARY`，根据需要添加 `DESCRIPTION`：
   - 集中竞价：`DESCRIPTION` 写三行流程。
   - 滚动撮合/挂牌/双边协商：简单写“交易方式: …”。
4. **新增月度/上中下旬包**：同一天若既有合同转让又有分时段交易，要分别建事件；滚动撮合通常包含上午/下午两个时段。
5. **校验**：
   - 用 `rg 'YYYYMM' 2026trade.ics` 检查目标月份所有事件是否齐全。
   - 用 `nl -ba 2026trade.ics | sed -n 'start,endp'` 目检格式：确保每个块以 `END:VEVENT` 结束，`DESCRIPTION` 换行使用 `\n`。
   - 确认 UID 连续、时间顺序正确。

## 产出
- `2026trade.ics` 更新后的事件集合。
- 可附一份新增事件列表，方便业务确认。
