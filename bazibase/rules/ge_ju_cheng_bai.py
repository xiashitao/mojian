"""
bazibase.rules.ge_ju_cheng_bai
==============================

格局成败 (pattern success/failure) assessment.

Given 用神, 相神, 忌神, we determine whether the格局 succeeds:

    **成格** (successful): 用神有力 + 相神护卫到位 + 忌神被制或不存在
    **败格** (failed):     忌神强且无救应，直接破坏用神
    **救应** (rescued):    败格之后另有星神制忌神，反败为成

Source: 《子平真诠·论用神成败》

Examples (from 子平真诠):
    - 正官格 + 财相 + 印相 → 成格（财生官，印护官）
    - 正官格 + 伤官忌无制 → 败格
    - 正官格 + 伤官忌 + 印制伤官 → 救应（印为救神）
    - 七杀格 + 食制杀 + 无财党杀 → 成格
    - 七杀格 + 无食无印 + 财党杀 → 败格
    - 财格 + 食伤相 + 无比劫 → 成格
    - 财格 + 比劫忌无制 → 败格
    - 印格 + 官杀相 → 成格
    - 印格 + 财忌 + 比劫制财 → 救应
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal

from ..chart import Chart
from .schema import Rule, RuleCitation, register_rule
from .yong_shen import YongShenResult
from .ge_ju import GeJuResult
from .xiang_shen import XiangShenResult, StemOccurrence


# ---------------------------------------------------------------------------
# Rule library
# ---------------------------------------------------------------------------

_R_CHENG = register_rule(Rule(
    id="ZP-CHENG-001",
    chapter="子平真诠·论用神成败",
    source_text=(
        "用神既立，遇相神则成，遇忌神则败。"
        "如正官格，有财生之，有印护之，乃成格也。"
    ),
    modern_summary=(
        "成格：用神已立，相神到位且无破坏，忌神不现或被制。"
    ),
    category="cheng_bai",
    priority=10,
))

_R_BAI = register_rule(Rule(
    id="ZP-BAI-001",
    chapter="子平真诠·论用神成败",
    source_text=(
        "遇忌神而无救应者，败格也。"
        "如正官格遇伤官，财格遇比劫，皆败。"
    ),
    modern_summary=(
        "败格：忌神强且无救应，直接破坏用神或相神。"
    ),
    category="cheng_bai",
    priority=11,
))

_R_JIU_YING = register_rule(Rule(
    id="ZP-JIUYING-001",
    chapter="子平真诠·论用神成败",
    source_text=(
        "败格之中，复有救应，反败为成。"
        "如正官格遇伤官，有印制伤官，则印为救神，反成贵格。"
    ),
    modern_summary=(
        "救应：忌神虽现，但被其他星神所制，格局反败为成。"
    ),
    category="cheng_bai",
    priority=12,
))


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

Verdict = Literal["成格", "败格", "救应", "未定"]


@dataclass(frozen=True)
class ChengBaiResult:
    """
    Result of 格局成败 assessment.

    Attributes:
        verdict: "成格" / "败格" / "救应" / "未定".
        source_rule_id: The rule that determined this verdict.
        rescue_gods: If 救应, the gods that rescued the pattern.
        citations: Citations explaining the reasoning.
        unresolved: True if the verdict couldn't be determined.
    """
    verdict: Verdict
    source_rule_id: str
    rescue_gods: tuple[StemOccurrence, ...]
    citations: list[RuleCitation]
    unresolved: bool = False

    def summary(self) -> str:
        if self.unresolved:
            return f"{self.verdict}（未定）"
        if self.verdict == "救应" and self.rescue_gods:
            rescues = "、".join(f"{g.stem}({g.ten_god})" for g in self.rescue_gods)
            return f"救应成格（救神：{rescues}）"
        return self.verdict


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _find_rescue_gods(
    ys: YongShenResult,
    xs_result: XiangShenResult,
) -> list[StemOccurrence]:
    """
    Find 救神 (rescue gods) that can control the 忌神.

    A 救神 is any 相神 that happens to also control the 忌神 in 五行
    terms. In practice, the simplest version is: if 忌神 exists and
    相神 also exists, the 相神 may serve as 救神.

    For example:
        正官格 + 伤官忌 + 印相 → 印制伤官，印为救神

    NOTE: This is a simplified model. The strict 子平派 logic requires
    五行 interaction analysis (e.g., 印木 vs 财金 — 金克木，印不能制财).
    The full 五行制化 analysis is deferred to v0.2.3 (刑冲合化).
    Until then, this function uses the heuristic that 相神 presence is
    sufficient to *potentially* rescue the格局. Treat the resulting
    "救应" verdict as a candidate requiring deeper analysis, not a
    final determination.
    """
    if not xs_result.ji_shen or not xs_result.xiang_shen:
        return []

    # Simplified rescue rule: 相神 is always a potential 救神 for 忌神.
    return list(xs_result.xiang_shen)


def assess_cheng_bai(
    chart: Chart,
    ys: YongShenResult,
    gj: GeJuResult,
    xs: XiangShenResult,
) -> ChengBaiResult:
    """
    Assess whether the格局 is 成 (successful), 败 (failed), or 救应 (rescued).

    Args:
        chart: A Chart.
        ys: YongShenResult from `determine_yong_shen`.
        gj: GeJuResult from `determine_ge_ju`.
        xs: XiangShenResult from `identify_xiang_ji`.

    Returns:
        ChengBaiResult with verdict and citations.
    """
    citations: list[RuleCitation] = []

    # Prerequisite: 用神 must be determined
    if ys.stem is None:
        citations.append(RuleCitation(
            rule_id=_R_CHENG.id,
            reason="用神未定，无法评估格局成败",
            conclusion="成败未定",
        ))
        return ChengBaiResult(
            verdict="未定",
            source_rule_id=_R_CHENG.id,
            rescue_gods=(),
            citations=citations,
            unresolved=True,
        )

    # Prerequisite: must have a 用神十神 in our table
    if ys.ten_god not in ("正官", "七杀", "正财", "偏财", "正印", "偏印",
                          "食神", "伤官"):
        # 比劫当令且未取到另寻用神的极少见 case
        citations.append(RuleCitation(
            rule_id=_R_CHENG.id,
            reason=f"用神十神为 {ys.ten_god}（不在八大正格之列）",
            conclusion="成败评估跳过",
        ))
        return ChengBaiResult(
            verdict="未定",
            source_rule_id=_R_CHENG.id,
            rescue_gods=(),
            citations=citations,
            unresolved=True,
        )

    # ---- Determine verdict ----
    has_xiang = bool(xs.xiang_shen)
    has_ji = bool(xs.ji_shen)

    # Case 1: 无忌神 → 成格（用神已立，且无破坏）
    if not has_ji:
        if has_xiang:
            xiang_str = "、".join(
                f"{o.stem}({o.ten_god})" for o in xs.xiang_shen
            )
            citations.append(RuleCitation(
                rule_id=_R_CHENG.id,
                reason=(
                    f"用神{ys.stem}（{ys.ten_god}）已立，"
                    f"相神{xiang_str}现而护卫，命中无忌神破坏"
                ),
                conclusion="相神护卫到位且无忌神，定为成格",
            ))
            return ChengBaiResult(
                verdict="成格",
                source_rule_id=_R_CHENG.id,
                rescue_gods=(),
                citations=citations,
            )
        else:
            citations.append(RuleCitation(
                rule_id=_R_CHENG.id,
                reason=(
                    f"用神{ys.stem}（{ys.ten_god}）已立，"
                    f"无相神护卫但亦无忌神破坏"
                ),
                conclusion="格局成立但根基稍弱（无相神）",
            ))
            return ChengBaiResult(
                verdict="成格",
                source_rule_id=_R_CHENG.id,
                rescue_gods=(),
                citations=citations,
            )

    # Case 2: 忌神现 + 有救神 → 救应成格
    rescue_gods = _find_rescue_gods(ys, xs)
    if rescue_gods:
        ji_str = "、".join(f"{o.stem}({o.ten_god})" for o in xs.ji_shen)
        rescue_str = "、".join(f"{g.stem}({g.ten_god})" for g in rescue_gods)
        citations.append(RuleCitation(
            rule_id=_R_JIU_YING.id,
            reason=(
                f"用神{ys.stem}（{ys.ten_god}）忌神{ji_str}虽现，"
                f"但相神{rescue_str}可制忌神"
            ),
            conclusion=f"反败为成，{rescue_str}为救神",
        ))
        return ChengBaiResult(
            verdict="救应",
            source_rule_id=_R_JIU_YING.id,
            rescue_gods=tuple(rescue_gods),
            citations=citations,
        )

    # Case 3: 忌神现 + 无救神 → 败格
    ji_str = "、".join(f"{o.stem}({o.ten_god})" for o in xs.ji_shen)
    citations.append(RuleCitation(
        rule_id=_R_BAI.id,
        reason=(
            f"用神{ys.stem}（{ys.ten_god}）被忌神{ji_str}所破，"
            f"且无相神可救"
        ),
        conclusion="忌神破用神而无救应，定为败格",
    ))
    return ChengBaiResult(
        verdict="败格",
        source_rule_id=_R_BAI.id,
        rescue_gods=(),
        citations=citations,
    )


__all__ = [
    "Verdict",
    "ChengBaiResult",
    "assess_cheng_bai",
]
