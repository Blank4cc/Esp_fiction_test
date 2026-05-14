#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A级联赛（星脉挑战联赛）模拟器
=============================
逐轮模拟四赛区BO3比赛结果。每运行一次模拟一轮，支持回退。
输出为 Markdown 格式，含各赛区对阵结果表和积分榜。

赛制：东/西/南/北四赛区，每区5队，赛区内单循环（共5轮）。
模拟：Elo期望 + ±5%扰动 + 主场+3加成。
积分：2:0=3分 / 2:1=2分 / 1:2=1分 / 0:2=0分。
"""

import os
import random
import re
from datetime import date, timedelta

# ============================================================
# 赛季日历（与 schedule_a_league.py 一致）
# ============================================================
BREAKS = [
    (date(2052, 4,  4), date(2052, 4,  6), "清明节",  "🌿"),
    (date(2052, 5,  1), date(2052, 5,  5), "劳动节黄金周", "💼"),
    (date(2052, 6,  7), date(2052, 6,  9), "端午节",  "🐉"),
]
MID_SEASON = (date(2052, 6, 14), date(2052, 6, 27), "全球季中赛", "🏆")
TOTAL_ROUNDS = 5


def _is_break_day(d):
    for start, end, name, icon in BREAKS:
        if start <= d <= end:
            return True, name, icon
    ms_s, ms_e, ms_n, ms_i = MID_SEASON
    if ms_s <= d <= ms_e:
        return True, ms_n, ms_i
    return False, "", ""


def _precompute_a_dates():
    """预计算A级联赛5轮日期（周日）+ 休赛标记。"""
    start = date(2052, 3, 1)
    while start.weekday() != 6:
        start += timedelta(days=1)

    dates = []
    breaks_between = {}
    current = start

    for r in range(TOTAL_ROUNDS):
        skipped_set = {}
        while True:
            is_brk, brk_name, brk_icon = _is_break_day(current)
            if not is_brk:
                break
            if brk_name not in skipped_set:
                skipped_set[brk_name] = brk_icon
            current += timedelta(days=1)
            while current.weekday() != 6:
                current += timedelta(days=1)
        if skipped_set:
            breaks_between[r + 1] = " / ".join(f"{icon} {name}" for name, icon in skipped_set.items())
        dates.append(current)
        current += timedelta(days=7)

    return dates, breaks_between


ALL_A_DATES, BREAKS_A_AFTER = _precompute_a_dates()

# ============================================================
# 队伍数据（含强度值）
# ============================================================
A_EAST_SIM = [
    {"abbr": "WE",  "full": "波澜电竞 Wave Esports",        "city": "沪江市", "strength": 72},
    {"abbr": "FD",  "full": "东方霜华 Frost Dawn",           "city": "杭溪市", "strength": 75},
    {"abbr": "GW",  "full": "银河行者 Galaxy Walk",          "city": "津门市", "strength": 62},
    {"abbr": "HT",  "full": "浦江猛虎 Huangpu Tiger",        "city": "沪江市", "strength": 60},
    {"abbr": "DR",  "full": "晨光突击 Dawn Raid",            "city": "苏锦市", "strength": 65},
]

A_NORTH_SIM = [
    {"abbr": "GWall","full": "长城守卫 Great Wall",           "city": "北燕市", "strength": 60},
    {"abbr": "IR",   "full": "燕山铁骑 Iron Rider",           "city": "北燕市", "strength": 70},
    {"abbr": "CL",   "full": "海岸领主 Coastal Lord",         "city": "津门市", "strength": 65},
    {"abbr": "PLR",  "full": "北极星 Polaris",               "city": "盛京市", "strength": 63},
    {"abbr": "BT",   "full": "玄武重甲 Black Tortoise",       "city": "恒州市", "strength": 58},
]

A_SOUTH_SIM = [
    {"abbr": "SS",   "full": "南海涛声 South Sea",            "city": "粤城",   "strength": 73},
    {"abbr": "PR",   "full": "珠江骑士 Pearl River",          "city": "粤城",   "strength": 72},
    {"abbr": "MB",   "full": "红树湾 Mangrove Bay",           "city": "深南市", "strength": 63},
    {"abbr": "HE",   "full": "鹭港雄鹰 Heron Eagle",          "city": "鹭港市", "strength": 60},
    {"abbr": "CW",   "full": "椰风逐浪 Coconut Wind",         "city": "椰城市", "strength": 55},
]

A_WEST_SIM = [
    {"abbr": "MRD",  "full": "岷江飞龙 Min River Dragon",     "city": "蓉城",   "strength": 65},
    {"abbr": "GR",   "full": "三峡怒浪 Gorge Rush",           "city": "渝州市", "strength": 63},
    {"abbr": "CHF",  "full": "楚天鹰隼 Chu Falcon",           "city": "武川市", "strength": 68},
    {"abbr": "SHR",  "full": "蜀道行者 Shu Road",             "city": "锦官市", "strength": 58},
    {"abbr": "SR",   "full": "丝路骑兵 Silk Road",            "city": "长安市", "strength": 60},
]

REGIONS_SIM = {
    "东赛区": A_EAST_SIM,
    "北赛区": A_NORTH_SIM,
    "南赛区": A_SOUTH_SIM,
    "西赛区": A_WEST_SIM,
}

# ============================================================
# 赛程生成
# ============================================================
def generate_region_schedule(teams):
    """为5队赛区生成单循环赛程（5轮，每轮2场对阵）。"""
    n = len(teams)
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


# ============================================================
# 模拟算法
# ============================================================
def win_probability(team_a, team_b):
    s_a = team_a["strength"]
    s_b = team_b["strength"]
    prob = 1.0 / (1.0 + 10 ** ((s_b - s_a) / 25.0))
    prob += random.uniform(-0.05, 0.05)
    return max(0.0, min(1.0, prob))


def simulate_game(home_team, away_team, home_bonus=3):
    adjusted_home = dict(home_team)
    adjusted_home["strength"] = home_team["strength"] + home_bonus
    if random.random() < win_probability(adjusted_home, away_team):
        return home_team["abbr"]
    return away_team["abbr"]


def simulate_bo3(home_team, away_team):
    hw = 0
    aw = 0
    while hw < 2 and aw < 2:
        winner = simulate_game(home_team, away_team)
        if winner == home_team["abbr"]:
            hw += 1
        else:
            aw += 1
    if hw == 2:
        return home_team["abbr"], f"2:{aw}", away_team["abbr"]
    return away_team["abbr"], f"{hw}:2", home_team["abbr"]


def points_from_score(winner_abbr, score, my_abbr):
    if my_abbr == winner_abbr:
        return 3 if score in ("2:0", "0:2") else 2
    return 0 if score in ("2:0", "0:2") else 1


def update_standings_for_match(standings, home_team, away_team, winner_abbr, score):
    home_pts = points_from_score(winner_abbr, score, home_team["abbr"])
    away_pts = points_from_score(winner_abbr, score, away_team["abbr"])
    parts = score.split(":")
    h_gw = int(parts[0])
    h_gl = int(parts[1])

    standings[home_team["abbr"]]["pts"] += home_pts
    standings[home_team["abbr"]]["games_won"] += h_gw
    standings[home_team["abbr"]]["games_lost"] += h_gl
    if home_pts >= 2:
        standings[home_team["abbr"]]["wins"] += 1
    else:
        standings[home_team["abbr"]]["losses"] += 1

    standings[away_team["abbr"]]["pts"] += away_pts
    standings[away_team["abbr"]]["games_won"] += h_gl
    standings[away_team["abbr"]]["games_lost"] += h_gw
    if away_pts >= 2:
        standings[away_team["abbr"]]["wins"] += 1
    else:
        standings[away_team["abbr"]]["losses"] += 1


# ============================================================
# 文件读写与解析
# ============================================================
def get_output_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sim_a_league_output.md")


def read_existing_data(filepath):
    if not os.path.exists(filepath):
        return 0, ""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    rounds_done = len(re.findall(r'^## 第 \d+ 轮', content, re.MULTILINE))
    return rounds_done, content


def parse_all_standings(content):
    """从 Markdown 输出解析各赛区最新积分榜。
    
    每赛区的积分榜位于 `### 东赛区` 等标题下的 `#### 积分榜` 表格中。
    取每个赛区最后一次出现的积分榜（即累计值）。
    """
    all_standings = {}
    for region_name, teams in REGIONS_SIM.items():
        standings = {}
        for team in teams:
            standings[team["abbr"]] = {"pts": 0, "wins": 0, "losses": 0,
                                         "games_won": 0, "games_lost": 0}
        all_standings[region_name] = standings

    if not content:
        return all_standings

    lines = content.split("\n")
    
    # 对每个赛区，找到最后一个积分榜位置
    for region_name in REGIONS_SIM:
        # 从后往前找该赛区的积分榜
        last_table_start = -1
        for i in range(len(lines) - 1, -1, -1):
            if f"### {region_name}" in lines[i]:
                # 从这个赛区标题往后找积分榜
                for j in range(i, len(lines)):
                    if "#### 积分榜" in lines[j]:
                        last_table_start = j
                        break
                break

        if last_table_start < 0:
            continue

        # 解析积分榜表格
        in_table = False
        for i in range(last_table_start, len(lines)):
            line = lines[i].strip()
            if line.startswith("| # |") or line.startswith("|# |"):
                in_table = True
                continue
            if in_table and re.match(r'^\|[\-\s|]+\|$', line):
                continue
            if in_table and line.startswith("|"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 7:
                    abbr = parts[1].replace("**", "")
                    pts = int(parts[2])
                    wins = int(parts[3])
                    losses = int(parts[4])
                    sp = parts[5].split(":")
                    gw = int(sp[0])
                    gl = int(sp[1])
                    if abbr in all_standings[region_name]:
                        all_standings[region_name][abbr] = {
                            "pts": pts, "wins": wins, "losses": losses,
                            "games_won": gw, "games_lost": gl
                        }
            elif in_table and line == "":
                break

    return all_standings


# ============================================================
# Markdown 格式化
# ============================================================

def format_region_matches_md(region_name, teams, matches_results):
    """一个赛区的对阵结果 Markdown 表格。"""
    lines = []
    lines.append(f"### {region_name}")
    lines.append("")
    lines.append("#### 对阵结果")
    lines.append("")
    lines.append("| # | 主场 | 比分 | 客场 | 强度 |")
    lines.append("|---|------|------|------|------|")

    for i, (home_idx, away_idx, home_team, away_team, winner_abbr, score) in enumerate(matches_results, 1):
        home_full = f"**{home_team['abbr']}** {home_team['full']}"
        away_full = f"**{away_team['abbr']}** {away_team['full']}"
        if winner_abbr == home_team["abbr"]:
            home_full = f"🏆 {home_full}"
        else:
            away_full = f"🏆 {away_full}"
        lines.append(f"| {i} | {home_full} | {score} | {away_full} | {home_team['strength']} vs {away_team['strength']} |")

    lines.append("")
    return "\n".join(lines)


def format_region_standings_md(region_name, teams, standings_dict):
    """一个赛区的积分榜 Markdown 表格。"""
    table = []
    for team in teams:
        abbr = team["abbr"]
        s = standings_dict.get(abbr, {"pts": 0, "wins": 0, "losses": 0,
                                        "games_won": 0, "games_lost": 0})
        gd = s["games_won"] - s["games_lost"]
        table.append({
            "abbr": abbr,
            "full": team["full"],
            "pts": s["pts"], "wins": s["wins"], "losses": s["losses"],
            "gw": s["games_won"], "gl": s["games_lost"],
            "gd": gd, "strength": team["strength"],
        })

    table.sort(key=lambda x: (-x["pts"], -x["wins"], -x["gd"], -x["strength"]))

    lines = []
    lines.append("#### 积分榜")
    lines.append("")
    lines.append("| # | 战队 | 积分 | 胜 | 负 | 局分 | 局差 | 强度 |")
    lines.append("|---|------|------|-----|-----|------|------|------|")

    for rank, row in enumerate(table, 1):
        score_str = f"{row['gw']}:{row['gl']}"
        gd_str = f"+{row['gd']}" if row['gd'] >= 0 else str(row['gd'])
        # 查全名
        full = row['full']
        lines.append(f"| {rank} | **{row['abbr']}** {full} | {row['pts']} | {row['wins']} | {row['losses']} | {score_str} | {gd_str} | {row['strength']} |")

    lines.append("")
    return "\n".join(lines)


def format_full_round_md(round_num, match_date, all_matches_results, all_standings):
    """格式化完整一轮 Markdown 输出。"""
    lines = []
    lines.append(f"## 第 {round_num:02d} 轮")
    lines.append("")
    lines.append(f"> **日期**: {match_date}")
    lines.append("")

    for region_name, region_teams in REGIONS_SIM.items():
        results = all_matches_results[region_name]
        standings = all_standings[region_name]
        lines.append(format_region_matches_md(region_name, region_teams, results))
        lines.append(format_region_standings_md(region_name, region_teams, standings))

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# ============================================================
# 回退与主流程
# ============================================================

def delete_last_round(filepath, current_rounds):
    """删除最后一轮数据。"""
    if current_rounds == 0:
        print("[提示] 没有可回退的数据。")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r'^## 第 \d+ 轮'
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    if not matches:
        print("[提示] 没有可回退的数据。")
        return 0

    last_match_start = matches[-1].start()
    new_content = content[:last_match_start].rstrip() + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    new_count = max(0, current_rounds - 1)
    print(f"[回退] 已删除第 {current_rounds} 轮数据。当前剩余 {new_count} 轮。")
    return new_count


def simulate_one_round(round_num, all_schedules, all_standings):
    """模拟一轮所有赛区。返回 (results, standings, date_str, break_note)。"""
    d = ALL_A_DATES[round_num - 1]
    date_str = f"{d.strftime('%Y-%m-%d')}（周日）"
    break_note = BREAKS_A_AFTER.get(round_num + 1, "")

    all_matches_results = {}

    for region_name, region_teams in REGIONS_SIM.items():
        round_matches = all_schedules[region_name][round_num - 1]
        standings = all_standings[region_name]
        matches_results = []

        for home_idx, away_idx in round_matches:
            home_team = region_teams[home_idx]
            away_team = region_teams[away_idx]
            winner_abbr, score, _ = simulate_bo3(home_team, away_team)
            update_standings_for_match(standings, home_team, away_team, winner_abbr, score)
            matches_results.append((home_idx, away_idx, home_team, away_team, winner_abbr, score))

        all_matches_results[region_name] = matches_results

    return all_matches_results, all_standings, date_str, break_note


def main():
    output_path = get_output_path()

    all_schedules = {}
    for region_name, region_teams in REGIONS_SIM.items():
        all_schedules[region_name] = generate_region_schedule(region_teams)

    current_rounds, existing_content = read_existing_data(output_path)
    all_standings = parse_all_standings(existing_content)

    print("=" * 60)
    print("  A级联赛（星脉挑战联赛）模拟器")
    print(f"  当前进度: 已完成 {current_rounds} / {TOTAL_ROUNDS} 轮")
    print("=" * 60)

    while True:
        print()
        if current_rounds >= TOTAL_ROUNDS:
            print("[提示] 全部5轮已完成！无法继续模拟。")
            print("[提示] 可输入 'r' 回退上一轮。")
            print()

        print("  可选操作:")
        if current_rounds < TOTAL_ROUNDS:
            print(f"    n / next  — 模拟下一轮（第 {current_rounds + 1} 轮）")
        if current_rounds > 0:
            print(f"    r / rollback — 回退上一轮（删除第 {current_rounds} 轮）")
        print("    q / quit  — 退出")
        print()

        choice = input("  >>> ").strip().lower()

        if choice in ("q", "quit", "exit"):
            print("[退出] 再见。")
            break

        elif choice in ("r", "rollback"):
            if current_rounds == 0:
                print("[提示] 没有可回退的数据。")
                continue
            current_rounds = delete_last_round(output_path, current_rounds)
            _, updated_content = read_existing_data(output_path)
            all_standings = parse_all_standings(updated_content)
            continue

        elif choice in ("n", "next", ""):
            if current_rounds >= TOTAL_ROUNDS:
                print("[提示] 全部5轮已完成！")
                continue

            round_num = current_rounds + 1
            print(f"\n[模拟中] 正在模拟第 {round_num} 轮...")

            all_matches_results, all_standings, date_str, break_note = simulate_one_round(
                round_num, all_schedules, all_standings
            )

            round_output = format_full_round_md(
                round_num, date_str, all_matches_results, all_standings
            )
            if break_note:
                round_output += f"\n> ⏸ **下轮休赛**：{break_note}\n"

            with open(output_path, "a", encoding="utf-8") as f:
                if current_rounds == 0:
                    header = "# A级联赛（星脉挑战联赛）— 模拟战报\n\n"
                    header += "> **赛季**: S7 | **赛区**: 东/西/南/北 × 5支战队 | **赛制**: 赛区内单循环 | **场次**: BO3 | **共**: 5轮\n\n"
                    header += "---\n\n"
                    f.write(header)
                f.write(round_output)

            current_rounds = round_num
            print(f"[完成] 第 {round_num} 轮已模拟并写入文件。")
            print(f"  文件路径: {output_path}")

        else:
            print(f"[错误] 未知操作: '{choice}'。请输入 n/r/q。")


if __name__ == "__main__":
    main()
