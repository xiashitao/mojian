"""
bazibase.rules.fortune
======================

大运 / 流年 喜忌判断 (luck-pillar & annual-year favorability).

子平真诠 论行运: 运的吉凶不看运本身漂不漂亮，而看它**对命局格局是帮还是破**——
带来相神、助旺用神(吉格)、或制住凶神(凶格) → 吉；带来忌神、或助旺凶神 → 凶。

This reuses the natal 相神/忌神 mapping (`XIANG_JI_TABLE`) as the single source
of truth, so a luck/annual pillar's favorability is **derived deterministically
from the chart's 用神/格局**, never invented. Each verdict carries the 十神
reasoning and a 子平真诠 citation.

Scope (v1): each pillar is judged against the natal 格局 independently. 流年×大运
interaction (流年 modulated by the running 大运) is a later refinement.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..constants import ten_god
from ..pillars import Pillar
from .schema import Rule, RuleCitation, register_rule
from .xiang_shen import XIANG_JI_TABLE


_R_YUN = register_rule(Rule(
    id="ZP-YUN-001",
    chapter="子平真诠·论行运",
    source_text=(
        "运者，命之所行。喜用所行之地则吉，忌神所行之地则凶。"
        "故看运与看命无二法，不过以运之干支配命之喜忌而已。"
    ),
    modern_summary=(
        "大运、流年的吉凶，由其干支十神对命局格局的喜忌决定："
        "助相神/用神(吉格)、制凶神(凶格)则吉；引忌神、助凶神则凶。"
    ),
    category="fortune",
    priority=20,
))


# 吉格顺用 (财官印食的正格): 行用神之地为助；凶格逆用 (杀伤枭刃): 行凶神自身之地为增凶。
_AUSPICIOUS_GE = frozenset({"正官", "正财", "偏财", "正印", "食神"})
_INAUSPICIOUS_GE = frozenset({"七杀", "伤官", "偏印"})

# Role → score. 天干为主(权重1)，地支本气为辅(权重0.5)。
_ROLE_SCORE = {"喜": 1.0, "助用": 0.6, "平": 0.0, "增凶": -0.6, "忌": -1.0}
_BRANCH_WEIGHT = 0.5


@dataclass(frozen=True)
class TenGodRole:
    """One stem's 十神 and its role relative to the natal 格局."""
    stem: str
    ten_god: str
    role: str        # 喜 | 忌 | 助用 | 增凶 | 平
    note: str


@dataclass(frozen=True)
class PillarFortune:
    """Favorability verdict for one 大运/流年 pillar against the natal 格局."""
    pillar: str                 # 干支, e.g. "壬寅"
    verdict: str                # 吉 | 凶 | 参半 | 平 | 未定
    stem: TenGodRole
    branch: TenGodRole | None
    reason: str
    citations: tuple[RuleCitation, ...] = ()

    def to_dict(self) -> dict:
        return {
            "pillar": self.pillar,
            "verdict": self.verdict,
            "stem": {"char": self.stem.stem, "ten_god": self.stem.ten_god,
                     "role": self.stem.role},
            "branch": (
                {"char": self.branch.stem, "ten_god": self.branch.ten_god,
                 "role": self.branch.role}
                if self.branch else None
            ),
            "reason": self.reason,
        }


def _classify(stem: str, ten_god_name: str, *, yong: str,
              xiang: tuple[str, ...], ji: tuple[str, ...],
              auspicious: bool) -> TenGodRole:
    if ten_god_name in ji:
        return TenGodRole(stem, ten_god_name, "忌", f"{ten_god_name}为忌神，破用神")
    if ten_god_name in xiang:
        return TenGodRole(stem, ten_god_name, "喜", f"{ten_god_name}为相神，护用神")
    if ten_god_name == yong:
        if auspicious:
            return TenGodRole(stem, ten_god_name, "助用", f"{ten_god_name}助旺用神")
        return TenGodRole(stem, ten_god_name, "增凶", f"{ten_god_name}使凶神更旺")
    return TenGodRole(stem, ten_god_name, "平", f"{ten_god_name}与格局无直接喜忌")


def assess_pillar_fortune(
    day_master: str,
    yong_shen_ten_god: str | None,
    pillar: Pillar,
) -> PillarFortune:
    """
    Judge a 大运/流年 pillar's favorability against the natal 格局.

    Args:
        day_master: The day stem (日主).
        yong_shen_ten_god: The natal 用神's 十神 (from the diagnosis). When
            None or a 比劫 type with no 相神/忌神 mapping, the verdict is 未定.
        pillar: The 大运/流年 Pillar (stem + branch + hidden stems).

    Returns:
        PillarFortune with an overall verdict and the 十神 reasoning.
    """
    stem_tg = ten_god(day_master, pillar.stem)

    if not yong_shen_ten_god or yong_shen_ten_god not in XIANG_JI_TABLE:
        return PillarFortune(
            pillar=pillar.stem_branch,
            verdict="未定",
            stem=TenGodRole(pillar.stem, stem_tg, "平", "用神未定或比劫格，运势喜忌待定"),
            branch=None,
            reason="命局用神未定（或为比劫格），无法据格局判此运吉凶。",
            citations=(),
        )

    xiang, ji = XIANG_JI_TABLE[yong_shen_ten_god]
    auspicious = yong_shen_ten_god in _AUSPICIOUS_GE
    stem_role = _classify(pillar.stem, stem_tg, yong=yong_shen_ten_god,
                          xiang=xiang, ji=ji, auspicious=auspicious)

    branch_role: TenGodRole | None = None
    if pillar.hidden_stems:
        bstem = pillar.hidden_stems[0]
        branch_role = _classify(bstem, ten_god(day_master, bstem),
                                yong=yong_shen_ten_god, xiang=xiang, ji=ji,
                                auspicious=auspicious)

    s_val = _ROLE_SCORE[stem_role.role]
    b_val = _ROLE_SCORE[branch_role.role] if branch_role else 0.0

    # Opposite non-zero signs between 天干 and 地支 → 参半 (mixed).
    if s_val * b_val < 0:
        verdict = "参半"
    else:
        score = s_val + _BRANCH_WEIGHT * b_val
        verdict = "吉" if score >= 0.5 else "凶" if score <= -0.5 else "平"

    reason = _build_reason(verdict, stem_role, branch_role)
    citation = RuleCitation(
        rule_id=_R_YUN.id,
        reason=(
            f"以运之干支配命局喜忌：天干{stem_role.stem}({stem_role.ten_god}/{stem_role.role})"
            + (f"，地支本气{branch_role.stem}({branch_role.ten_god}/{branch_role.role})"
               if branch_role else "")
        ),
        conclusion=f"此运判为「{verdict}」",
    )
    return PillarFortune(
        pillar=pillar.stem_branch,
        verdict=verdict,
        stem=stem_role,
        branch=branch_role,
        reason=reason,
        citations=(citation,),
    )


def _build_reason(verdict: str, stem: TenGodRole, branch: TenGodRole | None) -> str:
    parts = [f"天干{stem.stem}（{stem.note}）"]
    if branch:
        parts.append(f"地支{branch.stem}（{branch.note}）")
    head = "、".join(parts)
    tail = {
        "吉": "整体助益格局，为吉运。",
        "凶": "整体不利格局，为凶运。",
        "参半": "干支一喜一忌，吉凶参半，以天干所主为重。",
        "平": "对格局无显著助破，运势平平。",
        "未定": "",
    }[verdict]
    return f"{head}；{tail}"


__all__ = [
    "TenGodRole",
    "PillarFortune",
    "assess_pillar_fortune",
]
