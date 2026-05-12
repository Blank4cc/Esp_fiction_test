#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A级联赛（星脉挑战联赛）赛程生成器
=================================
根据 league_structure.md 和 teams_archive.md 的数据，
一键生成东/西/南/北四赛区单循环完整赛程，输出为 txt 表格格式。

赛制：4赛区 × 5支战队，赛区内单循环（每队打4场，5轮，每轮2场+1队轮空）。
"""

import os
from datetime import date, timedelta

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
    """为一个赛区生成完整的单循环赛程矩阵。
    
    5队单循环：添加虚拟队（bye），使用通用圆圈法生成6队双循环对阵，
    然后过滤掉含虚拟队的对阵。每轮产生2场实对阵 + 1队轮空。
    共5轮，每队打4场。
    """
    n = len(teams)
    if n % 2 == 0:
        # 偶数队：标准圆圈法
        fixed = n - 1
        circle = list(range(n - 1))
        total_rounds = n - 1
        rounds = []
        for r in range(total_rounds):
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
        # 奇数队（5队）：添加虚拟队，扩为6队（偶数）
        dummy_idx = n  # 虚拟队编号
        extended_n = n + 1
        fixed = dummy_idx  # 虚拟队作为固定队
        circle = list(range(n))  # 5个实队: [0,1,2,3,4]
        total_rounds = n  # 5轮
        rounds = []

        for r in range(total_rounds):
            round_matches = []
            # 虚拟队的对手本轮轮空
            # 其余4队配对成2场
            by_idx = circle[r % n]  # 本轮轮空队

            # 其余队伍配对
            for i in range(1, (n - 1) // 2 + 1):  # i=1 (n=5时 n-1=4, (n-1)//2=2)
                left = (r + i) % n
                right = (r - i) % n
                if i % 2 == 1:
                    round_matches.append((circle[left], circle[right]))
                else:
                    round_matches.append((circle[right], circle[left]))

            round_matches.sort(key=lambda m: m[0])
            rounds.append(round_matches)

        return rounds


def generate_dates_a(num_regions, rounds_per_region):
    """
    A级联赛日期生成。
    四赛区同时进行，每周一轮，与S级联赛同期（3月~7月）。
    共5轮（赛区赛），后续总决赛另行安排。
    """
    start = date(2025, 3, 1)
    while start.weekday() != 6:  # 周日
        start += timedelta(days=1)

    dates = []
    current = start
    for _ in range(rounds_per_region):
        dates.append(current)
        current += timedelta(days=7)  # 每周日

    return dates


def format_a_schedule_txt(regions, all_schedules, dates):
    """将A级联赛赛程格式化为txt。"""
    lines = []
    lines.append("=" * 100)
    lines.append("  A级联赛（星脉挑战联赛）— 完整赛程（赛区赛阶段）")
    lines.append("  赛季: S7 | 4赛区 × 5支战队 | 赛区内单循环 | 共5轮")
    lines.append("=" * 100)
    lines.append("")

    # 按轮次输出（所有赛区在同一轮）
    num_rounds = len(dates)
    for r in range(num_rounds):
        lines.append(f"{'─' * 80}")
        lines.append(f"  第 {r + 1} 轮  |  日期: {dates[r].strftime('%Y-%m-%d')}（周日）")
        lines.append(f"{'─' * 80}")

        for region_name, region_teams in regions.items():
            schedule = all_schedules[region_name]
            round_matches = schedule[r]

            lines.append(f"  ▸ {region_name}")
            lines.append(f"    {'主场战队':<30s} {'':>3s}  {'客场战队':<30s}  {'主场城市':<16s}")
            lines.append(f"    {'─' * 30} {'─' * 3}  {'─' * 30}  {'─' * 16}")

            for home_idx, away_idx in round_matches:
                home_team = region_teams[home_idx]
                away_team = region_teams[away_idx]
                home_full = f"{home_team['abbr']} {home_team['full']}"
                away_full = f"{away_team['abbr']} {away_team['full']}"
                lines.append(f"    {home_full:<30s}  vs  {away_full:<30s}  {home_team['city']:<16s}")

            lines.append("")

        lines.append("")

    # 统计信息
    lines.append("=" * 100)
    lines.append("  统计摘要")
    lines.append("=" * 100)
    for region_name, region_teams in regions.items():
        lines.append(f"  {region_name}: {len(region_teams)}队, {num_rounds}轮, {num_rounds * 2}场对阵")
    lines.append("")
    lines.append("  注：赛区赛结束后，各赛区前2名（共8队）进入A级全国总决赛（单败淘汰BO3）。")
    lines.append("  总决赛赛程另行安排。")
    lines.append("")

    # 队名对照
    lines.append("=" * 100)
    lines.append("  战队缩写对照表")
    lines.append("=" * 100)
    for region_name, region_teams in regions.items():
        lines.append(f"  [{region_name}]")
        for t in region_teams:
            lines.append(f"    {t['abbr']:<6s} = {t['full']}")

    return "\n".join(lines)


def main():
    # 为每个赛区生成赛程
    all_schedules = {}
    for region_name, region_teams in REGIONS.items():
        all_schedules[region_name] = generate_schedule_for_region(region_teams)

    # 生成日期（各赛区同一天比赛）
    dates = generate_dates_a(4, 5)

    # 格式化输出
    output = format_a_schedule_txt(REGIONS, all_schedules, dates)

    # 写入文件
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "schedule_a_league_output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"[完成] A级联赛赛程已生成 → {output_path}")
    print(f"  共 4 赛区，每赛区 5 轮，总计 40 场对阵")


if __name__ == "__main__":
    main()
