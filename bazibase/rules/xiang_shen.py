"""
bazibase.rules.xiang_shen
=========================

相神 (xiang-shen) and 忌神 (ji-shen) identification.

Once 用神 (yong-shen) is known, the next question is: **is the 用神
well-protected or under attack?**

- **相神** (Supporting God): gods that *protect* or *assist* the 用神,
  making the格局 actually work. Without 相神, a 用神 alone is fragile.

- **忌神** (Harmful God): gods that *damage* the 用神 directly or
  indirectly. If 忌神 is strong and uncontrolled, the 格局 fails.

The mapping below encodes the canonical 子平派 rules from
《子平真诠·论相神紧要》 and 《论用神成败》:

    用神十神      相神                忌神
    ─────────────────────────────────────────
    正官        财（生官）, 印（护官）  伤官（克官）, 七杀（混杂）
    七杀        食神（制杀）, 印（化杀） 财（党杀，无食制时）
    正财/偏财   食伤（生财）           比劫（夺财）
    正印/偏印   官杀（生印）           财（破印）
    食神        财（食神生财之路）     枭印（枭神夺食，特指偏印克食神）
    伤官        印（伤官配印）, 财（伤官生财） 官（伤官见官，特指正官）

Algorithm:
    1. Given a Chart and YongShenResult, look up the table for the
       用神's 十神.
    2. Search all positions (年/月/日/时 干 + 藏干) for stems whose
       十神 is in 相神 or 忌神 set.
    3. Output XiangShenResult with both lists and full citations.

For 比劫当令 cases (建禄/月劫/羊刃), 相神/忌神 are determined by the
alternative 用神's 十神, not by 比劫 itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..chart import Chart
from ..constants import ten_god
from .schema import Rule, RuleCitation, register_rule
from .yong_shen import YongShenResult


# ---------------------------------------------------------------------------
# Rule library
# ---------------------------------------------------------------------------

_R_XIANG = register_rule(Rule(
    id="ZP-XIANG-001",
    chapter="子平真诠·论相神紧要",
    source_text=(
        "相神无破，贵格乃成。如正官格以财为相，"
        "见财则官有源；以印为相，见印则官有护。"
    ),
    modern_summary=(
        "相神是护卫用神、使格局真正成立的星神。"
        "用神虽立，无相神则格局不固。"
    ),
    category="xiang_shen",
    priority=10,
))

_R_JI = register_rule(Rule(
    id="ZP-JI-001",
    chapter="子平真诠·论用神成败",
    source_text=(
        "用神既立，遇忌神则败。如正官格遇伤官，"
        "财格遇比劫，印格遇财，皆败格之象。"
    ),
    modern_summary=(
        "忌神是克制、合化或损耗用神的星神。"
        "忌神强而无救应，则格局败。"
    ),
    category="xiang_shen",
    priority=11,
))


# 相神/忌神 lookup table: 用神十神 → (相神十神集合, 忌神十神集合)
# Source: 《子平真诠·论用神成败》
XIANG_JI_TABLE: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    # 正官格：相神为财、印；忌神为伤官、七杀（混杂）
    "正官": (("正财", "偏财", "正印", "偏印"), ("伤官", "七杀")),
    # 七杀格：相神为食神（制杀）、印（化杀）；忌神为财（党杀）
    "七杀": (("食神", "正印", "偏印"), ("正财", "偏财")),
    # 正财格：相神为食伤（生财）；忌神为比劫（夺财）
    "正财": (("食神", "伤官"), ("比肩", "劫财")),
    # 偏财格：同正财
    "偏财": (("食神", "伤官"), ("比肩", "劫财")),
    # 正印格：相神为官杀（生印）；忌神为财（破印）
    "正印": (("正官", "七杀"), ("正财", "偏财")),
    # 偏印格：同正印（但偏印另有一忌：见食神则枭神夺食，需另议）
    "偏印": (("正官", "七杀"), ("正财", "偏财")),
    # 食神格：相神为财（食神生财）；忌神为偏印（枭神夺食）
    "食神": (("正财", "偏财"), ("偏印",)),
    # 伤官格：相神为印（伤官配印）、财（伤官生财）；忌神为正官（伤官见官）
    "伤官": (("正印", "偏印", "正财", "偏财"), ("正官",)),
}


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StemOccurrence:
    """A stem at a specific position with its 十神 and role."""
    position: str              # "year" / "month" / "day" / "hour"
    location: str              # "天干" / "本气" / "中气" / "余气"
    stem: str                  # the actual stem character
    ten_god: str               # 十神 of this stem relative to day master


@dataclass(frozen=True)
class XiangShenResult:
    """
    Result of 相神/忌神 identification.

    Attributes:
        xiang_shen: Tuple of StemOccurrence acting as 相神.
        ji_shen: Tuple of StemOccurrence acting as 忌神.
        citations: List of citations explaining the reasoning.
        yong_shen_ten_god: The 用神's 十神 (for context).
        notes: Special notes (e.g., 枭神夺食, 伤官见官).
    """
    xiang_shen: tuple[StemOccurrence, ...]
    ji_shen: tuple[StemOccurrence, ...]
    citations: list[RuleCitation]
    yong_shen_ten_god: Optional[str]
    notes: tuple[str, ...] = ()

    def summary(self) -> str:
        if not self.xiang_shen and not self.ji_shen:
            return "无相神无忌神"
        parts = []
        if self.xiang_shen:
            xs = ", ".join(
                f"{o.stem}({o.ten_god}@{o.position}{o.location})"
                for o in self.xiang_shen
            )
            parts.append(f"相神: {xs}")
        if self.ji_shen:
            js = ", ".join(
                f"{o.stem}({o.ten_god}@{o.position}{o.location})"
                for o in self.ji_shen
            )
            parts.append(f"忌神: {js}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _all_stems_in_chart(chart: Chart) -> list[StemOccurrence]:
    """
    Collect all stems in the chart with position, location, and 十神.

    Includes:
        - All 4 天干 (year/month/day/hour stems)
        - All 藏干 of all 4 地支 (year/month/day/hour branches)

    日干 (日主) is excluded — it is the reference, not an acting god.

    藏干 of 月令 are excluded from 忌神/相神 search if they include the
    用神 itself (which is normal — the 用神 often lives in 月令).
    """
    dm = chart.day_master
    out: list[StemOccurrence] = []
    roles = ("本气", "中气", "余气")

    # 天干 (skip 日干)
    for pos in ("year", "month", "hour"):
        pillar = getattr(chart, f"{pos}_pillar")
        tg = ten_god(dm, pillar.stem)
        out.append(StemOccurrence(
            position=pos, location="天干",
            stem=pillar.stem, ten_god=tg,
        ))

    # 藏干 (all 4 branches)
    for pos in ("year", "month", "day", "hour"):
        pillar = getattr(chart, f"{pos}_pillar")
        for i, hs in enumerate(pillar.hidden_stems):
            role = roles[i] if i < len(roles) else f"杂气{i}"
            tg = ten_god(dm, hs)
            out.append(StemOccurrence(
                position=pos, location=role,
                stem=hs, ten_god=tg,
            ))

    return out


def identify_xiang_ji(
    chart: Chart,
    ys: YongShenResult,
) -> XiangShenResult:
    """
    Identify 相神 and 忌神 for a chart given its 用神 result.

    Args:
        chart: A Chart from Layer 1.
        ys: A YongShenResult from `determine_yong_shen`.

    Returns:
        XiangShenResult with lists of 相神/忌神 occurrences and citations.

    Note:
        If 用神 is unresolved (ys.stem is None), returns an empty result
        with a note explaining the prerequisite is missing.
    """
    citations: list[RuleCitation] = []
    notes: list[str] = []

    # Prerequisite: 用神 must be determined
    if ys.stem is None or ys.ten_god is None:
        notes.append("用神未定，无法识别相神/忌神")
        return XiangShenResult(
            xiang_shen=(),
            ji_shen=(),
            citations=citations,
            yong_shen_ten_god=None,
            notes=tuple(notes),
        )

    ys_tg = ys.ten_god
    if ys_tg not in XIANG_JI_TABLE:
        notes.append(f"用神十神 {ys_tg} 无相神/忌神映射（比劫类）")
        return XiangShenResult(
            xiang_shen=(),
            ji_shen=(),
            citations=citations,
            yong_shen_ten_god=ys_tg,
            notes=tuple(notes),
        )

    xiang_tgs, ji_tgs = XIANG_JI_TABLE[ys_tg]
    all_stems = _all_stems_in_chart(chart)

    # Exclude the 用神 itself (by stem char, position-independent)
    xiang_list = [s for s in all_stems if s.ten_god in xiang_tgs and s.stem != ys.stem]
    ji_list = [s for s in all_stems if s.ten_god in ji_tgs and s.stem != ys.stem]

    # Build citations
    xiang_label = "/".join(xiang_tgs)
    ji_label = "/".join(ji_tgs)

    if xiang_list:
        xiang_chars = "、".join(f"{s.stem}({s.ten_god})" for s in xiang_list)
        citations.append(RuleCitation(
            rule_id=_R_XIANG.id,
            reason=(
                f"用神{ys.stem}（{ys_tg}）之相神应为 {xiang_label}，"
                f"命中见：{xiang_chars}"
            ),
            conclusion=f"相神已现，护卫用神",
        ))
    else:
        citations.append(RuleCitation(
            rule_id=_R_XIANG.id,
            reason=(
                f"用神{ys.stem}（{ys_tg}）之相神应为 {xiang_label}，"
                f"命中无相神"
            ),
            conclusion=f"相神不现，格局根基不稳",
        ))

    if ji_list:
        ji_chars = "、".join(f"{s.stem}({s.ten_god})" for s in ji_list)
        citations.append(RuleCitation(
            rule_id=_R_JI.id,
            reason=(
                f"用神{ys.stem}（{ys_tg}）之忌神为 {ji_label}，"
                f"命中见：{ji_chars}"
            ),
            conclusion=f"忌神已现，恐破用神",
        ))
    else:
        citations.append(RuleCitation(
            rule_id=_R_JI.id,
            reason=(
                f"用神{ys.stem}（{ys_tg}）之忌神为 {ji_label}，"
                f"命中无忌神"
            ),
            conclusion=f"忌神不现，用神无损",
        ))

    # Special notes
    if ys_tg == "食神" and any(s.ten_god == "偏印" for s in ji_list):
        notes.append("枭神夺食：偏印为食神之忌，食神格最忌偏印透干")
    if ys_tg == "伤官" and any(s.ten_god == "正官" for s in ji_list):
        notes.append("伤官见官：伤官与正官同现，为祸百端")
    if ys_tg == "正官" and any(s.ten_god == "七杀" for s in ji_list):
        notes.append("官杀混杂：正官与七杀同现，格局不纯")

    return XiangShenResult(
        xiang_shen=tuple(xiang_list),
        ji_shen=tuple(ji_list),
        citations=citations,
        yong_shen_ten_god=ys_tg,
        notes=tuple(notes),
    )


__all__ = [
    "StemOccurrence",
    "XiangShenResult",
    "XIANG_JI_TABLE",
    "identify_xiang_ji",
]
