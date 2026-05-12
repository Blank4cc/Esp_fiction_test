#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A级联赛（星脉挑战联赛）模拟器
=============================
基于 schedule_a_league.py 生成的赛程，逐轮模拟四个赛区的BO3比赛结果。
每运行一次模拟一轮，支持回退（删除最新一轮结果）。

赛制：东/西/南/北四赛区，每区5队，赛区内单循环（共5轮）。
每轮每赛区2场对阵+1队轮空。

模拟机制：
- 每支战队有一个强度值（0~100），决定胜负概率。
- 使用 Elo 期望公式：P(A胜) = 1 / (1 + 10^((s_B - s_A) / 25))
- 附带随机扰动（±5%）。
- BO3：三局两胜制，逐局模拟。

积分规则：
- 2:0 获胜 → 3分
- 2:1 获胜 → 2分
- 1:2 落败 → 1分
- 0:2 落败 → 0分

排名规则（赛区内）：积分优先 → 胜场数 → 局分差 → 缩写字母序

输出：tools/sim_a_league_output.txt，每轮含四赛区对阵结果表和积分榜。
"""

import os
import sys
import random
from datetime import date, timedelta

# ============================================================
# 队伍数据（含强度值）
# ============================================================

A_EAST_SIM = [
    {"abbr": "WE",  "full": "波澜电竞 Wave Esports",        "city": "沪江市",     "strength": 72},
    {"abbr": "FD",  "full": "东方霜华 Frost Dawn",           "city": "杭溪市",     "strength": 75},
    {"abbr": "GW",  "full": "银河行者 Galaxy Walk",          "city": "津门市",     "strength": 62},
    {"abbr": "HT",  "full": "浦江猛虎 Huangpu Tiger",        "city": "沪江市",     "strength": 60},
    {"abbr": "DR",  "full": "晨光突击 Dawn Raid",            "city": "苏锦市",     "strength": 65},
]

A_NORTH_SIM = [
    {"abbr": "GWall","full": "长城守卫 Great Wall",           "city": "北燕市",     "strength": 60},
    {"abbr": "IR",   "full": "燕山铁骑 Iron Rider",           "city": "北燕市",     "strength": 70},
    {"abbr": "CL",   "full": "海岸领主 Coastal Lord",         "city": "津门市",     "strength": 65},
    {"abbr": "PLR",  "full": "北极星 Polaris",               "city": "盛京市",     "strength": 63},
    {"abbr": "BT",   "full": "玄武重甲 Black Tortoise",       "city": "恒州市",     "strength": 58},
]

A_SOUTH_SIM = [
    {"abbr": "SS",   "full": "南海涛声 South Sea",            "city": "粤城",       "strength": 73},
    {"abbr": "PR",   "full": "珠江骑士 Pearl River",          "city": "粤城",       "strength": 72},
    {"abbr": "MB",   "full": "红树湾 Mangrove Bay",           "city": "深南市",     "strength": 63},
    {"abbr": "HE",   "full": "鹭港雄鹰 Heron Eagle",          "city": "鹭港市",     "strength": 60},
    {"abbr": "CW",   "full": "椰风逐浪 Coconut Wind",         "city": "椰城市",     "strength": 55},
]

A_WEST_SIM = [
    {"abbr": "MRD",  "full": "岷江飞龙 Min River Dragon",     "city": "蓉城",       "strength": 65},
    {"abbr": "GR",   "full": "三峡怒浪 Gorge Rush",           "city": "渝州市",     "strength": 63},
    {"abbr": "CHF",  "full": "楚天鹰隼 Chu Falcon",           "city": "武川市",     "strength": 68},
    {"abbr": "SHR",  "full": "蜀道行者 Shu Road",             "city": "锦官市",     "strength": 58},
    {"abbr": "SR",   "full": "丝路骑兵 Silk Road",            "city": "长安市",     "strength": 60},
]

REGIONS_SIM = {
    "东赛区": A_EAST_SIM,
    "北赛区": A_NORTH_SIM,
    "南赛区": A_SOUTH_SIM,
    "西赛区": A_WEST_SIM,
}

TOTAL_ROUNDS = 5  # 每赛区5轮单循环


# ============================================================
# 赛程生成（与 schedule_a_league.py 一致）
# ============================================================

def generate_region_schedule(teams):
    """为5队赛区生成单循环赛程（5轮，每轮2场对阵）。使用圆圈法+虚拟队。"""
    n = len(teams)
    dummy_idx = n  # 虚拟队
    circle = list(range(n))  # [0,1,2,3,4]
    rounds = []

    for r in range(n):  # 5轮
        round_matches = []
        # 虚拟队本轮对阵的实队轮空
        # 其余4队配对
        for i in range(1, n // 2 + 1):  # i=1,2 (n=5时 n//2=2)
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
# 模拟算法（与 S级模拟器一致）
# ============================================================

def win_probability(team_a, team_b):
    """计算Team A战胜Team B的概率。"""
    s_a = team_a["strength"]
    s_b = team_b["strength"]
    prob = 1.0 / (1.0 + 10 ** ((s_b - s_a) / 25.0))
    prob += random.uniform(-0.05, 0.05)
    return max(0.0, min(1.0, prob))


def simulate_game(home_team, away_team, home_bonus=3):
    """模拟一局比赛，主场加成3点强度。"""
    adjusted_home = dict(home_team)
    adjusted_home["strength"] = home_team["strength"] + home_bonus
    prob = win_probability(adjusted_home, away_team)
    if random.random() < prob:
        return home_team["abbr"]
    else:
        return away_team["abbr"]


def simulate_bo3(home_team, away_team):
    """模拟BO3，返回(胜者abbr, 比分字符串, 败者abbr)。"""
    home_wins = 0
    away_wins = 0

    while home_wins < 2 and away_wins < 2:
        winner = simulate_game(home_team, away_team)
        if winner == home_team["abbr"]:
            home_wins += 1
        else:
            away_wins += 1

    if home_wins == 2:
        return home_team["abbr"], f"2:{away_wins}", away_team["abbr"]
    else:
        return away_team["abbr"], f"{home_wins}:2", home_team["abbr"]


def points_from_score(winner_abbr, score, my_abbr):
    """根据比分计算积分。"""
    if my_abbr == winner_abbr:
        if score in ("2:0", "0:2"):
            return 3
        else:
            return 2
    else:
        if score in ("2:0", "0:2"):
            return 0
        else:
            return 1


def update_standings_for_match(standings, home_team, away_team, winner_abbr, score):
    """根据比赛结果更新积分榜。"""
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
# 文件读写
# ============================================================

def get_output_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sim_a_league_output.txt")


def read_existing_data(filepath):
    """读取已有数据，返回（已完成轮数, 文件内容）。"""
    if not os.path.exists(filepath):
        return 0, ""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    rounds_done = content.count("═══ 第")
    return rounds_done, content


def parse_all_standings(content):
    """从已有输出中解析各赛区最新积分榜。
    返回 {region_name: {abbr: {pts, wins, losses, games_won, games_lost}}}"""
    all_standings = {}
    for region_name, teams in REGIONS_SIM.items():
        standings = {}
        for team in teams:
            standings[team["abbr"]] = {
                "pts": 0, "wins": 0, "losses": 0,
                "games_won": 0, "games_lost": 0
            }
        all_standings[region_name] = standings

    if not content:
        return all_standings

    lines = content.split("\n")
    current_region = None

    for i, line in enumerate(lines):
        # 识别赛区标题
        for rname in REGIONS_SIM:
            if f"▸ {rname}" in line:
                current_region = rname
                break

        if current_region and "排名" in line:
            # 解析该赛区的积分榜
            for j in range(i + 1, min(i + 20, len(lines))):
                data_line = lines[j].strip()
                if not data_line or data_line.startswith("└"):
                    break
                if data_line.startswith("├") or data_line.startswith("│ #"):
                    continue
                if data_line.startswith("│"):
                    parts = [p.strip() for p in data_line.split("│") if p.strip()]
                    if len(parts) >= 6:
                        abbr = parts[1]
                        pts = int(parts[2])
                        wins = int(parts[3])
                        losses = int(parts[4])
                        score_parts = parts[5].split(":")
                        gw = int(score_parts[0])
                        gl = int(score_parts[1])
                        if abbr in all_standings[current_region]:
                            all_standings[current_region][abbr] = {
                                "pts": pts, "wins": wins, "losses": losses,
                                "games_won": gw, "games_lost": gl
                            }

    return all_standings


# ============================================================
# 格式化输出
# ============================================================

def format_region_matches(region_name, teams, round_matches, matches_results):
    """格式化一个赛区的对阵结果。"""
    lines = []
    lines.append(f"  ▸ {region_name}")
    lines.append("  ┌─ 对阵结果 " + "─" * 54 + "┐")
    lines.append(f"  │ {'主场':<18s} │ {'比分':>5s} │ {'客场':<18s} │ {'强度':>12s} │")
    lines.append("  ├" + "─" * 20 + "┼" + "─" * 7 + "┼" + "─" * 20 + "┼" + "─" * 14 + "┤")

    for home_idx, away_idx, home_team, away_team, winner_abbr, score in matches_results:
        home_str = f"{home_team['abbr']}"
        away_str = f"{away_team['abbr']}"
        if len(home_str) > 16:
            home_str = home_str[:15]
        if len(away_str) > 16:
            away_str = away_str[:15]
        strength_str = f"{home_team['strength']} vs {away_team['strength']}"
        if winner_abbr == home_team["abbr"]:
            home_str = f"★{home_str}"
        else:
            away_str = f"★{away_str}"
        lines.append(f"  │ {home_str:<17s} │ {score:>5s} │ {away_str:<17s} │ {strength_str:>12s} │")

    lines.append("  └" + "─" * 20 + "┴" + "─" * 7 + "┴" + "─" * 20 + "┴" + "─" * 14 + "┘")
    return "\n".join(lines)


def format_region_standings(region_name, teams, standings_dict):
    """格式化一个赛区的积分榜。"""
    table = []
    for team in teams:
        abbr = team["abbr"]
        s = standings_dict.get(abbr, {"pts": 0, "wins": 0, "losses": 0,
                                       "games_won": 0, "games_lost": 0})
        gd = s["games_won"] - s["games_lost"]
        table.append({
            "abbr": abbr,
            "pts": s["pts"],
            "wins": s["wins"],
            "losses": s["losses"],
            "games_won": s["games_won"],
            "games_lost": s["games_lost"],
            "gd": gd,
            "strength": team["strength"],
        })

    table.sort(key=lambda x: (-x["pts"], -x["wins"], -x["gd"], -x["strength"]))

    lines = []
    lines.append(f"  ▸ {region_name} 积分榜")
    lines.append("  ┌─" + "─" * 70 + "┐")
    lines.append(f"  │ {'#':>2s} │ {'战队':<6s} │ {'积分':>4s} │ {'胜':>2s} │ {'负':>2s} │ {'局分':>5s} │ {'局差':>3s} │ {'强度':>4s} │")
    lines.append("  ├" + "─" * 4 + "┼" + "─" * 8 + "┼" + "─" * 6 + "┼" + "─" * 4 + "┼" + "─" * 4 + "┼" + "─" * 7 + "┼" + "─" * 5 + "┼" + "─" * 6 + "┤")

    for rank, row in enumerate(table, 1):
        score_str = f"{row['games_won']}:{row['games_lost']}"
        gd_str = f"+{row['gd']}" if row['gd'] >= 0 else str(row['gd'])
        lines.append(
            f"  │ {rank:>2d} │ {row['abbr']:<6s} │ {row['pts']:>4d} │ {row['wins']:>2d} │ "
            f"{row['losses']:>2d} │ {score_str:>5s} │ {gd_str:>3s} │ {row['strength']:>4d} │"
        )

    lines.append("  └" + "─" * 4 + "┴" + "─" * 8 + "┴" + "─" * 6 + "┴" + "─" * 4 + "┴" + "─" * 4 + "┴" + "─" * 7 + "┴" + "─" * 5 + "┴" + "─" * 6 + "┘")
    return "\n".join(lines)


def format_full_round(round_num, match_date, all_schedules, all_matches_results, all_standings):
    """格式化完整一轮的输出（四赛区结果+积分榜）。"""
    lines = []
    lines.append(f"═══ 第 {round_num:02d} 轮  |  {match_date}  ═══")
    lines.append("")

    # 各赛区对阵结果
    lines.append("┌─ 各赛区对阵结果 " + "─" * 56 + "┐")
    for region_name, region_teams in REGIONS_SIM.items():
        round_matches = all_schedules[region_name][round_num - 1]
        results = all_matches_results[region_name]
        lines.append(format_region_matches(region_name, region_teams, round_matches, results))
        lines.append("")
    lines.append("└" + "─" * 74 + "┘")
    lines.append("")

    # 各赛区积分榜
    lines.append("┌─ 各赛区积分榜 " + "─" * 58 + "┐")
    for region_name, region_teams in REGIONS_SIM.items():
        standings = all_standings[region_name]
        lines.append(format_region_standings(region_name, region_teams, standings))
        lines.append("")
    lines.append("└" + "─" * 74 + "┘")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================

def simulate_one_round(round_num, all_schedules, all_standings):
    """模拟一轮所有赛区的比赛。返回（各赛区结果, 更新后积分榜, 日期字符串）。"""
    # 生成日期
    start_date = date(2025, 3, 1)
    while start_date.weekday() != 6:
        start_date += timedelta(days=1)
    match_date = start_date + timedelta(weeks=round_num - 1)
    date_str = f"{match_date.strftime('%Y-%m-%d')}（周日）"

    all_matches_results = {}

    for region_name, region_teams in REGIONS_SIM.items():
        round_matches = all_schedules[region_name][round_num - 1]
        standings = all_standings[region_name]
        matches_results = []

        for home_idx, away_idx in round_matches:
            home_team = region_teams[home_idx]
            away_team = region_teams[away_idx]
            winner_abbr, score, _ = simulate_bo3(home_team, away_team)

            update_standings_for_match(
                standings, home_team, away_team, winner_abbr, score
            )

            matches_results.append((home_idx, away_idx, home_team, away_team, winner_abbr, score))

        all_matches_results[region_name] = matches_results

    return all_matches_results, all_standings, date_str


def delete_last_round(filepath, current_rounds):
    """从输出文件中删除最后一轮数据，保留文件头部。"""
    if current_rounds == 0:
        print("[提示] 没有可回退的数据。")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    delimiter = "═══ 第"
    last_pos = content.rfind(delimiter)
    if last_pos > 0:
        prev_pos = content.rfind(delimiter, 0, last_pos)
        if prev_pos >= 0:
            new_content = content[:prev_pos].rstrip() + "\n"
        else:
            header_end = content.find("═══ 第")
            if header_end > 0:
                new_content = content[:header_end].rstrip() + "\n"
            else:
                new_content = ""
    else:
        new_content = ""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"[回退] 已删除第 {current_rounds} 轮数据。当前剩余 {current_rounds - 1} 轮。")
    return current_rounds - 1


def main():
    output_path = get_output_path()

    # 为所有赛区生成赛程
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

            all_matches_results, all_standings, date_str = simulate_one_round(
                round_num, all_schedules, all_standings
            )

            round_output = format_full_round(
                round_num, date_str, all_schedules, all_matches_results, all_standings
            )

            with open(output_path, "a", encoding="utf-8") as f:
                if current_rounds == 0:
                    header = "=" * 80
                    header += "\n  A级联赛（星脉挑战联赛）— 模拟战报\n"
                    header += "  赛季: S7 | 4赛区 × 5支战队 | 单循环 | BO3 | 共5轮\n"
                    header += "=" * 80 + "\n\n"
                    f.write(header)
                f.write(round_output)

            current_rounds = round_num
            print(f"[完成] 第 {round_num} 轮已模拟并写入文件。")
            print(f"  文件路径: {output_path}")

        else:
            print(f"[错误] 未知操作: '{choice}'。请输入 n/r/q。")


if __name__ == "__main__":
    main()
