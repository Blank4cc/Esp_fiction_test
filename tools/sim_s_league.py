#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级联赛（星脉超级联赛）模拟器
=============================
逐轮模拟BO3比赛结果。每运行一次模拟一轮，支持回退。
输出为 Markdown 格式，含对阵结果表和积分榜。

模拟机制：Elo期望公式 + ±5%随机扰动 + 主场+3强度加成。
积分：2:0=3分 / 2:1=2分 / 1:2=1分 / 0:2=0分。
"""

import os
import random
import re
from datetime import date, timedelta

# ============================================================
# 赛季日历常量（与 schedule_s_league.py 一致）
# ============================================================
BREAKS = [
    (date(2052, 4,  4), date(2052, 4,  6), "清明节",  "🌿"),
    (date(2052, 5,  1), date(2052, 5,  5), "劳动节黄金周", "💼"),
    (date(2052, 6,  7), date(2052, 6,  9), "端午节",  "🐉"),
]
MID_SEASON = (date(2052, 6, 14), date(2052, 6, 27), "全球季中赛", "🏆")
FAST_ROUNDS = 10
TOTAL_ROUNDS = 30


def _is_break_day(d):
    for start, end, name, icon in BREAKS:
        if start <= d <= end:
            return True, name, icon
    ms_s, ms_e, ms_n, ms_i = MID_SEASON
    if ms_s <= d <= ms_e:
        return True, ms_n, ms_i
    return False, "", ""


def _precompute_dates():
    """预计算全部30轮日期 + 休赛标记。"""
    season_start = date(2052, 3, 1)
    while season_start.weekday() != 5:
        season_start += timedelta(days=1)

    dates = []
    breaks_between = {}
    current = season_start

    for r in range(TOTAL_ROUNDS):
        target_wd = 5 if r >= FAST_ROUNDS or r % 2 == 0 else 2
        skipped_set = {}
        while True:
            while current.weekday() != target_wd:
                current += timedelta(days=1)
            is_brk, brk_name, brk_icon = _is_break_day(current)
            if not is_brk:
                break
            if brk_name not in skipped_set:
                skipped_set[brk_name] = brk_icon
            current += timedelta(days=1)
        if skipped_set:
            breaks_between[r + 1] = " / ".join(f"{icon} {name}" for name, icon in skipped_set.items())
        dates.append(current)
        current += timedelta(days=1)

    return dates, breaks_between


ALL_DATES, BREAKS_AFTER = _precompute_dates()

# ============================================================
# 队伍数据（含强度值）
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
# ============================================================
# 赛程生成
# ============================================================
def generate_all_rounds():
    """生成30轮赛程（主队索引, 客队索引）。"""
    n = 16
    fixed = n - 1
    circle = list(range(n - 1))
    all_rounds = []

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

    for r in range(n - 1):
        first_half = all_rounds[r]
        second_half = [(away, home) for (home, away) in first_half]
        all_rounds.append(second_half)

    return all_rounds


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


# ============================================================
# 文件读写与解析
# ============================================================

def get_output_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sim_s_league_output.md")


def read_existing_data(filepath):
    """读取已有的模拟数据，返回（已完成轮数, 文件内容）。"""
    if not os.path.exists(filepath):
        return 0, ""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    # 统计 "## 第 XX 轮" 出现次数
    rounds_done = len(re.findall(r'^## 第 \d+ 轮', content, re.MULTILINE))
    return rounds_done, content


def parse_standings_from_text(content):
    """从已有 Markdown 输出中解析最新积分榜。
    
    积分榜表格格式:
    | # | 战队 | 积分 | 胜 | 负 | 局分 | 局差 | 强度 |
    |---|------|------|-----|-----|------|------|------|
    | 1 | PV   | 6    | 2   | 0   | 4:0  | +4   | 92   |
    """
    standings = {}
    for team in S_TEAMS_SIM:
        standings[team["abbr"]] = {"pts": 0, "wins": 0, "losses": 0,
                                     "games_won": 0, "games_lost": 0}

    if not content:
        return standings

    # 找到最后一个积分榜（"### 积分榜" 之后的第一个表格）
    lines = content.split("\n")
    last_standings_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^###\s+积分榜', line):
            last_standings_idx = i

    if last_standings_idx < 0:
        return standings

    # 从积分榜标题后找表格行
    in_table = False
    for i in range(last_standings_idx, len(lines)):
        line = lines[i].strip()
        # 表头行
        if line.startswith("| # |") or line.startswith("|# |"):
            in_table = True
            continue
        # 分隔行
        if in_table and re.match(r'^\|[\-\s|]+\|$', line):
            continue
        # 数据行
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 7:
                rank_str = parts[0]
                abbr = parts[1]
                pts = int(parts[2])
                wins = int(parts[3])
                losses = int(parts[4])
                score_str = parts[5]
                gd_str = parts[6]
                sp = score_str.split(":")
                gw = int(sp[0])
                gl = int(sp[1])
                if abbr in standings:
                    standings[abbr] = {"pts": pts, "wins": wins, "losses": losses,
                                        "games_won": gw, "games_lost": gl}
        elif in_table and line == "":
            break

    return standings


# ============================================================
# Markdown 格式化
# ============================================================

def format_match_result_md(round_num, match_date, matches_results):
    """Markdown 对阵结果表。"""
    weekdays_map = ["周一","周二","周三","周四","周五","周六","周日"]
    lines = []
    lines.append(f"## 第 {round_num:02d} 轮")
    lines.append("")
    lines.append(f"> **日期**: {match_date}")
    lines.append("")
    lines.append("### 对阵结果")
    lines.append("")
    lines.append("| # | 主场 | 比分 | 客场 | 强度对比 |")
    lines.append("|---|------|------|------|----------|")

    for i, (home_idx, away_idx, home_team, away_team, winner_abbr, score) in enumerate(matches_results, 1):
        home_full = f"**{home_team['abbr']}** {home_team['full']}"
        away_full = f"**{away_team['abbr']}** {away_team['full']}"
        if winner_abbr == home_team["abbr"]:
            home_full = f"🏆 {home_full}"
        else:
            away_full = f"🏆 {away_full}"
        strength_str = f"{home_team['strength']} vs {away_team['strength']}"
        lines.append(f"| {i} | {home_full} | {score} | {away_full} | {strength_str} |")

    lines.append("")
    return "\n".join(lines)


def format_standings_md(standings_dict):
    """Markdown 积分榜。"""
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
            "gw": s["games_won"],
            "gl": s["games_lost"],
            "gd": gd,
            "strength": team["strength"],
        })

    table.sort(key=lambda x: (-x["pts"], -x["wins"], -x["gd"], -x["strength"]))

    lines = []
    lines.append("### 积分榜")
    lines.append("")
    lines.append("| # | 战队 | 积分 | 胜 | 负 | 局分 | 局差 | 强度 |")
    lines.append("|---|------|------|-----|-----|------|------|------|")

    for rank, row in enumerate(table, 1):
        score_str = f"{row['gw']}:{row['gl']}"
        gd_str = f"+{row['gd']}" if row['gd'] >= 0 else str(row['gd'])
        lines.append(f"| {rank} | **{row['abbr']}** {row['full']} | {row['pts']} | {row['wins']} | {row['losses']} | {score_str} | {gd_str} | {row['strength']} |")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# 回退与主流程
# ============================================================

def delete_last_round(filepath, current_rounds):
    """删除最后一轮的数据，保留文件头部和之前所有轮次。"""
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

    # 截断到最后一个轮次标题之前，保留之前的所有内容
    last_match_start = matches[-1].start()
    new_content = content[:last_match_start].rstrip() + "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    new_count = max(0, current_rounds - 1)
    print(f"[回退] 已删除第 {current_rounds} 轮数据。当前剩余 {new_count} 轮。")
    return new_count


def simulate_round(round_num, all_rounds, standings):
    """模拟一轮比赛。返回 (results, standings, match_date, break_note)。"""
    weekdays = ["周一","周二","周三","周四","周五","周六","周日"]
    d = ALL_DATES[round_num - 1]
    match_date = f"{d.strftime('%Y-%m-%d')}（{weekdays[d.weekday()]}）"

    # 本轮之后的休赛标记
    break_note = BREAKS_AFTER.get(round_num + 1, "")

    round_matches = all_rounds[round_num - 1]
    matches_results = []

    for home_idx, away_idx in round_matches:
        home_team = S_TEAMS_SIM[home_idx]
        away_team = S_TEAMS_SIM[away_idx]
        winner_abbr, score, _ = simulate_bo3(home_team, away_team)

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

        matches_results.append((home_idx, away_idx, home_team, away_team, winner_abbr, score))

    return matches_results, standings, match_date, break_note


def main():
    output_path = get_output_path()
    all_rounds = generate_all_rounds()
    current_rounds, existing_content = read_existing_data(output_path)
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
            _, updated_content = read_existing_data(output_path)
            standings = parse_standings_from_text(updated_content)
            continue

        elif choice in ("n", "next", ""):
            if current_rounds >= TOTAL_ROUNDS:
                print("[提示] 全部30轮已完成！")
                continue

            round_num = current_rounds + 1
            print(f"\n[模拟中] 正在模拟第 {round_num} 轮...")

            matches_results, standings, match_date, break_note = simulate_round(
                round_num, all_rounds, standings
            )

            round_output = format_match_result_md(round_num, match_date, matches_results)
            round_output += "\n"
            round_output += format_standings_md(standings)
            if break_note:
                round_output += f"\n> ⏸ **下轮休赛**：{break_note}\n"
            round_output += "\n---\n\n"

            with open(output_path, "a", encoding="utf-8") as f:
                if current_rounds == 0:
                    header = "# S级联赛（星脉超级联赛）— 模拟战报\n\n"
                    header += "> **赛季**: S7 | **战队**: 16支 | **赛制**: 双循环 | **场次**: BO3 | **共**: 30轮\n\n"
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
