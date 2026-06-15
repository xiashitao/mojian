"""
bazibase.rules.ge_ju
====================

格局判定 (pattern determination).

Once 用神 is known (from `yong_shen.determine_yong_shen`), the 格局
is largely determined by mapping the 用神's 十神 to a named pattern.

Eight 正格 (orthodox patterns):

    用神十神     格局名
    ─────────────────────
    正官         正官格
    七杀         七杀格 (又称偏官格)
    正财         正财格
    偏财         偏财格
    正印         正印格
    偏印         偏印格 (又称枭神格 / 枭印格)
    食神         食神格
    伤官         伤官格

Plus three special patterns for 比劫当令:

    月令本气        格局名
    ────────────────────────────
    与日主同（比肩）建禄格
    与日主劫财      月劫格（阴干） / 羊刃格（阳干）

羊刃严格定义：阳干（甲丙戊庚壬）月令为劫财时为羊刃格；
阴干（乙丁己辛癸）月令为劫财时为月劫格。两者本质上都是
"月令为劫财"，区别在于羊刃更"凶"，需要特别制化。

Source: 《子平真诠·论正官》《论七杀》《论正财》《论偏财》
        《论印绶》《论食神》《论伤官》《论建禄月劫》《论羊刃》
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..chart import Chart
from ..constants import ten_god, STEM_POLARITY
from .schema import Rule, RuleCitation, register_rule
from .yong_shen import YongShenResult


# ---------------------------------------------------------------------------
# Rule library
# ---------------------------------------------------------------------------

# Mapping rule: 用神十神 → 格局名
_R_GE_MAPPING = register_rule(Rule(
    id="ZP-GE-MAP",
    chapter="子平真诠·格局总论",
    source_text=(
        "用神既定，则格局随之。官则为正官格，杀则为七杀格，"
        "财印食伤，各以其名配之。"
    ),
    modern_summary="用神确定后，根据其十神属性命名格局。",
    category="ge_ju",
    priority=20,
))

# 比劫当令的特殊格局
_R_GE_JIANLU = register_rule(Rule(
    id="ZP-GE-JIANLU",
    chapter="子平真诠·论建禄月劫",
    source_text="建禄者，月令本气与日主相同，月建为日主之禄。",
    modern_summary="月令本气与日主同（比肩），定为建禄格。",
    category="ge_ju",
    priority=10,
))

_R_GE_YUEJIE = register_rule(Rule(
    id="ZP-GE-YUEJIE",
    chapter="子平真诠·论建禄月劫",
    source_text="月劫者，月令本气与日主异阴阳而同五行，为劫财。",
    modern_summary="阴干月令为劫财，定为月劫格。",
    category="ge_ju",
    priority=10,
))

_R_GE_YANGREN = register_rule(Rule(
    id="ZP-GE-YANGREN",
    chapter="子平真诠·论羊刃",
    source_text="羊刃者，阳干月令为劫财，气势刚烈，故名羊刃。",
    modern_summary="阳干月令为劫财，定为羊刃格（月劫之变）。",
    category="ge_ju",
    priority=10,
))


# 用神十神 → (格局名, 别名)
GE_JU_NAME_BY_TEN_GOD = {
    "正官": ("正官格", None),
    "七杀": ("七杀格", "偏官格"),
    "正财": ("正财格", None),
    "偏财": ("偏财格", None),
    "正印": ("正印格", None),
    "偏印": ("偏印格", "枭神格"),
    "食神": ("食神格", None),
    "伤官": ("伤官格", None),
}


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GeJuResult:
    """
    Result of 格局判定.

    Attributes:
        name: 格局名 like "七杀格", "建禄格".
        alias: Optional alternate name like "偏官格".
        category: "正格" (one of 8) or "建禄月劫" (比劫类) or "未定".
        source_rule_id: Rule id that determined this 格局.
        citations: List of citations explaining the reasoning.
        unresolved: True if 格局 couldn't be determined (e.g., 比劫当令
            with no alternative 用神 available).
    """
    name: str
    alias: Optional[str]
    category: str
    source_rule_id: str
    citations: list[RuleCitation]
    unresolved: bool = False

    def summary(self) -> str:
        if self.unresolved:
            return f"{self.name}（用神未定，需进一步分析）"
        alias_str = f"（又称{self.alias}）" if self.alias else ""
        return f"{self.name}{alias_str} by {self.source_rule_id}"


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def determine_ge_ju(chart: Chart, ys: YongShenResult) -> GeJuResult:
    """
    Determine the 格局 (pattern) given a Chart and 用神 result.

    Args:
        chart: A Chart from Layer 1.
        ys: A YongShenResult from `determine_yong_shen`.

    Returns:
        GeJuResult with citations.
    """
    citations: list[RuleCitation] = []

    # ----- Special case: 比劫当令 -----
    if ys.is_bi_jie:
        dm = chart.day_master
        month_branch = chart.month_pillar.branch
        # Find 本气 of 月令
        from ..constants import BRANCH_HIDDEN_STEMS
        benqi = BRANCH_HIDDEN_STEMS[month_branch][0]
        tg = ten_god(dm, benqi)
        # 比肩 = 建禄, 劫财 = 月劫/羊刃
        if tg == "比肩":
            rule = _R_GE_JIANLU
            name = "建禄格"
            alias = None
            reason_base = f"月令{month_branch}本气{benqi}即日主{dm}之比肩（禄）"
        else:
            # 劫财 — 区分阴干 / 阳干
            is_yang = STEM_POLARITY[dm] == 0
            if is_yang:
                rule = _R_GE_YANGREN
                name = "羊刃格"
                alias = "月劫格之变"
                reason_base = (
                    f"日主{dm}为阳干，月令{month_branch}本气{benqi}为劫财，"
                    f"阳干之劫财气势刚烈，定为羊刃格"
                )
            else:
                rule = _R_GE_YUEJIE
                name = "月劫格"
                alias = None
                reason_base = (
                    f"日主{dm}为阴干，月令{month_branch}本气{benqi}为劫财，"
                    f"定为月劫格"
                )

        # v0.2.1: 用神可能已通过另寻算法找到
        if ys.stem is not None and ys.ten_god is not None:
            reason = (
                f"{reason_base}；月令之外取{ys.stem}（{ys.ten_god}）为用神"
            )
            conclusion = f"定为{name}（用神{ys.stem}）"
            unresolved = False
        else:
            reason = reason_base
            conclusion = f"定为{name}（用神未定）"
            unresolved = True

        citations.append(RuleCitation(
            rule_id=rule.id,
            reason=reason,
            conclusion=conclusion,
        ))
        return GeJuResult(
            name=name,
            alias=alias,
            category="建禄月劫",
            source_rule_id=rule.id,
            citations=citations,
            unresolved=unresolved,
        )

    # ----- Standard case: 用神已知 → 格局由 十神映射 -----
    if ys.ten_god is None or ys.ten_god not in GE_JU_NAME_BY_TEN_GOD:
        # Should not happen if yong_shen was determined, but defensive.
        citations.append(RuleCitation(
            rule_id=_R_GE_MAPPING.id,
            reason=f"用神十神={ys.ten_god!r} 不在标准八格之列",
            conclusion="格局无法判定",
        ))
        return GeJuResult(
            name="未定",
            alias=None,
            category="未定",
            source_rule_id=_R_GE_MAPPING.id,
            citations=citations,
            unresolved=True,
        )

    ge_ju_name, alias = GE_JU_NAME_BY_TEN_GOD[ys.ten_god]
    citations.append(RuleCitation(
        rule_id=_R_GE_MAPPING.id,
        reason=(
            f"用神{ys.stem}为日主之{ys.ten_god}"
        ),
        conclusion=f"用神十神为{ys.ten_god}，定为{ge_ju_name}",
    ))
    return GeJuResult(
        name=ge_ju_name,
        alias=alias,
        category="正格",
        source_rule_id=_R_GE_MAPPING.id,
        citations=citations,
        unresolved=False,
    )


__all__ = [
    "GeJuResult",
    "determine_ge_ju",
    "GE_JU_NAME_BY_TEN_GOD",
]
