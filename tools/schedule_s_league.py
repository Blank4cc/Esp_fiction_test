#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S级联赛（星脉超级联赛）赛程生成器
===============================
根据 league_structure.md 和 teams_archive.md 的数据，
一键生成16支战队双循环30轮完整赛程，输出为 Markdown 表格格式。

赛制：双循环（主客场各一次），每轮8场对阵，共30轮。
赛程中预留：清明节、劳动节、端午节休赛 + 季中赛两周空档。
"""

import os
from datetime import date, timedelta

# ============================================================
# 赛季日历常量（2052年）
# ============================================================
SEASON_START = date(2052, 3, 1)       # 赛季起始日
FAST_ROUNDS = 10                       # 前10轮快节奏（周三/周六交替）

# 休赛期定义（start, end, 名称, 图标）
BREAKS = [
    (date(2052, 4,  4), date(2052, 4,  6), "清明节",  "🌿"),
    (date(2052, 5,  1), date(2052, 5,  5), "劳动节黄金周", "💼"),
    (date(2052, 6,  7), date(2052, 6,  9), "端午节",  "🐉"),
]

# 季中赛（单独标记，不占轮次但插入战报说明）
MID_SEASON_BREAK = (date(2052, 6, 14), date(2052, 6, 27), "全球季中赛（Rift Mid-Season Clash）", "🏆")


def is_break_day(d):
    """检查某日是否在休赛期内。返回 (is_break, break_name, icon)"""
    for start, end, name, icon in BREAKS:
        if start <= d <= end:
            return True, name, icon
    ms_start, ms_end, ms_name, ms_icon = MID_SEASON_BREAK
    if ms_start <= d <= ms_end:
        return True, ms_name, ms_icon
    return False, "", ""


# ============================================================
# 数据区：16支S级战队
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
    """圆圈法生成双循环赛程。"""
    n = len(teams)
    if n % 2 != 0:
        raise ValueError("队伍数必须为偶数")
    half_rounds = n - 1
    all_rounds = []
    fixed = n - 1
    circle = list(range(n - 1))
    for r in range(half_rounds):
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
    for r in range(half_rounds):
        first_half = all_rounds[r]
        all_rounds.append([(away, home) for (home, away) in first_half])
    return all_rounds


def generate_dates_with_breaks(start_date, num_rounds):
    """
    生成赛程日期序列，跳过节假日和季中赛休赛期。
    
    返回:
      dates: list[date] - 每轮比赛日期
      breaks_between: list[(after_round, break_desc)] - 轮次之间插入的休赛说明
    """
    dates = []
    breaks_between = []
    current = start_date
    prev_break_name = None

    for r in range(num_rounds):
        # 确定本轮目标星期几
        if r < FAST_ROUNDS:
            target_wd = 5 if r % 2 == 0 else 2  # 周六 / 周三
        else:
            target_wd = 5  # 仅周六

        # 找到下一个非休赛的比赛日
        skipped_set = {}  # {break_name: icon}
        while True:
            while current.weekday() != target_wd:
                current += timedelta(days=1)

            is_brk, brk_name, brk_icon = is_break_day(current)
            if not is_brk:
                break
            if brk_name not in skipped_set:
                skipped_set[brk_name] = brk_icon
            current += timedelta(days=1)

        if skipped_set:
            combined = " / ".join(f"{icon} {name}" for name, icon in skipped_set.items())
            breaks_between.append((r + 1, combined))

        dates.append(current)
        current += timedelta(days=1)

    return dates, breaks_between


def format_schedule_md(teams, all_rounds, dates, breaks_between):
    """将赛程格式化为 Markdown，含休赛期标记。"""
    weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    lines = []

    # 文档头部
    lines.append("# S级联赛（星脉超级联赛）— 完整赛程")
    lines.append("")
    lines.append(f"> **赛季**: S7 | **战队**: 16支 | **赛制**: 双循环（主客场各一次）| **共**: {len(all_rounds)}轮 | **单场**: BO2")
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

    # 构建break查找表：break在round_x之后
    break_map = {after_r: desc for after_r, desc in breaks_between}

    # 前半程
    half_point = len(all_rounds) // 2
    lines.append("## 前半程（第 1–15 轮）")
    lines.append("")

    for round_idx, (round_matches, match_date) in enumerate(zip(all_rounds, dates)):
        # 半程分界
        if round_idx == half_point:
            lines.append("---")
            lines.append("")
            lines.append("## 后半程（第 16–30 轮）")
            lines.append("")

        wd = weekdays[match_date.weekday()]
        lines.append(f"### 第 {round_idx + 1:02d} 轮 — {match_date.strftime('%Y-%m-%d')}（{wd}）")
        lines.append("")
        lines.append("| # | 主场战队 | | 客场战队 | 主场城市 |")
        lines.append("|---|----------|---|----------|----------|")

        for i, (home_idx, away_idx) in enumerate(round_matches, 1):
            home_team = teams[home_idx]
            away_team = teams[away_idx]
            home_full = f"**{home_team['abbr']}** {home_team['full']}"
            away_full = f"**{away_team['abbr']}** {away_team['full']}"
            lines.append(f"| {i} | {home_full} | vs | {away_full} | {home_team['city']} |")

        lines.append("")

        # 本轮之后的休赛标记
        after_r = round_idx + 1
        if after_r in break_map:
            lines.append(f"> ⏸ **休赛**：{break_map[after_r]}")
            lines.append("")

    # 统计摘要
    lines.append("---")
    lines.append("")
    lines.append("## 统计摘要")
    lines.append("")
    lines.append("| 项目 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总轮次 | {len(all_rounds)} |")
    lines.append(f"| 总场次 | {len(all_rounds) * len(all_rounds[0])} |")
    lines.append(f"| 起始日期 | {dates[0].strftime('%Y-%m-%d')} |")
    lines.append(f"| 结束日期 | {dates[-1].strftime('%Y-%m-%d')} |")
    lines.append(f"| 每队比赛场数 | {(len(teams) - 1) * 2} |")
    lines.append(f"| 休赛周 | 清明节、劳动节、端午节 + 季中赛2周 |")
    lines.append("")

    # === 季后赛 ===
    lines.append("---")
    lines.append("")
    lines.append("## 季后赛（S7 星脉超级联赛季后赛）")
    lines.append("")
    lines.append("> 🏆 **赛段**: 常规赛结束后 | **参赛**: 常规赛积分前8名 | **时间**: 约3周（8月）")
    lines.append("")
    lines.append("### 赛制")
    lines.append("")
    lines.append("- **四分之一决赛**：BO3 单败，种子排位 #1 vs #8 / #4 vs #5 / #3 vs #6 / #2 vs #7")
    lines.append("- **败者组**：常规赛前4名种子若在四分之一决赛落败，获得一次败者组复活机会（BO3）")
    lines.append("- **半决赛**：BO3")
    lines.append("- **决赛**：BO5")
    lines.append("- **世界赛资格**：季后赛前3名获得世界冠军赛参赛名额（第1名直接晋级小组赛，第2、3名参加入围赛）")
    lines.append("")
    lines.append("### 日程表")
    lines.append("")
    lines.append("| 日期 | 阶段 | 对阵 | 场次 |")
    lines.append("|------|------|------|------|")
    lines.append("| 08/02（周六） | 四分之一决赛 Day1 | #1 vs #8 / #4 vs #5 | BO3 ×2 |")
    lines.append("| 08/03（周日） | 四分之一决赛 Day2 | #3 vs #6 / #2 vs #7 | BO3 ×2 |")
    lines.append("| 08/09（周六） | 败者组 | 前4种子败者对阵 | BO3 |")
    lines.append("| 08/10（周日） | 半决赛 Day1 | QF胜者对阵 | BO3 |")
    lines.append("| 08/16（周六） | 半决赛 Day2 + 败者组决赛 | — | BO3 ×2 |")
    lines.append("| 08/23（周六） | 总决赛 | — | BO5 |")
    lines.append("")
    lines.append("### 晋级对阵图（模板）")
    lines.append("")
    lines.append("```")
    lines.append("四分之一决赛          半决赛            决赛")
    lines.append("─────────────────────────────────────────────")
    lines.append(" #1 ──┐")
    lines.append("      ├─ QF1胜者 ──┐")
    lines.append(" #8 ──┘             │")
    lines.append("                    ├─ SF1胜者 ──┐")
    lines.append(" #4 ──┐             │            │")
    lines.append("      ├─ QF2胜者 ──┘            │")
    lines.append(" #5 ──┘                          │")
    lines.append("                                 ├─ 总冠军")
    lines.append(" #3 ──┐                          │")
    lines.append("      ├─ QF3胜者 ──┐            │")
    lines.append(" #6 ──┘             │            │")
    lines.append("                    ├─ SF2胜者 ──┘")
    lines.append(" #2 ──┐             │")
    lines.append("      ├─ QF4胜者 ──┘")
    lines.append(" #7 ──┘")
    lines.append("")
    lines.append("败者组（仅#1–#4种子L可进入）：")
    lines.append("  LB → 胜者获得季军 / 世界赛第3名额")
    lines.append("```")
    lines.append("")

    # === 世界冠军赛 ===
    lines.append("---")
    lines.append("")
    lines.append("## 世界冠军赛（Rift World Championship · RWC）")
    lines.append("")
    lines.append("> 🌍 **主办**: 星脉动力 | **地点**: 沪江市 裂界穹顶 | **时间**: 10月–12月")
    lines.append("")
    lines.append("### 中国赛区名额")
    lines.append("")
    lines.append("| 名额 | 资格来源 | 说明 |")
    lines.append("|------|---------|------|")
    lines.append("| 1 | S级季后赛冠军 | 直接晋级小组赛 |")
    lines.append("| 2 | S级季后赛亚军 | 参加入围赛 |")
    lines.append("| 3 | S级季后赛季军 | 参加入围赛 |")
    lines.append("")
    lines.append("### 全球赛区名额分配")
    lines.append("")
    lines.append("| 赛区 | 名额 | 直接入组 | 入围赛 |")
    lines.append("|------|------|---------|--------|")
    lines.append("| 🇨🇳 中国赛区 | 4 | 1 | 3 |")
    lines.append("| 🇰🇷 韩国赛区 | 3 | 2 | 1 |")
    lines.append("| 🌏 东南亚赛区 | 2 | 0 | 2 |")
    lines.append("| 🇪🇺 欧洲赛区 | 2 | 1 | 1 |")
    lines.append("| 🇺🇸 北美赛区 | 2 | 1 | 1 |")
    lines.append("| 🌎 其他赛区 | 3 | 0 | 3 |")
    lines.append("| **合计** | **16** | **5** | **11** |")
    lines.append("")
    lines.append("### 赛程表")
    lines.append("")
    lines.append("| 日期 | 阶段 | 说明 |")
    lines.append("|------|------|------|")
    lines.append("| 10/04–10/18 | 入围赛 | 11队单败淘汰BO3，决出5席进入小组赛 |")
    lines.append("| 11/01–11/08 | 小组赛 Week1 | 16队瑞士轮（五轮三胜晋级），BO3 |")
    lines.append("| 11/15–11/22 | 小组赛 Week2 | 瑞士轮继续，决出8强 |")
    lines.append("| 12/06–12/07 | 八强赛 | BO5 双败制 |")
    lines.append("| 12/13–12/14 | 半决赛 | BO5 双败制 |")
    lines.append("| 12/27（周六） | 总决赛 | BO5，裂界穹顶 |")
    lines.append("")
    lines.append("### 赛制结构")
    lines.append("")
    lines.append("```")
    lines.append("入围赛（11队 BO3单败）→ 5队晋级")
    lines.append("         ↓")
    lines.append("小组赛（16队 瑞士轮 5轮3胜 BO3）→ 8队晋级")
    lines.append("         ↓")
    lines.append("八强赛（BO5 双败）→ 4队晋级")
    lines.append("         ↓")
    lines.append("半决赛（BO5 双败）→ 2队晋级")
    lines.append("         ↓")
    lines.append("总决赛（BO5 · 裂界穹顶）→ 🏆 世界冠军")
    lines.append("```")
    lines.append("")

    # 战队缩写对照
    lines.append("---")
    lines.append("")
    lines.append("## 战队缩写对照表")
    lines.append("")
    lines.append("| 编号 | 缩写 | 全称 | 主场城市 |")
    lines.append("|------|------|------|----------|")
    for t in teams:
        lines.append(f"| {t['id']} | **{t['abbr']}** | {t['full']} | {t['city']} |")

    return "\n".join(lines)


def main():
    all_rounds = generate_round_robin_schedule(S_TEAMS)

    season_start = SEASON_START
    while season_start.weekday() != 5:
        season_start += timedelta(days=1)

    dates, breaks_between = generate_dates_with_breaks(season_start, len(all_rounds))
    output = format_schedule_md(S_TEAMS, all_rounds, dates, breaks_between)

    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "schedule_s_league_output.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"[完成] S级联赛赛程已生成 → {output_path}")
    print(f"  共 {len(all_rounds)} 轮，{len(all_rounds) * 8} 场对阵")
    # 输出休赛断点供核对
    for after_r, desc in breaks_between:
        print(f"  ⏸ 第 {after_r - 1} 轮后：{desc}")


if __name__ == "__main__":
    main()
