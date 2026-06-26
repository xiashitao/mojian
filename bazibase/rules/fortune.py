"""
bazibase.rules.fortune
======================

大运 / 流年 行运事实 (luck-pillar & annual-year facts).

子平真诠 论行运: 运的吉凶看它对命局格局是帮还是破。**但"帮还是破、顺还是逆"的
综合权衡是判断，不是确定的事实**——按"确定交引擎、不确定交模型"的分工，本模块
只产出**确定的事实**：

  · 运/年 干支的十神，及其相对命局用神/格局的角色（喜/忌/助用/增凶/平）——
    由 `XIANG_JI_TABLE` 确定性推出。
  · 运/年 地支与**命局四支**、以及**当前大运支**之间的刑冲合会关系（查表即得），
    并标注被作用支的喜忌角色（确定）。

它**不再输出「吉/凶/参半/平」的 verdict**：顺逆的综合权衡（含"原命局是车、大运是
路、流年是当下，要综合看"）交给上层 LLM 去做。
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from ..constants import (
    BRANCH_HIDDEN_STEMS,
    ELEMENT_CONQUEST,
    ELEMENT_PRODUCTION,
    STEM_ELEMENT,
    ten_god,
)
from ..pillars import Pillar
from .interactions import (
    HAI_TABLE,
    LIU_CHONG_TABLE,
    SAN_HE_TABLE,
    SAN_HUI_TABLE,
    XING_HU_TYPES,
    XING_SAN_TYPES,
    ZI_XING_BRANCHES,
)
from .schema import Rule, RuleCitation, register_rule
from .xiang_shen import XIANG_JI_TABLE

# Clean pairwise 相刑, derived from the 三刑/互刑 sets but with 冲 pairs removed
# (寅申、丑未 are 六冲, recorded as 冲 not 刑). 自刑 handled separately.
_XING_PAIRS: set[frozenset[str]] = set(XING_HU_TYPES)
for _trio in XING_SAN_TYPES:
    for _a, _b in combinations(_trio, 2):
        _pair = frozenset({_a, _b})
        if _pair not in LIU_CHONG_TABLE:
            _XING_PAIRS.add(_pair)

# 地支六合 (not in interactions.py). 巳申 is both 六合 and 刑 (合中带刑).
_LIU_HE_PAIRS: frozenset[frozenset[str]] = frozenset({
    frozenset({"子", "丑"}), frozenset({"寅", "亥"}), frozenset({"卯", "戌"}),
    frozenset({"辰", "酉"}), frozenset({"巳", "申"}), frozenset({"午", "未"}),
})

# Reverse 生/克 cycles: who produces / conquers a given element.
_PRODUCED_BY = {v: k for k, v in ELEMENT_PRODUCTION.items()}  # 生我者
_CONQUERED_BY = {v: k for k, v in ELEMENT_CONQUEST.items()}   # 克我者

# 吉格顺用 (财官印食的正格): 行用神之地为助；凶格逆用 (杀伤枭刃): 行用神之地为增凶。
_AUSPICIOUS_GE = frozenset({"正官", "正财", "偏财", "正印", "食神"})


_R_YUN = register_rule(Rule(
    id="ZP-YUN-001",
    chapter="子平真诠·论行运",
    source_text=(
        "运者，命之所行。喜用所行之地则吉，忌神所行之地则凶。"
        "故看运与看命无二法，不过以运之干支配命之喜忌而已。"
    ),
    modern_summary=(
        "大运、流年的喜忌，由其干支十神对命局格局的喜忌、以及与命局/大运的刑冲合会"
        "决定。本引擎只给出这些确定事实，顺逆的综合权衡交由上层判断。"
    ),
    category="fortune",
    priority=20,
))


def _ten_god_element(day_master: str, ten_god_name: str) -> str:
    """The 五行 of a 十神 relative to the 日主 (so we can tag a 合成局)."""
    dm = STEM_ELEMENT[day_master]
    if ten_god_name in ("比肩", "劫财"):
        return dm
    if ten_god_name in ("食神", "伤官"):
        return ELEMENT_PRODUCTION[dm]
    if ten_god_name in ("偏财", "正财"):
        return ELEMENT_CONQUEST[dm]
    if ten_god_name in ("七杀", "正官"):
        return _CONQUERED_BY[dm]
    if ten_god_name in ("偏印", "正印"):
        return _PRODUCED_BY[dm]
    return dm


@dataclass(frozen=True)
class TenGodRole:
    """One stem's 十神 and its role relative to the natal 格局."""
    stem: str
    ten_god: str
    role: str        # 喜 | 忌 | 助用 | 增凶 | 平
    note: str


