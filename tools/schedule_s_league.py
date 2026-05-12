#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级联赛（星脉超级联赛）赛程生成器
===============================
根据 league_structure.md 和 teams_archive.md 的数据，
一键生成16支战队双循环30轮完整赛程，输出为 txt 表格格式。

赛制：双循环（主客场各一次），每轮8场对阵，共30轮。
"""

import os
from datetime import date, timedelta

# ============================================================
# 数据区：16支S级战队（按编号排列，非积分排名）
# ============================================================
S_TEAMS = [
    {"id": "S-01", "abbr": "PV",    "full": "幻界战队 PHANTOM VOID",        "city": "沪江市"},
    {"id": "S-02", "abbr": "IC",    "full": "北燕皇朝 IMPERIAL CROWN",      "city": "北燕市"},
    {"id": "S-03", "abbr": "NS",    "full": "深南闪电 NEON SPARK",           "city": "深南市"},
    {"id": "S-04", "abbr": "BF",    "full": "粤城烈焰 BLAZING FIRE",         "city": "粤城"},
    {"id": "S-05", "abbr": "TR",    "full": "蓉城咆哮 THUNDER ROAR",         "city": "蓉城"},
    {"id": "S-06", "abbr": "DT",    "full": "杭溪数码 DIGITAL TIDE",         "city": "杭溪市"},
    {"id": "S-07", "abbr": "IB",    "full": "武川铁甲 IRON BASTION",         "city": "武川市"},
    {"id": "S-08", "abbr": "DG",    "full": "渝州龙门 DRAGON GATE",          "city": "渝州市"},
    {"id": "S-09", "abbr": "SW",    "full": "津门钢铁 STEEL WALL",           "city": "津门市"},
    {"id": "S-10", "abbr": "CF",    "full": "锦官凤羽 CRIMSON FEATHER",      "city": "锦官市"},
    {"id": "S-11", "abbr": "StarW", "full": "静海星澜 STARWAVE",             "city": "沪江市"},
    {"id": "S-12", "abbr": "PS",    "full": "北燕幽影 PHANTOM SHADE",        "city": "北燕市"},
    {"id": "S-13", "abbr": "ET",    "full": "东渡潮浪 EASTERN TIDE",         "city": "沪江市"},
    {"id": "S-14", "abbr": "BS",    "full": "渤海风暴 BOHAI STORM",          "city": "津门市"},
    {"id": "S-15", "abbr": "HPE",   "full": "云贵高原鹰 HIGHPEAK EAGLE",     "city": "巡回主场"},
    {"id": "S-16", "abbr": "AA",    "full": "沪江星辰学院 ASTERIA ACADEMY",  "city": "沪江市"},
]


def generate_round_robin_schedule(teams):
    """
    使用圆圈法（Circle Method）生成双循环赛程。

    算法说明：
    - 将16队编号0~15，固定第15号（最后一队），其余15队围成圆圈。
    - 每轮中，固定队 vs 圆圈中某队，其余队按对称配对。
    - 前半程（1~15轮）生成所有不同的对阵组合。
    - 后半程（16~30轮）将主客场对调。

    返回: list of list of (home_idx, away_idx)
    """
    n = len(teams)
    if n % 2 != 0:
        raise ValueError("队伍数必须为偶数")

    half_rounds = n - 1  # 15轮
    all_rounds = []

    # 圆圈法生成前半程
    # fixed_team = n-1 (第16队), circle = teams[0..n-2] (前15队)
    fixed = n - 1
    circle = list(range(n - 1))

    for r in range(half_rounds):
        round_matches = []

        # 固定队对阵 circle[r]
        if r % 2 == 0:
            round_matches.append((circle[r], fixed))
        else:
            round_matches.append((fixed, circle[r]))

        # 其余队伍对称配对
        # circle中，从r出发，配对: (r+1) vs (r-1), (r+2) vs (r-2), ...
        for i in range(1, n // 2):
            left = (r + i) % (n - 1)
            right = (r - i) % (n - 1)
            if i % 2 == 1:
                round_matches.append((circle[left], circle[right]))
            else:
                round_matches.append((circle[right], circle[left]))

        all_rounds.append(round_matches)

    # 后半程：相同的对阵，主客场对调
    for r in range(half_rounds):
        first_half = all_rounds[r]
        second_half = [(away, home) for (home, away) in first_half]
        all_rounds.append(second_half)

    return all_rounds


def generate_dates(start_date, num_rounds):
    """
    生成赛程日期序列。

    S级联赛常规赛约20周，30轮。
    策略：每周六为主比赛日，部分周三加赛（前半程较快，后半程放缓）。
    第1~10轮：每周六+周三（快节奏，约5周）
    第11~30轮：每周六（约20周）
    """
    dates = []
    current = start_date
    fast_rounds = 10

    for r in range(num_rounds):
        if r < fast_rounds:
            # 快节奏：周三/周六交替
            if r % 2 == 0:
                # 周六
                while current.weekday() != 5:  # 周六=5
                    current += timedelta(days=1)
            else:
                # 下周三
                while current.weekday() != 2:  # 周三=2
                    current += timedelta(days=1)
        else:
            # 慢节奏：每周六
            while current.weekday() != 5:
                current += timedelta(days=1)

        dates.append(current)
        current += timedelta(days=1)  # 移动到下一天，避免重复

    return dates


def format_schedule_txt(teams, all_rounds, dates):
    """将赛程格式化为txt表格字符串。"""
    lines = []
    lines.append("=" * 100)
    lines.append("  S级联赛（星脉超级联赛）— 完整赛程")
    lines.append("  赛季: S7 | 16支战队 | 双循环 | 共30轮 | BO2")
    lines.append("=" * 100)
    lines.append("")

    for round_idx, (round_matches, match_date) in enumerate(zip(all_rounds, dates)):
        lines.append(f"{'─' * 80}")
        lines.append(f"  第 {round_idx + 1:02d} 轮  |  日期: {match_date.strftime('%Y-%m-%d')}（{['周一','周二','周三','周四','周五','周六','周日'][match_date.weekday()]}）")
        lines.append(f"{'─' * 80}")

        # 表头
        lines.append(f"  {'主场战队':<30s} {'':>3s}  {'客场战队':<30s}  {'主场城市':<12s}")
        lines.append(f"  {'─' * 30} {'─' * 3}  {'─' * 30}  {'─' * 12}")

        for home_idx, away_idx in round_matches:
            home_team = teams[home_idx]
            away_team = teams[away_idx]
            home_full = f"{home_team['abbr']} {home_team['full']}"
            away_full = f"{away_team['abbr']} {away_team['full']}"
            lines.append(f"  {home_full:<30s}  vs  {away_full:<30s}  {home_team['city']:<12s}")

        lines.append("")

    # 统计信息
    lines.append("=" * 100)
    lines.append("  统计摘要")
    lines.append("=" * 100)
    lines.append(f"  总轮次: {len(all_rounds)}")
    lines.append(f"  总场次: {len(all_rounds) * len(all_rounds[0])}")
    lines.append(f"  起始日期: {dates[0].strftime('%Y-%m-%d')}")
    lines.append(f"  结束日期: {dates[-1].strftime('%Y-%m-%d')}")
    lines.append(f"  每队比赛场数: {(len(teams) - 1) * 2}")
    lines.append("")

    # 队名对照
    lines.append("=" * 100)
    lines.append("  战队缩写对照表")
    lines.append("=" * 100)
    for t in teams:
        lines.append(f"  {t['abbr']:<6s} = {t['full']}")

    return "\n".join(lines)


def main():
    # 生成赛程
    all_rounds = generate_round_robin_schedule(S_TEAMS)

    # 生成日期：假设赛季从3月第一个周六开始
    season_start = date(2025, 3, 1)
    while season_start.weekday() != 5:
        season_start += timedelta(days=1)

    dates = generate_dates(season_start, len(all_rounds))

    # 格式化输出
    output = format_schedule_txt(S_TEAMS, all_rounds, dates)

    # 写入文件
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "schedule_s_league_output.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"[完成] S级联赛赛程已生成 → {output_path}")
    print(f"  共 {len(all_rounds)} 轮，{len(all_rounds) * 8} 场对阵")


if __name__ == "__main__":
    main()
