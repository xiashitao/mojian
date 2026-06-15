"""
bazibase.rules.yong_shen
========================

用神取法 (yong-shen determination) — the foundation of 子平派 analysis.

Implements the algorithm from 《子平真诠·论用神》:

    八字用神，专凭月令。
    月令本气透出天干者，用此透出之神；
    本气不透，透中气者，用中气透出之神；
    本中气俱不透，方用余气透出之神。
    如三气俱不透，则用月令本气。
    如月令本气为比劫（建禄月劫羊刃），弃之不用，另寻用神。

Algorithm priority (for non-比劫 cases):
    1. 月令本气透干 → 用本气
    2. 月令本气不透，中气透干 → 用中气
    3. 月令本气中气俱不透，余气透干 → 用余气
    4. 三气俱不透 → 用月令本气（暗用）
    5. 月令为比劫（建禄月劫羊刃）→ 另寻用神（v1 returns a placeholder
       flag; full algorithm needs deeper analysis deferred to Layer 2.2）

"透干" definition: the hidden stem appears in 年干 / 月干 / 时干
(NOT 日干, which is the 日主).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..chart import Chart
from ..constants import (
    BRANCH_HIDDEN_STEMS,
    STEM_ELEMENT,
    ten_god,
)
from .schema import Rule, RuleCitation, register_rule


# ---------------------------------------------------------------------------
# Rule library — registered at import time
# ---------------------------------------------------------------------------

_R_YONG_PREFACE = register_rule(Rule(
    id="ZP-YONG-000",
    chapter="子平真诠·论用神",
    source_text="八字用神，专凭月令。",
    modern_summary="用神的核心来源是月令（出生月的地支）。",
    category="yong_shen",
    priority=10,
))

_R_YONG_BENQI_TOU = register_rule(Rule(
    id="ZP-YONG-001",
    chapter="子平真诠·论用神",
    source_text="月令本气透出天干者，用此透出之神。",
    modern_summary="月令本气（如寅月的甲）若透出在年/月/时干，即用本气为用神。",
    category="yong_shen",
    priority=20,
))

_R_YONG_ZHONGQI_TOU = register_rule(Rule(
    id="ZP-YONG-002",
    chapter="子平真诠·论用神",
    source_text="本气不透，透中气者，用中气透出之神。",
    modern_summary="月令本气未透干，但中气透干，则用中气为用神。",
    category="yong_shen",
    priority=30,
))

_R_YONG_YUQI_TOU = register_rule(Rule(
    id="ZP-YONG-003",
    chapter="子平真诠·论用神",
    source_text="本中气俱不透，方用余气透出之神。",
    modern_summary="月令本气中气俱未透干，仅余气透干，则用余气。",
    category="yong_shen",
    priority=40,
))

_R_YONG_AN_YONG = register_rule(Rule(
    id="ZP-YONG-004",
    chapter="子平真诠·论用神",
    source_text="如三气俱不透，则用月令本气。",
    modern_summary="月令藏干均未透干，仍用月令本气（暗用）。",
    category="yong_shen",
    priority=50,
))

_R_YONG_BI_JIE = register_rule(Rule(
    id="ZP-YONG-005",
    chapter="子平真诠·论用神 / 论建禄月劫",
    source_text="如月令本气为比劫，弃之不用，另寻用神。",
    modern_summary=(
        "月令本气与日主同五行（比肩或劫财）时，月令本身不能为用神。"
        "此类格局另名：建禄（本气为日主之禄）、月劫（本气为劫财）、羊刃（阳干之劫财）。"
        "需在月令之外另寻用神。"
    ),
    category="yong_shen",
    priority=15,  # 比劫判定优先级最高，要先识别再分流
))

# ----- v0.2.1: 比劫当令的另寻用神规则 -----
# 来源：《子平真诠·论建禄月劫》《论羊刃》
# 优先级：官星 → 七杀 → 财星 → 印星 → 食伤 → 无

_R_YONG_ALT_GUAN = register_rule(Rule(
    id="ZP-YONG-006",
    chapter="子平真诠·论建禄月劫",
    source_text=(
        "建禄月劫，无格可取，无官可用，只论日主之情。"
        "故必取财官食伤之最有情者，以为用神。最宜官星。"
    ),
    modern_summary=(
        "建禄月劫格优先在月令之外寻正官为用神；"
        "透干（年/月/时干）优先，藏干（年/日/时支）次之。"
    ),
    category="yong_shen",
    priority=25,
))

_R_YONG_ALT_SHA = register_rule(Rule(
    id="ZP-YONG-007",
    chapter="子平真诠·论建禄月劫 / 论羊刃",
    source_text=(
        "官不可得，七杀亦可。羊刃格尤喜七杀以制刃，"
        "盖阳刃性刚，必用七杀以制之，方成大器。"
    ),
    modern_summary=(
        "无正官时取七杀为用神；羊刃格最喜七杀制刃。"
    ),
    category="yong_shen",
    priority=26,
))

_R_YONG_ALT_CAI = register_rule(Rule(
    id="ZP-YONG-008",
    chapter="子平真诠·论建禄月劫",
    source_text=(
        "无官无杀，取财为用。盖财可生官，亦能资身。"
    ),
    modern_summary=(
        "官杀俱无时取财星（正财或偏财）为用神。"
    ),
    category="yong_shen",
    priority=27,
))

_R_YONG_ALT_YIN = register_rule(Rule(
    id="ZP-YONG-009",
    chapter="子平真诠·论建禄月劫",
    source_text=(
        "财官俱无，取印为用。印能护身，亦能生身。"
    ),
    modern_summary=(
        "财官俱无时取印星（正印或偏印）为用神。"
    ),
    category="yong_shen",
    priority=28,
))

_R_YONG_ALT_SHI_SHANG = register_rule(Rule(
    id="ZP-YONG-010",
    chapter="子平真诠·论建禄月劫 / 论羊刃",
    source_text=(
        "若印亦无，取食伤泄日主之秀气为用。"
        "羊刃无杀，取食伤泄之亦可。"
    ),
    modern_summary=(
        "官杀财印俱无时取食神或伤官泄日主之秀气为用神。"
    ),
    category="yong_shen",
    priority=29,
))

_R_YONG_ALT_NONE = register_rule(Rule(
    id="ZP-YONG-011",
    chapter="子平真诠·论建禄月劫",
    source_text=(
        "若财官印食伤俱无，则用神真不可取，八字非贵命。"
    ),
    modern_summary=(
        "天干与地支藏干中均无可取之用神，标记为未定。"
    ),
    category="yong_shen",
    priority=30,
))


# 优先级表：(候选十神元组, 对应规则)
_ALT_PRIORITY_TABLE: tuple[tuple[tuple[str, ...], Rule], ...] = (
    (("正官",), _R_YONG_ALT_GUAN),
    (("七杀",), _R_YONG_ALT_SHA),
    (("正财", "偏财"), _R_YONG_ALT_CAI),
    (("正印", "偏印"), _R_YONG_ALT_YIN),
    (("食神", "伤官"), _R_YONG_ALT_SHI_SHANG),
)


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TransparentStem:
    """Record of a 月令藏干 that appears in 天干."""
    hidden_stem: str          # the hidden stem character
    role: str                 # 本气 / 中气 / 余气
    transparent_at: str       # which position: "year" / "month" / "hour"


@dataclass(frozen=True)
class YongShenResult:
    """
    Result of 用神取法.

    Attributes:
        stem: The chosen 用神 stem (single char).
        ten_god: 十神 of 用神 relative to day master (e.g. "七杀").
        source_rule_id: The rule id that determined this 用神.
        citations: List of citations explaining the reasoning.
        transparent_stems: Debug info — which hidden stems were transparent.
        is_bi_jie: True if 月令本气 is 比肩/劫财 (special case).
        unresolved: True if 用神 couldn't be determined (e.g., 比劫当令
            with no obvious candidate). In this case `stem` may be None.
        alternative_source: For 比劫当令 cases where an alternative was
            found, describes where (e.g. "透于hour干" or "藏于year支本气").
            None for non-比劫 cases or when unresolved.
    """
    stem: Optional[str]
    ten_god: Optional[str]
    source_rule_id: str
    citations: list[RuleCitation]
    transparent_stems: tuple[TransparentStem, ...]
    is_bi_jie: bool = False
    unresolved: bool = False
    alternative_source: Optional[str] = None

    def summary(self) -> str:
        if self.unresolved or self.stem is None:
            return f"用神未定（{self.citations[-1].conclusion}）"
        alt = f"，{self.alternative_source}" if self.alternative_source else ""
        return f"用神={self.stem}（{self.ten_god}）by {self.source_rule_id}{alt}"


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _find_transparent_stems(chart: Chart) -> list[TransparentStem]:
    """
    Find which 月令藏干 also appear in 年/月/时干.

    日干 (日主) is excluded — it is the reference, not a 透干.
    """
    month_branch = chart.month_pillar.branch
    hidden = BRANCH_HIDDEN_STEMS[month_branch]
    roles = ("本气", "中气", "余气")

    sky_stems_by_pos = {
        "year": chart.year_pillar.stem,
        "month": chart.month_pillar.stem,
        "hour": chart.hour_pillar.stem,
    }

    out: list[TransparentStem] = []
    for i, hs in enumerate(hidden):
        role = roles[i] if i < len(roles) else f"杂气{i}"
        for pos, sky_stem in sky_stems_by_pos.items():
            if hs == sky_stem:
                out.append(TransparentStem(
                    hidden_stem=hs,
                    role=role,
                    transparent_at=pos,
                ))
    return out


def _is_bi_or_jie(day_master: str, hidden_stem: str) -> bool:
    """True if `hidden_stem` is 比肩 or 劫财 of `day_master`."""
    tg = ten_god(day_master, hidden_stem)
    return tg in ("比肩", "劫财")


# ---------------------------------------------------------------------------
# v0.2.1: Alternative 用神 search for 比劫当令 cases
# ---------------------------------------------------------------------------

def _find_alternative_yong_shen(
    chart: Chart,
) -> tuple[Optional[str], Optional[str], Optional[str], list[RuleCitation]]:
    """
    Search for an alternative 用神 when 月令 is 比劫当令 (建禄/月劫/羊刃).

    Algorithm (per 《子平真诠·论建禄月劫》):
        For each priority tier (正官 → 七杀 → 财 → 印 → 食伤):
            1. Search 天干 (year/month/hour stems, excluding 日干) in
               positional order year → month → hour.
            2. If not found, search 藏干 of year/day/hour branches
               (NOT 月令, which is already known to be 比劫).

    "透干" (transparent in 天干) is preferred over "藏干" (hidden in 地支)
    because 透干 is active while 藏干 is passive.

    Args:
        chart: A Chart from Layer 1 whose 月令本气 is 比劫.

    Returns:
        (stem, ten_god, position_description, citations)
        stem/ten_god/position_description are None if no candidate found.
        citations always contains any tier-rule citations we considered.
    """
    dm = chart.day_master
    citations: list[RuleCitation] = []

    # ----- 搜索空间 -----
    # 天干（排除日干 = 日主）
    sky_stems: list[tuple[str, str]] = [
        ("year", chart.year_pillar.stem),
        ("month", chart.month_pillar.stem),
        ("hour", chart.hour_pillar.stem),
    ]
    # 藏干（排除月令）
    roles = ("本气", "中气", "余气")
    hidden_stems: list[tuple[str, str, str]] = []
    for pos in ("year", "day", "hour"):
        pillar = getattr(chart, f"{pos}_pillar")
        for i, hs in enumerate(pillar.hidden_stems):
            role = roles[i] if i < len(roles) else f"杂气{i}"
            hidden_stems.append((pos, hs, role))

    # ----- 按优先级搜索 -----
    for target_tgs, rule in _ALT_PRIORITY_TABLE:
        tg_label = "/".join(target_tgs)

        # 第一轮：天干
        for pos, stem in sky_stems:
            if stem == dm:
                continue  # 日主本人不算
            tg = ten_god(dm, stem)
            if tg in target_tgs:
                citations.append(RuleCitation(
                    rule_id=rule.id,
                    reason=(
                        f"月令为比劫当令，弃月令不用；按优先级"
                        f"{tg_label}搜索，{pos}干{stem}为日主之{tg}（透干）"
                    ),
                    conclusion=f"取{stem}为用神（{tg}），透出于{pos}干",
                ))
                return stem, tg, f"透于{pos}干", citations

        # 第二轮：藏干
        for pos, stem, role in hidden_stems:
            if stem == dm:
                continue
            tg = ten_god(dm, stem)
            if tg in target_tgs:
                citations.append(RuleCitation(
                    rule_id=rule.id,
                    reason=(
                        f"月令为比劫当令，弃月令不用；天干无{tg_label}，"
                        f"按藏干搜索，{pos}支{role}{stem}为日主之{tg}"
                    ),
                    conclusion=f"取{stem}为用神（{tg}），藏于{pos}支{role}",
                ))
                return stem, tg, f"藏于{pos}支{role}", citations

    # 所有优先级都未命中
    return None, None, None, citations


def determine_yong_shen(chart: Chart) -> YongShenResult:
    """
    Determine the 用神 (yong-shen) of a chart.

    Implements the deterministic algorithm from 《子平真诠·论用神》.
    For the 比劫当令 special case, returns a flagged result with
    `unresolved=True` — the full alternative 用神 search requires
    more sophisticated analysis deferred to a future Layer 2.2.

    Args:
        chart: A Chart from Layer 1.

    Returns:
        YongShenResult with full citation chain.
    """
    dm = chart.day_master
    month_branch = chart.month_pillar.branch
    hidden = BRANCH_HIDDEN_STEMS[month_branch]
    roles = ("本气", "中气", "余气")
    citations: list[RuleCitation] = []

    # Always cite the preface rule.
    citations.append(RuleCitation(
        rule_id=_R_YONG_PREFACE.id,
        reason=f"月令为{month_branch}（藏：{''.join(hidden)}）",
        conclusion="用神从月令取",
    ))

    transparent = _find_transparent_stems(chart)

    # ----- Special case: 月令本气为比劫 -----
    benqi = hidden[0]
    if _is_bi_or_jie(dm, benqi):
        tg = ten_god(dm, benqi)
        citations.append(RuleCitation(
            rule_id=_R_YONG_BI_JIE.id,
            reason=(
                f"月令{month_branch}本气为{benqi}，"
                f"日主{dm}，{benqi}为日主之{tg}（同五行）"
            ),
            conclusion=(
                f"月令本气为{tg}，弃月令不用，属"
                f"{'建禄' if tg == '比肩' else '月劫/羊刃'}格范畴，需另寻用神"
            ),
        ))

        # v0.2.1: 在月令之外搜索用神
        alt_stem, alt_tg, alt_pos, alt_citations = _find_alternative_yong_shen(chart)
        citations.extend(alt_citations)

        if alt_stem is not None:
            # 找到候选用神
            return YongShenResult(
                stem=alt_stem,
                ten_god=alt_tg,
                source_rule_id=citations[-1].rule_id,
                citations=citations,
                transparent_stems=tuple(transparent),
                is_bi_jie=True,
                unresolved=False,
                alternative_source=alt_pos,
            )
        else:
            # 所有优先级都未命中 — 真无可用神
            citations.append(RuleCitation(
                rule_id=_R_YONG_ALT_NONE.id,
                reason=(
                    f"天干（年/月/时）与地支藏干（年/日/时支）中均无"
                    f"官杀财印食伤可取"
                ),
                conclusion="用神真不可取，标记为未定",
            ))
            return YongShenResult(
                stem=None,
                ten_god=None,
                source_rule_id=_R_YONG_ALT_NONE.id,
                citations=citations,
                transparent_stems=tuple(transparent),
                is_bi_jie=True,
                unresolved=True,
            )

    # ----- Build a role → (stem, transparent_at) map -----
    # Walk hidden in role order 本/中/余.
    for i, hs in enumerate(hidden):
        role = roles[i] if i < len(roles) else None
        if role is None:
            break
        # Is this hidden stem transparent?
        match = next((t for t in transparent if t.role == role), None)
        if match is not None:
            # Found a transparent stem at this priority level. Use it.
            rule_map = {
                "本气": _R_YONG_BENQI_TOU,
                "中气": _R_YONG_ZHONGQI_TOU,
                "余气": _R_YONG_YUQI_TOU,
            }
            rule = rule_map[role]
            tg = ten_god(dm, hs)
            citations.append(RuleCitation(
                rule_id=rule.id,
                reason=(
                    f"月令{month_branch}之{role}{hs}透出于{match.transparent_at}干"
                ),
                conclusion=f"用{hs}为用神（{tg}）",
            ))
            return YongShenResult(
                stem=hs,
                ten_god=tg,
                source_rule_id=rule.id,
                citations=citations,
                transparent_stems=tuple(transparent),
            )

    # ----- No transparent hidden stem: 暗用月令本气 -----
    tg = ten_god(dm, benqi)
    citations.append(RuleCitation(
        rule_id=_R_YONG_AN_YONG.id,
        reason=f"月令{month_branch}藏干{''.join(hidden)}均未透干",
        conclusion=f"用月令本气{benqi}为用神（{tg}，暗用）",
    ))
    return YongShenResult(
        stem=benqi,
        ten_god=tg,
        source_rule_id=_R_YONG_AN_YONG.id,
        citations=citations,
        transparent_stems=tuple(transparent),
    )


__all__ = [
    "TransparentStem",
    "YongShenResult",
    "determine_yong_shen",
    "_find_transparent_stems",
    "_find_alternative_yong_shen",
]
