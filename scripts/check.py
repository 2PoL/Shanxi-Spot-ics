#!/usr/bin/env python3
"""校验 trade.ics 的结构，并核对某月公告中的场次是否都已写入。

用法:
  python3 scripts/check.py --ics-only  # 只校验结构(Cloudflare Pages 构建命令)
  python3 scripts/check.py             # 校验结构 + 核对最新一个月的公告
  python3 scripts/check.py 2026-10     # 核对指定月份
  python3 scripts/check.py all         # 核对全部月份

公告核对基于转换后的 Markdown；PDF 转换造成的断行会显示为 “!” 警告，
对应场次可能被报告为缺失，需对照 PDF 原文判断。

退出码: 0 = 通过, 1 = 有错误。
"""
import re
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICS = ROOT / "trade.ics"
NOTICES = ROOT / "交易公告"
REQUIRED = ("DTSTAMP", "UID", "DTSTART", "DTEND", "SUMMARY")
MERGED_STAGES = ("预申报", "申报", "出清")  # 合并为同一事件的集中竞价阶段
SKIPPED = ("日滚动", "多月连续")  # 不写入日历的场次

errors = []


def parse_ics(path):
    text = path.read_text(encoding="utf-8")
    if text.startswith("﻿"):
        errors.append("文件含 BOM")
    if not text.endswith("\n"):
        errors.append("文件末尾缺少换行")
    stack, events, ev = [], [], None
    for no, line in enumerate(text.splitlines(), 1):
        if line.startswith("BEGIN:"):
            stack.append(line[6:])
            if line == "BEGIN:VEVENT":
                ev = {"_line": no}
        elif line.startswith("END:"):
            if not stack or stack.pop() != line[4:]:
                errors.append(f"第 {no} 行 {line} 不匹配")
            if line == "END:VEVENT" and ev is not None:
                events.append(ev)
                ev = None
        elif ev is not None:
            key, _, value = line.partition(":")
            key = key.split(";")[0]
            if key in ev:
                errors.append(f"第 {ev['_line']} 行事件重复属性 {key}")
            ev[key] = value
        elif stack == ["VCALENDAR", "VTIMEZONE"] and line.startswith("X-WR-"):
            errors.append(f"第 {no} 行 {line.split(':')[0]} 应位于 VCALENDAR 层级")
    if stack:
        errors.append(f"未闭合的组件: {stack}")
    return events


def lint(events):
    uids = Counter(e.get("UID") for e in events)
    errors.extend(f"UID 重复: {u}" for u, c in uids.items() if c > 1)
    for e in events:
        where = f"第 {e['_line']} 行事件"
        missing = [k for k in REQUIRED if k not in e]
        if missing:
            errors.append(f"{where}缺少 {', '.join(missing)}")
            continue
        if e["DTEND"] <= e["DTSTART"]:
            errors.append(f"{where}结束时间不晚于开始时间")
        if not re.fullmatch(rf"{e['DTSTART']}-\d+@shanxi", e["UID"]):
            errors.append(f"{where} UID 与 DTSTART 不一致: {e['UID']}")
        if any(s in e["SUMMARY"] for s in SKIPPED):
            errors.append(f"{where}不应写入: {e['SUMMARY']}")


class TableParser(HTMLParser):
    """把公告第一张 HTML 表格展开为二维数组(处理 rowspan/colspan)。"""

    def __init__(self):
        super().__init__()
        self.tables, self.cell = [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.tables[-1].append([])
        elif tag == "td":
            self.cell = ["", int(a.get("rowspan") or 1), int(a.get("colspan") or 1)]

    def handle_endtag(self, tag):
        if tag == "td" and self.cell:
            self.tables[-1][-1].append(self.cell)
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell[0] += data


def expand(rows):
    grid, carry = [], {}  # carry: 列号 -> [文本, 剩余行数]
    for row in rows:
        out, cells, col = [], iter(row), 0
        while True:
            if carry.get(col, [None, 0])[1] > 0:
                out.append(carry[col][0])
                carry[col][1] -= 1
                col += 1
                continue
            cell = next(cells, None)
            if cell is None:
                break
            text, rowspan, colspan = re.sub(r"\s+", "", cell[0]), cell[1], cell[2]
            for _ in range(colspan):
                out.append(text)
                if rowspan > 1:
                    carry[col] = [text, rowspan - 1]
                col += 1
        grid.append(out)
    return grid


def stamp(y, m, d, hh, mm):
    return f"{int(y):04}{int(m):02}{int(d):02}T{int(hh):02}{int(mm):02}00"


def parse_slot(date, time):
    """返回 (DTSTART, DTEND)；无法解析时返回 None。"""
    # 跨日写法: 日期列与时间列合并为 “2025年12月18日09:00-12月19日12:00”
    m = re.fullmatch(r"(\d{4})年(\d+)月(\d+)日(\d+):(\d+)-(\d+)月(\d+)日(\d+):(\d+)", date)
    if m:
        y, m1, d1, h1, n1, m2, d2, h2, n2 = m.groups()
        return stamp(y, m1, d1, h1, n1), stamp(y, m2, d2, h2, n2)
    d = re.fullmatch(r"(\d{4})年(\d+)月(\d+)(?:-(\d+))?日", date)
    t = re.fullmatch(r"(\d+):(\d+)-(\d+):(\d+)", time)
    if not (d and t):
        return None
    y, mon, d1, d2 = d.groups()
    return stamp(y, mon, d1, *t.groups()[:2]), stamp(y, mon, d2 or d1, *t.groups()[2:])


def expected_events(path):
    parser = TableParser()
    parser.feed(path.read_text(encoding="utf-8"))
    expected, warnings = {}, []
    for row in expand(parser.tables[0])[1:]:
        date, time, method, summary = (row + [""] * 4)[:4]
        if any(s in summary for s in SKIPPED):
            continue
        slot = parse_slot(date, time)
        if not slot or not summary:
            warnings.append(f"无法解析的行(需人工核对): {row}")
            continue
        start, end = slot
        if method in MERGED_STAGES:
            key = (start[:8], summary)
            if key in expected:
                start, end = min(expected[key][0], start), max(expected[key][1], end)
        else:
            key = (start, summary)
        expected[key] = (start, end, summary)
    return expected.values(), warnings


def check_coverage(events, months):
    have = {(e.get("DTSTART"), e.get("DTEND"), e.get("SUMMARY")) for e in events}
    for path in months:
        expected, warnings = expected_events(path)
        missing = [e for e in expected if e not in have]
        print(f"{path.name}: 公告场次 {len(expected)}，缺失 {len(missing)}")
        for w in warnings:
            print(f"  ! {w}")
        for start, end, summary in missing:
            errors.append(f"{path.name} 缺少事件: {start}-{end[9:]} {summary}")


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    notices = sorted(NOTICES.glob("*.md"))
    if arg == "--ics-only":
        months = []
    elif arg == "all":
        months = notices
    elif arg:
        months = [NOTICES / f"{arg}.md"]
    else:
        months = notices[-1:]

    events = parse_ics(ICS)
    lint(events)
    print(f"trade.ics: {len(events)} 个事件")
    check_coverage(events, months)

    for e in errors:
        print(f"✗ {e}")
    print("通过" if not errors else f"共 {len(errors)} 个错误")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
