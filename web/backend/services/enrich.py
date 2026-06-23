"""统一增强 chart/diagnosis 数据：纳音、空亡、六亲、五行力量。"""
from bazibase import STEM_ELEMENT, BRANCH_ELEMENT, BRANCH_HIDDEN_STEMS
from bazibase import ten_god as compute_ten_god
from .nayin import get_nayin
from .kong_wang import get_kong_wang, is_void
from .liuqin import ten_god_to_relative


def enrich_chart(chart_dict: dict) -> dict:
    """给 Chart.to_dict() 输出追加纳音、空亡、六亲、五行力量字段。

    不修改原始结构，只追加 enrichment 数据。
    """
    gender = chart_dict["input"]["gender"]
    day_master = chart_dict["day_master"]

    # --- 四柱增强 ---
    void_year = get_kong_wang(chart_dict["four_pillars"]["year"]["stem_branch"])
    void_month = get_kong_wang(chart_dict["four_pillars"]["month"]["stem_branch"])
    void_day = get_kong_wang(chart_dict["four_pillars"]["day"]["stem_branch"])
    void_hour = get_kong_wang(chart_dict["four_pillars"]["hour"]["stem_branch"])

    for pos, (v1, v2) in [
        ("year", void_year), ("month", void_month),
        ("day", void_day), ("hour", void_hour),
    ]:
        pillar = chart_dict["four_pillars"][pos]
        pillar["nayin"] = get_nayin(pillar["stem_branch"])
        pillar["void_branches"] = list((v1, v2))
        # 该柱地支是否落入日柱空亡
        pillar["branch_is_void"] = is_void(pillar["branch"]["char"],
                                           chart_dict["four_pillars"]["day"]["stem_branch"])
        # 六亲
        pillar["stem"]["relative"] = ten_god_to_relative(
            pillar["stem"]["ten_god"], gender) if pillar["stem"]["ten_god"] != "日主" else "自身"
        # 地支主气的十神和六亲
        branch_hidden = pillar["branch"]["hidden_stems"]
        if branch_hidden:
            main_hidden = branch_hidden[0]
            pillar["branch"]["ten_god"] = main_hidden["ten_god"]
            pillar["branch"]["relative"] = ten_god_to_relative(main_hidden["ten_god"], gender)
        else:
            pillar["branch"]["ten_god"] = ""
            pillar["branch"]["relative"] = ""

    chart_dict["void_info"] = {
        "year": list(void_year),
        "month": list(void_month),
        "day": list(void_day),
        "hour": list(void_hour),
    }

    # --- 五行力量分布 ---
    element_counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for pos in ("year", "month", "day", "hour"):
        pillar = chart_dict["four_pillars"][pos]
        # 天干
        stem_char = pillar["stem"]["char"]
        el = STEM_ELEMENT.get(stem_char, "")
        if el:
            element_counts[el] += 1
        # 地支主气
        branch_char = pillar["branch"]["char"]
        el = BRANCH_ELEMENT.get(branch_char, "")
        if el:
            element_counts[el] += 1
        # 藏干（权重递减：本气1, 中气0.5, 余气0.3 — 简化版用整数计数）
        for hidden in pillar["branch"]["hidden_stems"]:
            el = STEM_ELEMENT.get(hidden["char"], "")
            if el:
                element_counts[el] += 1

    total = sum(element_counts.values())
    chart_dict["element_distribution"] = {
        el: {
            "count": count,
            "percentage": round(count / total * 100, 1) if total > 0 else 0,
        }
        for el, count in element_counts.items()
    }
    chart_dict["element_total"] = total

    # --- 大运六亲 ---
    for luck in chart_dict["luck"]["pillars"]:
        sb = luck["stem_branch"]
        stem = sb[0]
        branch = sb[1]
        luck["stem_ten_god"] = compute_ten_god(day_master, stem)
        luck["stem_relative"] = ten_god_to_relative(luck["stem_ten_god"], gender)
        # 地支主气的十神
        hidden_stems = BRANCH_HIDDEN_STEMS.get(branch, ())
        if hidden_stems:
            main_hidden = hidden_stems[0]
            luck["branch_ten_god"] = compute_ten_god(day_master, main_hidden)
            luck["branch_relative"] = ten_god_to_relative(luck["branch_ten_god"], gender)
        else:
            luck["branch_ten_god"] = ""
            luck["branch_relative"] = ""

    return chart_dict


def enrich_luck_year(stem_branch: str, day_master: str, gender: str) -> dict:
    """给流年干支计算十神和六亲。"""
    stem = stem_branch[0]
    branch = stem_branch[1]
    stem_tg = compute_ten_god(day_master, stem)
    hidden_stems = BRANCH_HIDDEN_STEMS.get(branch, ())
    branch_tg = compute_ten_god(day_master, hidden_stems[0]) if hidden_stems else ""
    return {
        "stem_ten_god": stem_tg,
        "stem_relative": ten_god_to_relative(stem_tg, gender),
        "branch_ten_god": branch_tg,
        "branch_relative": ten_god_to_relative(branch_tg, gender) if branch_tg else "",
    }
