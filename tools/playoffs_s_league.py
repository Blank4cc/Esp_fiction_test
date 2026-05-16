#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级联赛季后赛模拟器
===================
读取 sim_s_league_output.md 的最终常规赛积分榜，
取前8名进行季后赛模拟，输出淘汰赛对阵图和结果。

赛制：
  - 四分之一决赛：BO3 单败（#1v#8, #4v#5, #3v#6, #2v#7）
  - 败者组：常规赛前4种子若QF落败，获一次复活机会（BO3）
  - 半决赛：BO3
  - 决赛：BO5
"""

import os
import re
import random
from datetime import date

# ============================================================
# 队伍数据（强度值，与 sim_s_league.py 一致）
# ============================================================
S_TEAMS = {
    "PV":    {"full": "幻界战队 PHANTOM VOID",        "strength": 92},
    "IC":    {"full": "北燕皇朝 IMPERIAL CROWN",      "strength": 90},
    "NS":    {"full": "深南闪电 NEON SPARK",           "strength": 88},
    "BF":    {"full": "粤城烈焰 BLAZING FIRE",         "strength": 86},
    "TR":    {"full": "蓉城咆哮 THUNDER ROAR",         "strength": 83},
    "DT":    {"full": "杭溪数码 DIGITAL TIDE",         "strength": 82},
    "IB":    {"full": "武川铁甲 IRON BASTION",         "strength": 80},
    "DG":    {"full": "渝州龙门 DRAGON GATE",          "strength": 75},
    "SW":    {"full": "津门钢铁 STEEL WALL",           "strength": 74},
    "CF":    {"full": "锦官凤羽 CRIMSON FEATHER",      "strength": 72},
    "StarW": {"full": "静海星澜 STARWAVE",             "strength": 71},
    "PS":    {"full": "北燕幽影 PHANTOM SHADE",        "strength": 70},
    "ET":    {"full": "东渡潮浪 EASTERN TIDE",         "strength": 68},
    "BS":    {"full": "渤海风暴 BOHAI STORM",          "strength": 67},
    "HPE":   {"full": "云贵高原鹰 HIGHPEAK EAGLE",     "strength": 65},
    "AA":    {"full": "沪江星辰学院 ASTERIA ACADEMY",  "strength": 62},
}


# ============================================================
# 解析常规赛积分榜
# ============================================================
def read_final_standings(sim_output_path):
    """从 sim_s_league_output.md 读取最终积分榜，返回按排名排序的 [(abbr, pts, wins, ...)]。"""
    if not os.path.exists(sim_output_path):
        print(f"[错误] 找不到模拟战报: {sim_output_path}")
        print("  请先运行 sim_s_league.py 完成至少一轮模拟。")
        return None

    with open(sim_output_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 找到最后一个积分榜
    lines = content.split("\n")
    last_standings_idx = -1
    for i, line in enumerate(lines):
        if re.match(r'^###\s+积分榜', line):
            last_standings_idx = i

    if last_standings_idx < 0:
        print("[错误] 未在模拟战报中找到积分榜。")
        return None

    standings = []
    in_table = False
    for i in range(last_standings_idx, len(lines)):
        line = lines[i].strip()
        if line.startswith("| # |") or line.startswith("|# |"):
            in_table = True
            continue
        if in_table and re.match(r'^\|[\-\s|]+\|$', line):
            continue
        if in_table and line.startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 7:
                rank = int(parts[0])
                # 战队列格式: **ABBR** Full Name → 提取缩写
                abbr_raw = parts[1].replace("**", "").split()[0]
                pts = int(parts[2])
                wins = int(parts[3])
                losses = int(parts[4])
                sp = parts[5].split(":")
                gw = int(sp[0])
                gl = int(sp[1])
                if abbr_raw in S_TEAMS:
                    standings.append({
                        "rank": rank, "abbr": abbr_raw,
                        "full": S_TEAMS[abbr_raw]["full"],
                        "pts": pts, "wins": wins, "losses": losses,
                        "gw": gw, "gl": gl,
                        "strength": S_TEAMS[abbr_raw]["strength"],
                    })
        elif in_table and line == "":
            break

    if len(standings) < 8:
        print(f"[错误] 积分榜只有 {len(standings)} 支队伍，需要至少8支。")
        return None

    return standings[:8]


# ============================================================
# 模拟算法
# ============================================================
def win_probability(team_a, team_b):
    pa = 1.0 / (1.0 + 10 ** ((team_b["strength"] - team_a["strength"]) / 25.0))
    pa += random.uniform(-0.03, 0.03)  # 季后赛扰动更小
    return max(0.0, min(1.0, pa))


def simulate_match(team_a, team_b, bo=3):
    """模拟一场BO3或BO5。返回 (胜者abbr, 比分)。"""
    wins_needed = bo // 2 + 1  # BO3→2, BO5→3
    aw = 0
    bw = 0
    while aw < wins_needed and bw < wins_needed:
        if random.random() < win_probability(team_a, team_b):
            aw += 1
        else:
            bw += 1
    if aw == wins_needed:
        return team_a["abbr"], f"{aw}:{bw}"
    return team_b["abbr"], f"{aw}:{bw}"


# ============================================================
# 对阵图格式化
# ============================================================
def fmt_team(t, label=""):
    """格式化战队显示。"""
    return f"**{t['abbr']}** {t['full']}（#{t['rank']} 种子）{label}"


def run_playoffs(teams):
    """
    运行完整季后赛。返回各阶段结果。
    
    返回: dict，含 quarters, losers_bracket, semis, final, third_place
    """
    # 确保按种子排序
    teams_by_seed = {t["rank"]: t for t in teams}
    s1, s2, s3, s4 = teams_by_seed[1], teams_by_seed[2], teams_by_seed[3], teams_by_seed[4]
    s5, s6, s7, s8 = teams_by_seed[5], teams_by_seed[6], teams_by_seed[7], teams_by_seed[8]

    results = {}

    # --- 四分之一决赛 ---
    print("\n[四分之一决赛 BO3]")
    qf1_winner, qf1_score = simulate_match(s1, s8, 3)
    qf1_loser = s8 if qf1_winner == s1["abbr"] else s1
    print(f"  QF1: {s1['abbr']}(#{1}) vs {s8['abbr']}(#{8}) → {qf1_winner} {qf1_score}")
    results["QF1"] = (s1, s8, qf1_winner, qf1_score, qf1_loser)

    qf2_winner, qf2_score = simulate_match(s4, s5, 3)
    qf2_loser = s5 if qf2_winner == s4["abbr"] else s4
    print(f"  QF2: {s4['abbr']}(#{4}) vs {s5['abbr']}(#{5}) → {qf2_winner} {qf2_score}")
    results["QF2"] = (s4, s5, qf2_winner, qf2_score, qf2_loser)

    qf3_winner, qf3_score = simulate_match(s3, s6, 3)
    qf3_loser = s6 if qf3_winner == s3["abbr"] else s3
    print(f"  QF3: {s3['abbr']}(#{3}) vs {s6['abbr']}(#{6}) → {qf3_winner} {qf3_score}")
    results["QF3"] = (s3, s6, qf3_winner, qf3_score, qf3_loser)

    qf4_winner, qf4_score = simulate_match(s2, s7, 3)
    qf4_loser = s7 if qf4_winner == s2["abbr"] else s2
    print(f"  QF4: {s2['abbr']}(#{2}) vs {s7['abbr']}(#{7}) → {qf4_winner} {qf4_score}")
    results["QF4"] = (s2, s7, qf4_winner, qf4_score, qf4_loser)

    # 收集胜者和败者
    qf_winners = {qf1_winner, qf2_winner, qf3_winner, qf4_winner}
    qf_losers = [qf1_loser, qf2_loser, qf3_loser, qf4_loser]

    # --- 败者组（仅前4种子有资格） ---
    lb_teams = [t for t in qf_losers if t["rank"] <= 4]
    print(f"\n[败者组 BO3] 资格队伍: {[t['abbr'] for t in lb_teams]}")
    lb_winner = None
    if len(lb_teams) >= 2:
        lb_winner, lb_score = simulate_match(lb_teams[0], lb_teams[1], 3)
        results["LB"] = (lb_teams[0], lb_teams[1], lb_winner, lb_score)
        print(f"  LB: {lb_teams[0]['abbr']} vs {lb_teams[1]['abbr']} → {lb_winner} {lb_score}")
    elif len(lb_teams) == 1:
        lb_winner = lb_teams[0]["abbr"]
        results["LB"] = (lb_teams[0], None, lb_winner, "bye")
        print(f"  LB: {lb_teams[0]['abbr']} 直接晋级（唯一资格者）")
    else:
        results["LB"] = None
        print("  LB: 无资格队伍（前4种子全部晋级）")

    # --- 半决赛 ---
    print("\n[半决赛 BO3]")
    sf1_t1 = teams_by_seed[min(s1["rank"], s8["rank"])] if qf1_winner == s1["abbr"] else teams_by_seed[max(s1["rank"], s8["rank"])]
    sf1_t2 = teams_by_seed[min(s4["rank"], s5["rank"])] if qf2_winner == s4["abbr"] else teams_by_seed[max(s4["rank"], s5["rank"])]
    # 直接用 winner abbr 找队伍
    sf1_a = next(t for t in [s1, s8] if t["abbr"] == qf1_winner)
    sf1_b = next(t for t in [s4, s5] if t["abbr"] == qf2_winner)

    sf1_winner_abbr, sf1_score = simulate_match(sf1_a, sf1_b, 3)
    sf1_loser = sf1_b if sf1_winner_abbr == sf1_a["abbr"] else sf1_a
    print(f"  SF1: {sf1_a['abbr']} vs {sf1_b['abbr']} → {sf1_winner_abbr} {sf1_score}")
    results["SF1"] = (sf1_a, sf1_b, sf1_winner_abbr, sf1_score, sf1_loser)

    sf2_a = next(t for t in [s3, s6] if t["abbr"] == qf3_winner)
    sf2_b = next(t for t in [s2, s7] if t["abbr"] == qf4_winner)
    sf2_winner_abbr, sf2_score = simulate_match(sf2_a, sf2_b, 3)
    sf2_loser = sf2_b if sf2_winner_abbr == sf2_a["abbr"] else sf2_a
    print(f"  SF2: {sf2_a['abbr']} vs {sf2_b['abbr']} → {sf2_winner_abbr} {sf2_score}")
    results["SF2"] = (sf2_a, sf2_b, sf2_winner_abbr, sf2_score, sf2_loser)

    # --- 季军赛（败者组胜者 vs 半决赛败者中种子较低的） ---
    third_place_result = None
    if lb_winner:
        sf_losers = [sf1_loser, sf2_loser]
        lb_team = next(t for t in lb_teams if t["abbr"] == lb_winner)
        # 挑种子最低的SF败者
        tp_opponent = min(sf_losers, key=lambda t: t.get("rank", 99))
        print(f"\n[季军赛 BO3]")
        tp_winner, tp_score = simulate_match(lb_team, tp_opponent, 3)
        tp_loser = tp_opponent if tp_winner == lb_team["abbr"] else lb_team
        print(f"  季军赛: {lb_team['abbr']}(LB) vs {tp_opponent['abbr']} → {tp_winner} {tp_score}")
        results["3rd"] = (lb_team, tp_opponent, tp_winner, tp_score)
        # 季军和殿军
        third = next(t for t in [lb_team, tp_opponent] if t["abbr"] == tp_winner)
        fourth = tp_loser
    else:
        # 无LB → 两个SF败者争季军
        sf_losers = [sf1_loser, sf2_loser]
        print(f"\n[季军赛 BO3] (无LB复活)")
        tp_winner, tp_score = simulate_match(sf_losers[0], sf_losers[1], 3)
        tp_loser = sf_losers[1] if tp_winner == sf_losers[0]["abbr"] else sf_losers[0]
        print(f"  季军赛: {sf_losers[0]['abbr']} vs {sf_losers[1]['abbr']} → {tp_winner} {tp_score}")
        results["3rd"] = (sf_losers[0], sf_losers[1], tp_winner, tp_score)
        third = next(t for t in sf_losers if t["abbr"] == tp_winner)
        fourth = tp_loser

    # --- 总决赛 BO5 ---
    final_a = next(t for t in [sf1_a, sf1_b] if t["abbr"] == sf1_winner_abbr)
    final_b = next(t for t in [sf2_a, sf2_b] if t["abbr"] == sf2_winner_abbr)
    print(f"\n[总决赛 BO5]")
    champ_abbr, champ_score = simulate_match(final_a, final_b, 5)
    runner_up = final_b if champ_abbr == final_a["abbr"] else final_a
    print(f"  总决赛: {final_a['abbr']} vs {final_b['abbr']} → {champ_abbr} {champ_score}")
    results["Final"] = (final_a, final_b, champ_abbr, champ_score, runner_up)

    # 最终排名
    final_ranking = [
        {"rank": 1, "abbr": champ_abbr, "full": S_TEAMS[champ_abbr]["full"], 
         "note": "🏆 S7总冠军 · 世界赛小组赛直通"},
        {"rank": 2, "abbr": runner_up["abbr"], "full": S_TEAMS[runner_up["abbr"]]["full"],
         "note": "🥈 亚军 · 世界赛入围赛"},
        {"rank": 3, "abbr": third["abbr"], "full": S_TEAMS[third["abbr"]]["full"],
         "note": "🥉 季军 · 世界赛入围赛"},
        {"rank": 4, "abbr": fourth["abbr"], "full": S_TEAMS[fourth["abbr"]]["full"],
         "note": "殿军"},
    ]
    # 5-8名：QF出局且非前4种子（或无LB晋级）
    eliminated = []
    for t in qf_losers:
        if t["rank"] > 4:  # 下半区种子，直接淘汰
            eliminated.append(t)
        elif t["rank"] <= 4 and lb_winner != t["abbr"]:
            eliminated.append(t)
    for rank, t in enumerate(sorted(eliminated, key=lambda x: x["rank"]), 5):
        final_ranking.append({"rank": rank, "abbr": t["abbr"], "full": S_TEAMS[t["abbr"]]["full"], "note": f"季后赛第{rank}名"})

    results["ranking"] = final_ranking
    return results


# ============================================================
# 输出格式化
# ============================================================
def format_playoff_output(teams, results):
    """格式化为 Markdown。"""
    lines = []
    lines.append("# S7 星脉超级联赛 — 季后赛战报")
    lines.append("")
    lines.append(f"> 📅 2052年8月 | 🏟 各队主场及中立场地 | 🏆 BO3淘汰 / BO5决赛")
    lines.append("")

    # 常规赛排名
    lines.append("## 常规赛最终排名（前8晋级）")
    lines.append("")
    lines.append("| 种子 | 战队 | 积分 | 胜 | 负 | 局分 |")
    lines.append("|------|------|------|-----|-----|------|")
    for t in teams:
        score_str = f"{t['gw']}:{t['gl']}"
        lines.append(f"| #{t['rank']} | **{t['abbr']}** {t['full']} | {t['pts']} | {t['wins']} | {t['losses']} | {score_str} |")
    lines.append("")

    # 四分之一决赛
    lines.append("---")
    lines.append("")
    lines.append("## 四分之一决赛（BO3）")
    lines.append("")
    lines.append("| 场次 | 对阵 | 比分 | 胜者 |")
    lines.append("|------|------|------|------|")
    for key in ["QF1", "QF2", "QF3", "QF4"]:
        t1, t2, winner, score, loser = results[key]
        lines.append(f"| {key} | **{t1['abbr']}**(#{t1['rank']}) vs **{t2['abbr']}**(#{t2['rank']}) | {score} | 🏆 **{winner}** |")
    lines.append("")

    # 败者组
    if results["LB"]:
        lines.append("---")
        lines.append("")
        lines.append("## 败者组（BO3 · 仅常规赛前4种子享有）")
        lines.append("")
        lb = results["LB"]
        if lb[1] is not None:
            t1, t2, winner, score = lb
            lines.append(f"| 对阵 | 比分 | 胜者 |")
            lines.append(f"|------|------|------|")
            lines.append(f"| **{t1['abbr']}**(#{t1['rank']}) vs **{t2['abbr']}**(#{t2['rank']}) | {score} | 🏆 **{winner}**（复活） |")
        else:
            lines.append(f"> **{lb[0]['abbr']}**(#{lb[0]['rank']}) 为唯一败者组资格者，直接晋级季军赛。")
        lines.append("")

    # 半决赛
    lines.append("---")
    lines.append("")
    lines.append("## 半决赛（BO3）")
    lines.append("")
    lines.append("| 场次 | 对阵 | 比分 | 胜者 |")
    lines.append("|------|------|------|------|")
    for key in ["SF1", "SF2"]:
        t1, t2, winner, score, loser = results[key]
        lines.append(f"| {key} | **{t1['abbr']}** vs **{t2['abbr']}** | {score} | 🏆 **{winner}** |")
    lines.append("")

    # 季军赛
    if "3rd" in results:
        lines.append("---")
        lines.append("")
        lines.append("## 季军赛（BO3）")
        lines.append("")
        t1, t2, winner, score = results["3rd"]
        loser_abbr = t2["abbr"] if winner == t1["abbr"] else t1["abbr"]
        lines.append(f"| 对阵 | 比分 | 胜者 |")
        lines.append(f"|------|------|------|")
        lines.append(f"| **{t1['abbr']}** vs **{t2['abbr']}** | {score} | 🥉 **{winner}** |")
        lines.append("")

    # 总决赛
    lines.append("---")
    lines.append("")
    lines.append("## 总决赛（BO5）")
    lines.append("")
    t1, t2, winner, score, runner_up = results["Final"]
    lines.append(f"| 对阵 | 比分 | 🏆 总冠军 |")
    lines.append(f"|------|------|-----------|")
    lines.append(f"| **{t1['abbr']}** vs **{t2['abbr']}** | {score} | 👑 **{winner}** |")
    lines.append("")

    # 最终排名
    lines.append("---")
    lines.append("")
    lines.append("## 季后赛最终排名")
    lines.append("")
    lines.append("| 排名 | 战队 | 世界赛资格 |")
    lines.append("|------|------|-----------|")
    for r in results["ranking"]:
        lines.append(f"| {r['rank']} | **{r['abbr']}** {r['full']} | {r['note']} |")

    return "\n".join(lines)


# ============================================================
# 主流程
# ============================================================
def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    sim_path = os.path.join(output_dir, "sim_s_league_output.md")

    print("=" * 60)
    print("  S级联赛季后赛模拟器")
    print("=" * 60)

    # 读取常规赛排名
    teams = read_final_standings(sim_path)
    if teams is None:
        return

    print(f"\n[常规赛前8名]")
    for t in teams:
        print(f"  #{t['rank']} {t['abbr']} {t['full']}  {t['pts']}分  {t['wins']}-{t['losses']}")

    # 运行季后赛
    results = run_playoffs(teams)

    # 输出
    output = format_playoff_output(teams, results)
    output_path = os.path.join(output_dir, "playoffs_s_league_output.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"\n[完成] 季后赛战报已生成 → {output_path}")

    # 打印冠军
    champ = results["ranking"][0]
    print(f"\n{'=' * 60}")
    print(f"  🏆 S7 总冠军: {champ['abbr']} {champ['full']}")
    print(f"  🌍 世界赛资格: 小组赛直通")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
