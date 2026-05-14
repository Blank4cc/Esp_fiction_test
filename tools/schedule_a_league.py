#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A级联赛（星脉挑战联赛）赛程生成器
=================================
根据 league_structure.md 和 teams_archive.md 的数据，
一键生成东/西/南/北四赛区单循环完整赛程，输出为 Markdown 表格格式。

赛制：4赛区 × 5支战队，赛区内单循环（每队打4场，5轮，每轮2场+1队轮空）。
赛程中预留：清明节、劳动节、端午节休赛 + 季中赛两周空档。
"""

import os
from datetime import date, timedelta

# ============================================================
# 赛季日历常量（2052年，与S级联赛一致）
# ============================================================
BREAKS = [
    (date(2052, 4,  4), date(2052, 4,  6), "清明节",  "🌿"),
    (date(2052, 5,  1), date(2052, 5,  5), "劳动节黄金周", "💼"),
    (date(2052, 6,  7), date(2052, 6,  9), "端午节",  "🐉"),
]
MID_SEASON_BREAK = (date(2052, 6, 14), date(2052, 6, 27), "全球季中赛", "🏆")


def is_break_day(d):
    for start, end, name, icon in BREAKS:
        if start <= d <= end:
            return True, name, icon
    ms_start, ms_end, ms_name, ms_icon = MID_SEASON_BREAK
    if ms_start <= d <= ms_end:
        return True, ms_name, ms_icon
    return False, "", ""


# ============================================================
# 数据区：A级联赛四赛区战队
# ============================================================
A_EAST = [
    {"abbr": "WE",  "full": "波澜电竞 Wave Esports",        "city": "沪江市（杨江区）"},
    {"abbr": "FD",  "full": "东方霜华 Frost Dawn",           "city": "杭溪市"},
    {"abbr": "GW",  "full": "银河行者 Galaxy Walk",          "city": "津门市"},
    {"abbr": "HT",  "full": "浦江猛虎 Huangpu Tiger",        "city": "沪江市（皇浦区）"},
    {"abbr": "DR",  "full": "晨光突击 Dawn Raid",            "city": "苏锦市"},
]
A_NORTH = [
    {"abbr": "GWall","full": "长城守卫 Great Wall",           "city": "北燕市（朝阳区）"},
    {"abbr": "IR",   "full": "燕山铁骑 Iron Rider",           "city": "北燕市（顺义）"},
    {"abbr": "CL",   "full": "海岸领主 Coastal Lord",         "city": "津门市附近"},
    {"abbr": "PLR",  "full": "北极星 Polaris",               "city": "盛京市"},
    {"abbr": "BT",   "full": "玄武重甲 Black Tortoise",       "city": "恒州市"},
]
A_SOUTH = [
    {"abbr": "SS",   "full": "南海涛声 South Sea",            "city": "粤城（番禺）"},
    {"abbr": "PR",   "full": "珠江骑士 Pearl River",          "city": "粤城"},
    {"abbr": "MB",   "full": "红树湾 Mangrove Bay",           "city": "深南市（福田）"},
    {"abbr": "HE",   "full": "鹭港雄鹰 Heron Eagle",          "city": "鹭港市"},
    {"abbr": "CW",   "full": "椰风逐浪 Coconut Wind",         "city": "椰城市"},
]
A_WEST = [
    {"abbr": "MRD",  "full": "岷江飞龙 Min River Dragon",     "city": "蓉城（青羊区）"},
    {"abbr": "GR",   "full": "三峡怒浪 Gorge Rush",           "city": "渝州市"},
    {"abbr": "CHF",  "full": "楚天鹰隼 Chu Falcon",           "city": "武川市"},
    {"abbr": "SHR",  "full": "蜀道行者 Shu Road",             "city": "锦官市"},
    {"abbr": "SR",   "full": "丝路骑兵 Silk Road",            "city": "长安市"},
]

REGIONS = {
    "东赛区": A_EAST,
    "北赛区": A_NORTH,
    "南赛区": A_SOUTH,
    "西赛区": A_WEST,
}


def generate_schedule_for_region(teams):
    """为5队赛区生成单循环赛程（5轮，每轮2场）。"""
    n = len(teams)
    if n % 2 == 0:
        fixed = n - 1
        circle = list(range(n - 1))
        rounds = []
        for r in range(n - 1):
            round_matches = []
            opponent_fixed = circle[r % (n - 1)]
            if r % 2 == 0:
                round_matches.append((opponent_fixed, fixed))
            else:
                round_matches.append((fixed, opponent_fixed))
            for i in range(1, n // 2):
                left = (r + i) % (n - 1)
                right = (r - i) % (n - 1)
                if i % 2 == 1:
                    round_matches.append((circle[left], circle[right]))
                else:
                    round_matches.append((circle[right], circle[left]))
            round_matches.sort(key=lambda m: m[0])
            rounds.append(round_matches)
        return rounds
    else:
        circle = list(range(n))
        rounds = []
        for r in range(n):
            round_matches = []
            for i in range(1, n // 2 + 1):
                left = (r + i) % n
                right = (r - i) % n
                if i % 2 == 1:
                    round_matches.append((circle[left], circle[right]))
                else:
                    round_matches.append((circle[right], circle[left]))
            round_matches.sort(key=lambda m: m[0])
            rounds.append(round_matches)
        return rounds


def generate_dates_a(num_rounds):
    """
    生成A级联赛日期（每周日），跳过休赛期。
    返回 (dates, breaks_between)。
    """
    start = date(2052, 3, 1)
    while start.weekday() != 6:
        start += timedelta(days=1)

    dates = []
    breaks_between = []
    current = start

    for r in range(num_rounds):
        skipped_set = {}
        while True:
            is_brk, brk_name, brk_icon = is_break_day(current)
            if not is_brk:
                break
            if brk_name not in skipped_set:
                skipped_set[brk_name] = brk_icon
            current += timedelta(days=1)
            while current.weekday() != 6:
                current += timedelta(days=1)

        if skipped_set:
            combined = " / ".join(f"{icon} {name}" for name, icon in skipped_set.items())
            breaks_between.append((r + 1, combined))

        dates.append(current)
        current += timedelta(days=7)

    return dates, breaks_between


def format_a_schedule_md(regions, all_schedules, dates, breaks_between):
    """格式化 A 级赛程为 Markdown。"""
    lines = []

    lines.append("# A级联赛（星脉挑战联赛）— 完整赛程（赛区赛阶段）")
    lines.append("")
    lines.append(f"> **赛季**: S7 | **赛区**: 东/西/南/北 × 5支战队 | **赛制**: 赛区内单循环 | **共**: {len(dates)}轮 | **单场**: BO3")
    lines.append("")

    # 休赛日历
    lines.append("## 休赛日历")
    lines.append("")
    lines.append("| 时间段 | 说明 |")
    lines.append("|--------|------|")
    for start, end, name, icon in BREAKS:
        lines.append(f"| {icon} {start.strftime('%m/%d')}–{end.strftime('%m/%d')} | {name} |")
    ms_start, ms_end, ms_name, ms_icon = MID_SEASON_BREAK
    lines.append(f"| {ms_icon} {ms_start.strftime('%m/%d')}–{ms_end.strftime('%m/%d')} | {ms_name} |")
    lines.append("")
    lines.append("---")
    lines.append("")

    break_map = {after_r: desc for after_r, desc in breaks_between}

    for r in range(len(dates)):
        lines.append(f"## 第 {r + 1} 轮 — {dates[r].strftime('%Y-%m-%d')}（周日）")
        lines.append("")

        for region_name, region_teams in regions.items():
            schedule = all_schedules[region_name]
            round_matches = schedule[r]
            lines.append(f"### {region_name}")
            lines.append("")
            lines.append("| # | 主场战队 | | 客场战队 | 主场城市 |")
            lines.append("|---|----------|---|----------|----------|")
            for i, (home_idx, away_idx) in enumerate(round_matches, 1):
                home_team = region_teams[home_idx]
                away_team = region_teams[away_idx]
                home_full = f"**{home_team['abbr']}** {home_team['full']}"
                away_full = f"**{away_team['abbr']}** {away_team['full']}"
                lines.append(f"| {i} | {home_full} | vs | {away_full} | {home_team['city']} |")
            lines.append("")

        after_r = r + 1
        if after_r in break_map:
            lines.append(f"> ⏸ **休赛**：{break_map[after_r]}")
            lines.append("")

        lines.append("---")
        lines.append("")

    # 统计摘要
    lines.append("## 统计摘要")
    lines.append("")
    lines.append("| 赛区 | 队伍数 | 轮次 | 总场次 |")
    lines.append("|------|--------|------|--------|")
    for region_name, region_teams in regions.items():
        lines.append(f"| {region_name} | {len(region_teams)} | {len(dates)} | {len(dates) * 2} |")
    lines.append("")
    lines.append("> **注**：赛区赛结束后，各赛区前2名（共8队）进入A级全国总决赛（单败淘汰BO3）。总决赛赛程另行安排。")
    lines.append("")

    # 战队缩写对照
    lines.append("---")
    lines.append("")
    lines.append("## 战队缩写对照表")
    lines.append("")
    for region_name, region_teams in regions.items():
        lines.append(f"### {region_name}")
        lines.append("")
        lines.append("| 缩写 | 全称 | 城市 |")
        lines.append("|------|------|------|")
        for t in region_teams:
            lines.append(f"| **{t['abbr']}** | {t['full']} | {t['city']} |")
        lines.append("")

    return "\n".join(lines)


def main():
    all_schedules = {}
    for region_name, region_teams in REGIONS.items():
        all_schedules[region_name] = generate_schedule_for_region(region_teams)

    dates, breaks_between = generate_dates_a(5)
    output = format_a_schedule_md(REGIONS, all_schedules, dates, breaks_between)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "schedule_a_league_output.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"[完成] A级联赛赛程已生成 → {output_path}")
    print(f"  共 4 赛区，每赛区 5 轮，总计 40 场对阵")
    for after_r, desc in breaks_between:
        print(f"  ⏸ 第 {after_r - 1} 轮后：{desc}")


if __name__ == "__main__":
    main()