@dataclass(frozen=True)
class PillarFacts:
    """确定的行运事实 for one 大运/流年 pillar — 十神角色 + 与命局/大运的刑冲合会。

    **No 吉凶 verdict**: weighing 顺逆 is the LLM's job (确定交引擎，不确定交模型).
    """
    pillar: str                          # 干支, e.g. "壬寅"
    stem: TenGodRole
    branch: TenGodRole | None
    relations: tuple[str, ...] = ()      # 刑冲合会关系（事实）
    yong_unknown: bool = False           # 用神未定/比劫格：十神喜忌无法标
    citations: tuple[RuleCitation, ...] = ()

    def to_dict(self) -> dict:
        def role_dict(r: TenGodRole | None) -> dict | None:
            if r is None:
                return None
            return {"char": r.stem, "ten_god": r.ten_god, "role": r.role, "note": r.note}

        return {
            "pillar": self.pillar,
            "stem": role_dict(self.stem),
            "branch": role_dict(self.branch),
            "relations": list(self.relations),
            "yong_unknown": self.yong_unknown,
        }


def _classify(stem: str, ten_god_name: str, *, yong: str | None,
              xiang: tuple[str, ...], ji: tuple[str, ...],
              auspicious: bool) -> TenGodRole:
    if ten_god_name in ji:
        return TenGodRole(stem, ten_god_name, "忌", f"{ten_god_name}为忌神，破用神")
    if ten_god_name in xiang:
        return TenGodRole(stem, ten_god_name, "喜", f"{ten_god_name}为相神，护用神")
    if yong is not None and ten_god_name == yong:
        if auspicious:
            return TenGodRole(stem, ten_god_name, "助用", f"{ten_god_name}助旺用神")
        return TenGodRole(stem, ten_god_name, "增凶", f"{ten_god_name}使凶神更旺")
    return TenGodRole(stem, ten_god_name, "平", f"{ten_god_name}与格局无直接喜忌")


def _branch_role(branch: str, day_master: str, *, yong: str | None,
                 xiang: tuple[str, ...], ji: tuple[str, ...],
                 auspicious: bool) -> TenGodRole | None:
    """The 喜/忌/助用/平 role of a branch by its 本气十神."""
    hidden = BRANCH_HIDDEN_STEMS.get(branch)
    if not hidden:
        return None
    return _classify(branch, ten_god(day_master, hidden[0]),
                     yong=yong, xiang=xiang, ji=ji, auspicious=auspicious)


def _role_tag(branch: str, day_master: str, *, yong: str | None,
              xiang: tuple[str, ...], ji: tuple[str, ...], auspicious: bool) -> str:
    """A factual 喜忌 tag for a clashed/combined branch, e.g. '（正财，命局忌神）'.
    Empty when 用神 unknown or the branch is neutral — no judgment, just the fact.
    """
    role = _branch_role(branch, day_master, yong=yong, xiang=xiang, ji=ji,
                        auspicious=auspicious)
    if role is None:
        return ""
    if role.role in ("忌", "增凶"):
        return f"（{role.ten_god}，命局忌神）"
    if role.role in ("喜", "助用"):
        return f"（{role.ten_god}，命局喜用）"
    return ""


def _el_tag(element: str, yong_el: str | None, ke_yong: str | None) -> str:
    """Factual tag for a 合成局's element vs the 用神 五行."""
    if yong_el and element == yong_el:
        return f"（{element}为用神五行）"
    if ke_yong and element == ke_yong:
        return f"（{element}克用神五行）"
    return ""


def _pillar_relations(
    subject_branch: str, *, natal_branches: tuple[str, ...],
    luck_branch: str | None, day_master: str, yong: str | None,
    xiang: tuple[str, ...], ji: tuple[str, ...], auspicious: bool,
    yong_el: str | None,
) -> list[str]:
    """确定的关系事实：subject 支 与 命局四支 / 当前大运支 的 冲/刑/害/六合/三合/三会。

    标注被作用支的喜忌角色（确定），但**不下"吉/凶"判断**——那交给上层综合。
    """
    notes: list[str] = []
    targets: list[tuple[str, str]] = [(nb, "命局") for nb in dict.fromkeys(natal_branches)]
    if luck_branch:
        targets.append((luck_branch, "大运"))

    def tag(b: str) -> str:
        return _role_tag(b, day_master, yong=yong, xiang=xiang, ji=ji, auspicious=auspicious)

    for tb, label in targets:
        pair = frozenset({subject_branch, tb})
        if len(pair) == 2 and pair in LIU_CHONG_TABLE:
            notes.append(f"冲{label}{tb}{tag(tb)}")
            continue  # 同一支以冲为重，不再记刑/害
        if pair in _XING_PAIRS or (subject_branch == tb and subject_branch in ZI_XING_BRANCHES):
            notes.append(f"与{label}{tb}相刑")
        if len(pair) == 2 and pair in HAI_TABLE:
            notes.append(f"与{label}{tb}相害")
        if pair in _LIU_HE_PAIRS:
            notes.append(f"与{label}{tb}六合{tag(tb)}")

    # 三合局 / 三会方 over the natal + 大运 branch pool.
    pool = set(natal_branches) | ({luck_branch} if luck_branch else set())
    ke_yong = _CONQUERED_BY.get(yong_el) if yong_el else None
    for table, kind, allow_half in (
        (SAN_HE_TABLE, "三合", True),
        (SAN_HUI_TABLE, "三会", False),
    ):
        for combo, element in table:
            if subject_branch not in combo:
                continue
            others = combo - {subject_branch}
            present = others & pool
            if present == others:
                notes.append(f"与{'、'.join(sorted(present))}成{kind}{element}局"
                             f"{_el_tag(element, yong_el, ke_yong)}")
            elif allow_half and len(present) == 1:
                notes.append(f"与{next(iter(present))}半合{element}局"
                             f"{_el_tag(element, yong_el, ke_yong)}")
    return notes


