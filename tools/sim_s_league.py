#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级联赛（星脉超级联赛）模拟器
=============================
基于 schedule_s_league.py 生成的赛程，逐轮模拟BO3比赛结果。
每运行一次模拟一轮，支持回退（删除最新一轮结果）。

模拟机制：
- 每支战队有一个强度值（0~100），决定胜负概率。
- 使用 Elo 期望公式：P(A胜) = 1 / (1 + 10^((s_B - s_A) / 25))
- 附带随机扰动（±5%），保证一定的不确定性。
- BO3：三局两胜制，逐局模拟。

积分规则：
- 2:0 获胜 → 3分
- 2:1 获胜 → 2分
- 1:2 落败 → 1分
- 0:2 落败 → 0分

排名规则：积分优先 → 胜场数 → 局分差 → 缩写字母序

输出：tools/sim_s_league_output.txt，每轮含对阵结果表和积分榜。
"""

import os
import sys
import random
import re
from datetime import date, timedelta

# ============================================================
# 队伍数据（含强度值，基于teams_archive中的描述评定）
# ============================================================
S_TEAMS_SIM = [
    {"abbr": "PV",    "full": "幻界战队 PHANTOM VOID",        "city": "沪江市",   "strength": 92},
    {"abbr": "IC",    "full": "北燕皇朝 IMPERIAL CROWN",      "city": "北燕市",   "strength": 90},
    {"abbr": "NS",    "full": "深南闪电 NEON SPARK",           "city": "深南市",   "strength": 88},
    {"abbr": "BF",    "full": "粤城烈焰 BLAZING FIRE",         "city": "粤城",     "strength": 86},
    {"abbr": "TR",    "full": "蓉城咆哮 THUNDER ROAR",         "city": "蓉城",     "strength": 83},
    {"abbr": "DT",    "full": "杭溪数码 DIGITAL TIDE",         "city": "杭溪市",   "strength": 82},
    {"abbr": "IB",    "full": "武川铁甲 IRON BASTION",         "city": "武川市",   "strength": 80},
    {"abbr": "DG",    "full": "渝州龙门 DRAGON GATE",          "city": "渝州市",   "strength": 75},
    {"abbr": "SW",    "full": "津门钢铁 STEEL WALL",           "city": "津门市",   "strength": 74},
    {"abbr": "CF",    "full": "锦官凤羽 CRIMSON FEATHER",      "city": "锦官市",   "strength": 72},
    {"abbr": "StarW", "full": "静海星澜 STARWAVE",             "city": "沪江市",   "strength": 71},
    {"abbr": "PS",    "full": "北燕幽影 PHANTOM SHADE",        "city": "北燕市",   "strength": 70},
    {"abbr": "ET",    "full": "东渡潮浪 EASTERN TIDE",         "city": "沪江市",   "strength": 68},
    {"abbr": "BS",    "full": "渤海风暴 BOHAI STORM",          "city": "津门市",   "strength": 67},
    {"abbr": "HPE",   "full": "云贵高原鹰 HIGHPEAK EAGLE",     "city": "巡回主场", "strength": 65},
    {"abbr": "AA",    "full": "沪江星辰学院 ASTERIA ACADEMY",  "city": "沪江市",   "strength": 62},
]

TOTAL_ROUNDS = 30

# ============================================================
# 赛程数据（与 schedule_s_league.py 一致：圆圈法双循环）
# ============================================================
def generate_all_rounds():
    """生成30轮赛程（主队索引, 客队索引）。"""
    n = 16
    fixed = n - 1
    circle = list(range(n - 1))
    all_rounds = []

    # 前半程（15轮）
    for r in range(n - 1):
        round_matches = []
        if r % 2 == 0:
            round_matches.append((circle[r], fixed))
        else:
            round_matches.append((fixed, circle[r]))
        for i in range(1, n // 2):
            left = (r + i) % (n - 1)
            right = (r - i) % (n - 1)
            if i % 2 == 1:
                round_matches.append((circle[left], circle[right]))
            else:
                round_matches.append((circle[right], circle[left]))
        all_rounds.append(round_matches)

    # 后半程（15轮）：主客场对调
    for r in range(n - 1):
        first_half = all_rounds[r]
        second_half = [(away, home) for (home, away) in first_half]
        all_rounds.append(second_half)

    return all_rounds


# ============================================================
# 模拟算法
# ============================================================
def win_probability(team_a, team_b):
    """计算Team A战胜Team B的概率（基于Elo期望公式）。"""
    s_a = team_a["strength"]
    s_b = team_b["strength"]
    prob = 1.0 / (1.0 + 10 ** ((s_b - s_a) / 25.0))
    # 加随机扰动 ±5%
    prob += random.uniform(-0.05, 0.05)
    return max(0.0, min(1.0, prob))


def simulate_game(home_team, away_team, home_bonus=3):
    """模拟一局比赛，返回胜者abbr。主场加成3点强度。"""
    # 临时调整强度：主场加成
    adjusted_home = dict(home_team)
    adjusted_home["strength"] = home_team["strength"] + home_bonus
    prob = win_probability(adjusted_home, away_team)
    if random.random() < prob:
        return home_team["abbr"]
    else:
        return away_team["abbr"]


def simulate_bo3(home_team, away_team):
    """模拟一场BO3比赛，返回(胜者abbr, 局分, 败者abbr)。"""
    home_wins = 0
    away_wins = 0

    while home_wins < 2 and away_wins < 2:
        winner = simulate_game(home_team, away_team)
        if winner == home_team["abbr"]:
            home_wins += 1
        else:
            away_wins += 1

    if home_wins == 2:
        score = f"2:{away_wins}"
        return home_team["abbr"], score, away_team["abbr"]
    else:
        score = f"{home_wins}:2"
        return away_team["abbr"], score, home_team["abbr"]


def points_from_score(winner_abbr, score, my_abbr):
    """根据比分和己方缩写计算积分。"""
    if my_abbr == winner_abbr:
        # 获胜方
        if score in ("2:0", "0:2"):  # 2:0 或对手0:2（即自己2:0）
            return 3
        else:
            return 2
    else:
        # 落败方
        if score in ("2:0", "0:2"):
            return 0
        else:
            return 1


# ============================================================
# 文件读写
# ============================================================

def get_output_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sim_s_league_output.txt")


def read_existing_data(filepath):
    """读取已有的模拟数据，返回（已完成轮数, 原文件其余内容）。"""
    if not os.path.exists(filepath):
        return 0, ""

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 统计当前已模拟的轮数
    rounds_done = content.count("═══ 第")  # Match the delimiter
    return rounds_done, content


def parse_standings_from_text(content):
    """从已有输出中解析最新积分榜，返回 {abbr: {pts, wins, losses, games_w, games_l}}"""
    standings = {}
    for team in S_TEAMS_SIM:
        standings[team["abbr"]] = {
            "pts": 0, "wins": 0, "losses": 0,
            "games_won": 0, "games_lost": 0
        }

    # 找到所有积分榜表格并累加（最后一轮的积分榜是累计值）
    # 简化处理：找到最后一个积分榜即可
    lines = content.split("\n")
    in_standings = False
    last_standings_start = -1
    for i, line in enumerate(lines):
        if "积分榜" in line:
            last_standings_start = i

    if last_standings_start >= 0:
        in_standings = False
        for i in range(last_standings_start, len(lines)):
            line = lines[i].strip()
            if "排名" in line and "战队" in line:
                in_standings = True
                continue
            if in_standings and line.startswith("──"):
                continue
            if in_standings and line == "":
                break
            if in_standings and line:
                # 解析: | 1 | PV | 30 | 5 | 1 | 12:3 | ...
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 6:
                    abbr = parts[1]
                    pts = int(parts[2])
                    wins = int(parts[3])
                    losses = int(parts[4])
                    score_parts = parts[5].split(":")
                    gw = int(score_parts[0])
                    gl = int(score_parts[1])
                    if abbr in standings:
                        standings[abbr] = {
                            "pts": pts, "wins": wins, "losses": losses,
                            "games_won": gw, "games_lost": gl
                        }

    return standings


def format_match_result(round_num, match_date, matches_results):
    """格式化单轮对阵结果表。"""
    lines = []
    lines.append(f"═══ 第 {round_num:02d} 轮  |  {match_date}  ═══")
    lines.append("")
    lines.append("┌─ 对阵结果 ───────────────────────────────────────────────────────────────┐")
    lines.append(f"│ {'主场':<22s} │ {'比分':>5s} │ {'客场':<22s} │ {'强度对比':>16s} │")
    lines.append("├──────────────────────────┼───────┼──────────────────────────┼──────────────────┤")

    for home_idx, away_idx, home_team, away_team, winner_abbr, score in matches_results:
        home_str = f"{home_team['abbr']} {home_team['full']}"
        away_str = f"{away_team['abbr']} {away_team['full']}"
        # 截断以适应宽度
        if len(home_str) > 21:
            home_str = home_team['abbr'] + " " + home_team['full'][:13] + "..."
            home_str = home_str[:21]
        if len(away_str) > 21:
            away_str = away_team['abbr'] + " " + away_team['full'][:13] + "..."
            away_str = away_str[:21]

        strength_str = f"{home_team['strength']} vs {away_team['strength']}"
        # 胜者标记
        if winner_abbr == home_team['abbr']:
            home_str = f"★{home_str}"
        else:
            away_str = f"★{away_str}"

        lines.append(f"│ {home_str:<21s} │ {score:>5s} │ {away_str:<21s} │ {strength_str:>16s} │")

    lines.append("└──────────────────────────┴───────┴──────────────────────────┴──────────────────┘")
    return "\n".join(lines)


def format_standings(standings_dict):
    """格式化积分榜。"""
    # 构建排序列表
    table = []
    for team in S_TEAMS_SIM:
        abbr = team["abbr"]
        s = standings_dict.get(abbr, {"pts": 0, "wins": 0, "losses": 0,
                                        "games_won": 0, "games_lost": 0})
        gd = s["games_won"] - s["games_lost"]
        table.append({
            "abbr": abbr,
            "full": team["full"],
            "pts": s["pts"],
            "wins": s["wins"],
            "losses": s["losses"],
            "games_won": s["games_won"],
            "games_lost": s["games_lost"],
            "gd": gd,
            "strength": team["strength"],
        })

    # 排序：积分 → 胜场 → 局分差 → 强度
    table.sort(key=lambda x: (-x["pts"], -x["wins"], -x["gd"], -x["strength"]))

    lines = []
    lines.append("┌─ 积分榜 ───────────────────────────────────────────────────────────────────────┐")
    lines.append(f"│ {'#':>2s} │ {'战队':<22s} │ {'积分':>4s} │ {'胜':>3s} │ {'负':>3s} │ {'局分':>6s} │ {'局差':>4s} │ {'强度':>4s} │")
    lines.append("├─────┼────────────────────────┼──────┼─────┼─────┼────────┼──────┼──────┤")

    for rank, row in enumerate(table, 1):
        score_str = f"{row['games_won']}:{row['games_lost']}"
        gd_str = f"+{row['gd']}" if row['gd'] >= 0 else str(row['gd'])
        # 截断
        full_display = row["full"]
        if len(full_display) > 21:
            full_display = full_display[:20]
        lines.append(
            f"│ {rank:>2d} │ {full_display:<21s} │ {row['pts']:>4d} │ {row['wins']:>3d} │ "
            f"{row['losses']:>3d} │ {score_str:>6s} │ {gd_str:>4s} │ {row['strength']:>4d} │"
        )

    lines.append("└─────┴────────────────────────┴──────┴─────┴─────┴────────┴──────┴──────┘")
    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================

def simulate_round(round_num, all_rounds, standings):
    """模拟一轮比赛，返回（轮次结果列表, 更新后的积分榜, 日期字符串）。"""
    # 生成日期
    season_start = date(2025, 3, 1)
    while season_start.weekday() != 5:
        season_start += timedelta(days=1)

    # 与schedule生成器保持一致：前10轮快节奏，后20轮慢节奏
    dates = []
    current = season_start
    for r in range(TOTAL_ROUNDS):
        if r < 10:
            if r % 2 == 0:
                while current.weekday() != 5:
                    current += timedelta(days=1)
            else:
                while current.weekday() != 2:
                    current += timedelta(days=1)
        else:
            while current.weekday() != 5:
                current += timedelta(days=1)
        dates.append(current)
        current += timedelta(days=1)

    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    match_date = f"{dates[round_num - 1].strftime('%Y-%m-%d')}（{weekdays[dates[round_num - 1].weekday()]}）"

    # 当轮对阵
    round_matches = all_rounds[round_num - 1]
    matches_results = []

    for home_idx, away_idx in round_matches:
        home_team = S_TEAMS_SIM[home_idx]
        away_team = S_TEAMS_SIM[away_idx]
        winner_abbr, score, _ = simulate_bo3(home_team, away_team)

        # 更新积分
        home_pts = points_from_score(winner_abbr, score, home_team["abbr"])
        away_pts = points_from_score(winner_abbr, score, away_team["abbr"])

        # 解析局分（始终是 home_score:away_score）
        parts_score = score.split(":")
        h_gw = int(parts_score[0])  # 主队本场赢的局数
        h_gl = int(parts_score[1])  # 主队本场输的局数

        # 更新主场
        standings[home_team["abbr"]]["pts"] += home_pts
        standings[home_team["abbr"]]["games_won"] += h_gw
        standings[home_team["abbr"]]["games_lost"] += h_gl
        if home_pts >= 2:
            standings[home_team["abbr"]]["wins"] += 1
        else:
            standings[home_team["abbr"]]["losses"] += 1

        # 更新客场
        standings[away_team["abbr"]]["pts"] += away_pts
        standings[away_team["abbr"]]["games_won"] += h_gl
        standings[away_team["abbr"]]["games_lost"] += h_gw
        if away_pts >= 2:
            standings[away_team["abbr"]]["wins"] += 1
        else:
            standings[away_team["abbr"]]["losses"] += 1

        matches_results.append((home_idx, away_idx, home_team, away_team, winner_abbr, score))

    return matches_results, standings, match_date


def delete_last_round(filepath, current_rounds):
    """从输出文件中删除最后一轮的数据。保留文件头部。"""
    if current_rounds == 0:
        print("[提示] 没有可回退的数据。")
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 找到最后一个轮次分隔线并删除
    delimiter = "═══ 第"
    last_pos = content.rfind(delimiter)
    if last_pos > 0:
        prev_pos = content.rfind(delimiter, 0, last_pos)
        if prev_pos >= 0:
            # 保留之前的所有内容（含头部）
            new_content = content[:prev_pos].rstrip() + "\n"
        else:
            # 只剩一轮，只保留文件头部
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
    all_rounds = generate_all_rounds()
    current_rounds, existing_content = read_existing_data(output_path)

    # 解析当前积分榜
    standings = parse_standings_from_text(existing_content)

    print("=" * 60)
    print("  S级联赛（星脉超级联赛）模拟器")
    print(f"  当前进度: 已完成 {current_rounds} / {TOTAL_ROUNDS} 轮")
    print("=" * 60)

    while True:
        print()
        if current_rounds >= TOTAL_ROUNDS:
            print("[提示] 全部30轮已完成！无法继续模拟。")
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
            # 回退后重新从文件解析积分榜
            _, updated_content = read_existing_data(output_path)
            standings = parse_standings_from_text(updated_content)
            continue

        elif choice in ("n", "next", ""):
            if current_rounds >= TOTAL_ROUNDS:
                print("[提示] 全部30轮已完成！")
                continue

            # 模拟下一轮
            round_num = current_rounds + 1
            print(f"\n[模拟中] 正在模拟第 {round_num} 轮...")

            matches_results, standings, match_date = simulate_round(
                round_num, all_rounds, standings
            )

            # 格式化输出
            round_output = format_match_result(round_num, match_date, matches_results)
            round_output += "\n\n"
            round_output += format_standings(standings)
            round_output += "\n\n"

            # 写入文件（追加）
            with open(output_path, "a", encoding="utf-8") as f:
                # 如果文件不存在或为空，先写头部
                if current_rounds == 0:
                    header = (
                        "=" * 80 + "\n"
                        "  S级联赛（星脉超级联赛）— 模拟战报\n"
                        "  赛季: S7 | 16支战队 | 双循环 | BO3 | 共30轮\n"
                        "=" * 80 + "\n\n"
                    )
                    f.write(header)

                f.write(round_output)

            current_rounds = round_num
            print(f"[完成] 第 {round_num} 轮已模拟并写入文件。")
            print(f"  文件路径: {output_path}")

        else:
            print(f"[错误] 未知操作: '{choice}'。请输入 n/r/q。")


if __name__ == "__main__":
    main()