def assess_pillar_facts(
    day_master: str,
    yong_shen_ten_god: str | None,
    pillar: Pillar,
    *,
    natal_branches: tuple[str, ...] = (),
    luck_branch: str | None = None,
) -> PillarFacts:
    """
    Collect the **deterministic facts** about a 大运/流年 pillar.

    Args:
        day_master: The day stem (日主).
        yong_shen_ten_god: The natal 用神's 十神. None / a 比劫 type with no
            相神/忌神 mapping → roles can't be labelled (`yong_unknown=True`),
            but 干支十神 and 刑冲合会 relationships are still reported.
        pillar: The 大运/流年 Pillar.
        natal_branches: The chart's four 地支 — to detect 刑冲合会 with this pillar.
        luck_branch: The branch of the *current 大运*. Pass it when assessing a
            流年 so the facts include 流年×大运 relationships ("综合起来看").

    Returns:
        PillarFacts — 十神 roles + relationship facts. **No 吉凶 verdict.**
    """
    stem_tg = ten_god(day_master, pillar.stem)
    yong_unknown = (not yong_shen_ten_god) or (yong_shen_ten_god not in XIANG_JI_TABLE)

    if yong_unknown:
        stem_role = TenGodRole(pillar.stem, stem_tg, "平", f"{stem_tg}（用神未定，喜忌待判）")
        branch_role: TenGodRole | None = None
        if pillar.hidden_stems:
            b = pillar.hidden_stems[0]
            branch_role = TenGodRole(b, ten_god(day_master, b), "平", "用神未定，喜忌待判")
        relations = _pillar_relations(
            pillar.branch, natal_branches=natal_branches, luck_branch=luck_branch,
            day_master=day_master, yong=None, xiang=(), ji=(), auspicious=False,
            yong_el=None,
        )
        return PillarFacts(pillar.stem_branch, stem_role, branch_role,
                           tuple(relations), True, ())

    xiang, ji = XIANG_JI_TABLE[yong_shen_ten_god]
    auspicious = yong_shen_ten_god in _AUSPICIOUS_GE
    stem_role = _classify(pillar.stem, stem_tg, yong=yong_shen_ten_god,
                          xiang=xiang, ji=ji, auspicious=auspicious)
    branch_role = None
    if pillar.hidden_stems:
        bstem = pillar.hidden_stems[0]
        branch_role = _classify(bstem, ten_god(day_master, bstem),
                                yong=yong_shen_ten_god, xiang=xiang, ji=ji,
                                auspicious=auspicious)

    relations = _pillar_relations(
        pillar.branch, natal_branches=natal_branches, luck_branch=luck_branch,
        day_master=day_master, yong=yong_shen_ten_god, xiang=xiang, ji=ji,
        auspicious=auspicious, yong_el=_ten_god_element(day_master, yong_shen_ten_god),
    )
    citation = RuleCitation(
        rule_id=_R_YUN.id,
        reason=(
            f"以运之干支配命局喜忌：天干{stem_role.stem}({stem_role.ten_god}/{stem_role.role})"
            + (f"，地支本气{branch_role.stem}({branch_role.ten_god}/{branch_role.role})"
               if branch_role else "")
            + (f"；关系：{'、'.join(relations)}" if relations else "")
        ),
        conclusion="（确定事实，顺逆由上层综合判断）",
    )
    return PillarFacts(pillar.stem_branch, stem_role, branch_role,
                       tuple(relations), False, (citation,))


__all__ = [
    "TenGodRole",
    "PillarFacts",
    "assess_pillar_facts",
]
