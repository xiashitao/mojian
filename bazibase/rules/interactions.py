"""
bazibase.rules.interactions
===========================

刑冲合化 (interactions between stems and branches).

Once a chart is cast, the 4 pillars contain 4 天干 and 4 地支. These
do not exist in isolation — they interact:

    **合 (combination)**: 天干五合 / 地支三合 / 地支三会
        Two or more stems/branches join and may transform into a
        different element. Harmonious, consolidating.

    **冲 (clash)**: 地支六冲
        Two branches in opposing positions (180° on the zodiac wheel).
        Disruptive, agitating.

    **刑 (punishment)**: 地支相刑
        Specific branch patterns that imply friction, legal trouble,
        or self-sabotage.

    **害 (harm)**: 地支相害 / 相穿
        Specific branch pairs that undermine each other.

Source: 《子平真诠·论刑冲合化》《渊海子平·论地支属相》

Notation:
    We use pinyin abbreviations for the interaction kinds:
        HE = 合 (hé, combine)
        CHONG = 冲 (chōng, clash)
        XING = 刑 (xíng, punish)
        HAI = 害 (hài, harm)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal
from itertools import combinations

from ..chart import Chart
from .schema import Rule, RuleCitation, register_rule


# ---------------------------------------------------------------------------
# Rule library
# ---------------------------------------------------------------------------

_R_HE_GAN = register_rule(Rule(
    id="ZP-HE-GAN",
    chapter="子平真诠·论天干五合",
    source_text=(
        "甲己合化土，乙庚合化金，丙辛合化水，"
        "丁壬合化木，戊癸合化火。"
        "两干相合，犹夫妇之合，化气因之而变。"
    ),
    modern_summary=(
        "天干五合：两干相合，若化神有力（得月令或旺相），"
        "则化为化神之五行；否则合而不化，仅为合绊。"
    ),
    category="he_chong_xing_hai",
    priority=20,
))

_R_SAN_HE = register_rule(Rule(
    id="ZP-SAN-HE",
    chapter="子平真诠·论地支三合",
    source_text=(
        "申子辰合水局，亥卯未合木局，"
        "寅午戌合火局，巳酉丑合金局。"
        "三支全见，则化局成；见其二支，为半三合。"
    ),
    modern_summary=(
        "地支三合：三支全见则成局，力量最强；"
        "半三合（两支）次之；半三合又分生地半合与墓地半合。"
    ),
    category="he_chong_xing_hai",
    priority=21,
))

_R_SAN_HUI = register_rule(Rule(
    id="ZP-SAN-HUI",
    chapter="子平真诠·论地支三会",
    source_text=(
        "寅卯辰会东方木，巳午未会南方火，"
        "申酉戌会西方金，亥子丑会北方水。"
        "一方之气聚于一局，其力大于三合。"
    ),
    modern_summary=(
        "地支三会：同一季令的三个地支聚在一起，"
        "形成一方之气。力量强于三合，主导五行倾向。"
    ),
    category="he_chong_xing_hai",
    priority=22,
))

_R_CHONG = register_rule(Rule(
    id="ZP-CHONG",
    chapter="子平真诠·论地支六冲",
    source_text=(
        "子午冲，丑未冲，寅申冲，"
        "卯酉冲，辰戌冲，巳亥冲。"
        "相冲则动，动则生变。"
    ),
    modern_summary=(
        "地支六冲：相对的两个地支相遇，互相冲动。"
        "冲则动变，往往代表奔波、变动、冲突。"
    ),
    category="he_chong_xing_hai",
    priority=23,
))

_R_XING = register_rule(Rule(
    id="ZP-XING",
    chapter="子平真诠·论地支相刑",
    source_text=(
        "寅巳申为三刑，丑戌未为三刑，"
        "子卯为相刑，辰午酉亥为自刑。"
        "刑者，刑罚、刑伤之象，主是非口舌、官非纠纷。"
    ),
    modern_summary=(
        "地支相刑：特定地支组合产生刑罚之象。"
        "三刑全见最重，互刑次之，自刑为自找麻烦。"
    ),
    category="he_chong_xing_hai",
    priority=24,
))

_R_HAI = register_rule(Rule(
    id="ZP-HAI",
    chapter="子平真诠·论地支相害",
    source_text=(
        "子未相害，丑午相害，寅巳相害，"
        "卯辰相害，申亥相害，酉戌相害。"
        "相害者，彼此伤害之象。"
    ),
    modern_summary=(
        "地支相害（穿）：六组地支互相伤害。"
        "力量弱于冲与刑，但亦主小人、口舌、骨肉无情。"
    ),
    category="he_chong_xing_hai",
    priority=25,
))


# ---------------------------------------------------------------------------
# Static tables
# ---------------------------------------------------------------------------

# 天干五合: (stem_a, stem_b) -> transformed element
# Order within pair doesn't matter; both orders are registered.
GAN_HE_TABLE: dict[tuple[str, str], str] = {
    ("甲", "己"): "土", ("己", "甲"): "土",
    ("乙", "庚"): "金", ("庚", "乙"): "金",
    ("丙", "辛"): "水", ("辛", "丙"): "水",
    ("丁", "壬"): "木", ("壬", "丁"): "木",
    ("戊", "癸"): "火", ("癸", "戊"): "火",
}

# 地支三合: frozenset of 3 branches -> resulting element
SAN_HE_TABLE: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"申", "子", "辰"}), "水"),
    (frozenset({"亥", "卯", "未"}), "木"),
    (frozenset({"寅", "午", "戌"}), "火"),
    (frozenset({"巳", "酉", "丑"}), "金"),
)

# 地支三会: frozenset of 3 branches -> resulting element
SAN_HUI_TABLE: tuple[tuple[frozenset[str], str], ...] = (
    (frozenset({"寅", "卯", "辰"}), "木"),
    (frozenset({"巳", "午", "未"}), "火"),
    (frozenset({"申", "酉", "戌"}), "金"),
    (frozenset({"亥", "子", "丑"}), "水"),
)

# 地支六冲: unordered pairs
LIU_CHONG_TABLE: tuple[frozenset[str], ...] = (
    frozenset({"子", "午"}),
    frozenset({"丑", "未"}),
    frozenset({"寅", "申"}),
    frozenset({"卯", "酉"}),
    frozenset({"辰", "戌"}),
    frozenset({"巳", "亥"}),
)

# 地支相刑:
# - 三刑: two triple patterns (寅巳申, 丑戌未)
# - 互刑: 子卯
# - 自刑: 辰午酉亥 (when a branch appears 2+ times, or even once in some schools)
XING_SAN_TYPES: tuple[frozenset[str], ...] = (
    frozenset({"寅", "巳", "申"}),
    frozenset({"丑", "戌", "未"}),
)
XING_HU_TYPES: tuple[frozenset[str], ...] = (
    frozenset({"子", "卯"}),
)
# 自刑: 辰见辰, 午见午, 酉见酉, 亥见亥
ZI_XING_BRANCHES: frozenset[str] = frozenset({"辰", "午", "酉", "亥"})

# 地支相害: unordered pairs
HAI_TABLE: tuple[frozenset[str], ...] = (
    frozenset({"子", "未"}),
    frozenset({"丑", "午"}),
    frozenset({"寅", "巳"}),
    frozenset({"卯", "辰"}),
    frozenset({"申", "亥"}),
    frozenset({"酉", "戌"}),
)


# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

InteractionKind = Literal[
    "天干合", "三合", "半三合", "三会", "半三会",
    "六冲", "三刑", "互刑", "自刑", "相害",
]


@dataclass(frozen=True)
class Interaction:
    """A single detected interaction (合/冲/刑/害) in the chart.

    Attributes:
        kind: The interaction kind (see InteractionKind).
        participants: Position names involved ("year"/"month"/"day"/"hour").
                      For 地支 interactions, these are pillar positions.
                      For 天干 interactions, these are stem positions.
        elements: The actual stem or branch characters involved.
        resulting_element: For 合/会, the transformed element. None otherwise.
        note: Extra context (e.g., "缺子", "生地半合", "墓地半合").
    """
    kind: InteractionKind
    participants: tuple[str, ...]
    elements: tuple[str, ...]
    resulting_element: Optional[str] = None
    note: str = ""


@dataclass(frozen=True)
class InteractionResult:
    """Result of 刑冲合化 analysis on a chart.

    Attributes:
        gan_he: Detected 天干五合 interactions.
        san_he: Detected 地支三合 (full) interactions.
        ban_he: Detected 地支半三合 (2 of 3) interactions.
        san_hui: Detected 地支三会 (full) interactions.
        ban_hui: Detected 地支半三会 (2 of 3) interactions.
        chong: Detected 地支六冲 interactions.
        xing: Detected 地支相刑 (all kinds: 三刑/互刑/自刑) interactions.
        hai: Detected 地支相害 interactions.
        citations: Citations explaining the analysis.
    """
    gan_he: tuple[Interaction, ...]
    san_he: tuple[Interaction, ...]
    ban_he: tuple[Interaction, ...]
    san_hui: tuple[Interaction, ...]
    ban_hui: tuple[Interaction, ...]
    chong: tuple[Interaction, ...]
    xing: tuple[Interaction, ...]
    hai: tuple[Interaction, ...]
    citations: list[RuleCitation]

    def all_interactions(self) -> tuple[Interaction, ...]:
        """Return all interactions in a flat tuple."""
        return (
            *self.gan_he, *self.san_he, *self.ban_he,
            *self.san_hui, *self.ban_hui,
            *self.chong, *self.xing, *self.hai,
        )

    def has_any(self) -> bool:
        """True if at least one interaction was detected."""
        return bool(self.all_interactions())

    def summary(self) -> str:
        if not self.has_any():
            return "无合冲刑害"
        parts = []
        if self.gan_he:
            parts.append("天干合: " + "、".join(
                "+".join(i.elements) for i in self.gan_he
            ))
        if self.san_he:
            parts.append("三合: " + "、".join(
                "+".join(i.elements) + f"→{i.resulting_element}"
                for i in self.san_he
            ))
        if self.ban_he:
            parts.append(f"半三合×{len(self.ban_he)}")
        if self.san_hui:
            parts.append("三会: " + "、".join(
                "+".join(i.elements) + f"→{i.resulting_element}"
                for i in self.san_hui
            ))
        if self.ban_hui:
            parts.append(f"半三会×{len(self.ban_hui)}")
        if self.chong:
            parts.append("冲: " + "、".join(
                "+".join(i.elements) for i in self.chong
            ))
        if self.xing:
            parts.append("刑: " + "、".join(
                "+".join(i.elements) for i in self.xing
            ))
        if self.hai:
            parts.append("害: " + "、".join(
                "+".join(i.elements) for i in self.hai
            ))
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Core algorithm
# ---------------------------------------------------------------------------

def _collect_branches(chart: Chart) -> list[tuple[str, str]]:
    """Return [(position, branch_char), ...] for all 4 branches."""
    out = []
    for pos in ("year", "month", "day", "hour"):
        pillar = getattr(chart, f"{pos}_pillar")
        out.append((pos, pillar.branch))
    return out


def _collect_stems(chart: Chart) -> list[tuple[str, str]]:
    """Return [(position, stem_char), ...] for all 4 stems (including 日干)."""
    out = []
    for pos in ("year", "month", "day", "hour"):
        pillar = getattr(chart, f"{pos}_pillar")
        out.append((pos, pillar.stem))
    return out


def _detect_gan_he(
    stems: list[tuple[str, str]],
) -> list[Interaction]:
    """Detect 天干五合 between any 2 stems in the chart."""
    out: list[Interaction] = []
    # Check all pairs (avoid duplicates by using combinations)
    for (pos_a, s_a), (pos_b, s_b) in combinations(stems, 2):
        key = (s_a, s_b)
        if key in GAN_HE_TABLE:
            element = GAN_HE_TABLE[key]
            out.append(Interaction(
                kind="天干合",
                participants=(pos_a, pos_b),
                elements=(s_a, s_b),
                resulting_element=element,
                note=f"合化{element}",
            ))
    return out


def _detect_san_he(
    branches: list[tuple[str, str]],
) -> tuple[list[Interaction], list[Interaction]]:
    """Detect 地支三合 (full) and 半三合 (2 of 3).

    Returns (full_san_he, ban_san_he).
    """
    full: list[Interaction] = []
    half: list[Interaction] = []

    # Map branch char to list of positions (a branch can repeat)
    branch_to_positions: dict[str, list[str]] = {}
    for pos, b in branches:
        branch_to_positions.setdefault(b, []).append(pos)

    present_branches = set(branch_to_positions.keys())

    for san_set, element in SAN_HE_TABLE:
        present_in_set = present_branches & san_set
        if len(present_in_set) == 3:
            # Full 三合
            positions = tuple(
                branch_to_positions[b][0] for b in san_set
            )
            elements = tuple(san_set)
            full.append(Interaction(
                kind="三合",
                participants=positions,
                elements=elements,
                resulting_element=element,
                note=f"三合{element}局",
            ))
        elif len(present_in_set) == 2:
            # 半三合 — determine which is missing
            missing = next(iter(san_set - present_in_set))
            present_two = tuple(present_in_set)
            # 半三合 subtypes:
            # 生地半合 = has the 生支 (长生位) + 帝旺支
            # 墓地半合 = has the 墓支 + 帝旺支
            # 具体命名需要知道三合的"生/旺/墓"三个位置
            # 申子辰: 申=生, 子=旺, 辰=墓
            # 亥卯未: 亥=生, 卯=旺, 未=墓
            # 寅午戌: 寅=生, 午=旺, 戌=墓
            # 巳酉丑: 巳=生, 酉=旺, 丑=墓
            positions = tuple(
                branch_to_positions[b][0] for b in present_two
            )
            half.append(Interaction(
                kind="半三合",
                participants=positions,
                elements=present_two,
                resulting_element=element,
                note=f"半三合{element}局（缺{missing}）",
            ))

    return full, half


def _detect_san_hui(
    branches: list[tuple[str, str]],
) -> tuple[list[Interaction], list[Interaction]]:
    """Detect 地支三会 (full) and 半三会 (2 of 3).

    Returns (full_san_hui, ban_san_hui).
    """
    full: list[Interaction] = []
    half: list[Interaction] = []

    branch_to_positions: dict[str, list[str]] = {}
    for pos, b in branches:
        branch_to_positions.setdefault(b, []).append(pos)

    present_branches = set(branch_to_positions.keys())

    for hui_set, element in SAN_HUI_TABLE:
        present_in_set = present_branches & hui_set
        if len(present_in_set) == 3:
            positions = tuple(
                branch_to_positions[b][0] for b in hui_set
            )
            full.append(Interaction(
                kind="三会",
                participants=positions,
                elements=tuple(hui_set),
                resulting_element=element,
                note=f"三会{element}方",
            ))
        elif len(present_in_set) == 2:
            missing = next(iter(hui_set - present_in_set))
            present_two = tuple(present_in_set)
            positions = tuple(
                branch_to_positions[b][0] for b in present_two
            )
            half.append(Interaction(
                kind="半三会",
                participants=positions,
                elements=present_two,
                resulting_element=element,
                note=f"半三会{element}（缺{missing}）",
            ))

    return full, half


def _detect_chong(
    branches: list[tuple[str, str]],
) -> list[Interaction]:
    """Detect 地支六冲 between any 2 branches."""
    out: list[Interaction] = []
    for (pos_a, b_a), (pos_b, b_b) in combinations(branches, 2):
        pair = frozenset({b_a, b_b})
        if pair in LIU_CHONG_TABLE and len(pair) == 2:
            out.append(Interaction(
                kind="六冲",
                participants=(pos_a, pos_b),
                elements=(b_a, b_b),
            ))
    return out


def _detect_xing(
    branches: list[tuple[str, str]],
) -> list[Interaction]:
    """Detect 地支相刑 (三刑 / 互刑 / 自刑)."""
    out: list[Interaction] = []
    branch_to_positions: dict[str, list[str]] = {}
    for pos, b in branches:
        branch_to_positions.setdefault(b, []).append(pos)

    present_branches = set(branch_to_positions.keys())

    # 三刑: 寅巳申 / 丑戌未 — detect full (3 of 3) and partial (2 of 3)
    for san_set in XING_SAN_TYPES:
        present_in_set = present_branches & san_set
        if len(present_in_set) == 3:
            positions = tuple(branch_to_positions[b][0] for b in san_set)
            out.append(Interaction(
                kind="三刑",
                participants=positions,
                elements=tuple(san_set),
                note="三刑全见",
            ))
        elif len(present_in_set) == 2:
            present_two = tuple(present_in_set)
            positions = tuple(
                branch_to_positions[b][0] for b in present_two
            )
            missing = next(iter(san_set - present_in_set))
            out.append(Interaction(
                kind="三刑",
                participants=positions,
                elements=present_two,
                note=f"三刑缺{missing}（子刑寅上、丑刑戌上之类）",
            ))

    # 互刑: 子卯
    for hu_set in XING_HU_TYPES:
        if hu_set <= present_branches:
            positions = tuple(branch_to_positions[b][0] for b in hu_set)
            out.append(Interaction(
                kind="互刑",
                participants=positions,
                elements=tuple(hu_set),
                note="子卯相刑（无礼之刑）",
            ))

    # 自刑: 辰午酉亥 appearing 2+ times
    for b, positions in branch_to_positions.items():
        if b in ZI_XING_BRANCHES and len(positions) >= 2:
            out.append(Interaction(
                kind="自刑",
                participants=tuple(positions[:2]),
                elements=(b, b),
                note=f"{b}见{b}自刑",
            ))

    return out


def _detect_hai(
    branches: list[tuple[str, str]],
) -> list[Interaction]:
    """Detect 地支相害 between any 2 branches."""
    out: list[Interaction] = []
    for (pos_a, b_a), (pos_b, b_b) in combinations(branches, 2):
        pair = frozenset({b_a, b_b})
        if pair in HAI_TABLE and len(pair) == 2:
            out.append(Interaction(
                kind="相害",
                participants=(pos_a, pos_b),
                elements=(b_a, b_b),
            ))
    return out


def detect_interactions(chart: Chart) -> InteractionResult:
    """
    Detect all 刑冲合化 interactions in a chart.

    Args:
        chart: A Chart from Layer 1.

    Returns:
        InteractionResult with all detected interactions and citations.

    Note:
        This function detects the *structural* presence of interactions.
        Whether a 天干合 actually *transforms* (化) depends on the 化神
        having support in the 月令 — that judgment is deferred to a
        deeper analysis layer.
    """
    citations: list[RuleCitation] = []
    stems = _collect_stems(chart)
    branches = _collect_branches(chart)

    gan_he = _detect_gan_he(stems)
    san_he_full, san_he_half = _detect_san_he(branches)
    san_hui_full, san_hui_half = _detect_san_hui(branches)
    chong = _detect_chong(branches)
    xing = _detect_xing(branches)
    hai = _detect_hai(branches)

    # Build citations for each category that fired
    if gan_he:
        pairs = "、".join(
            f"{i.elements[0]}+{i.elements[1]}→{i.resulting_element}"
            for i in gan_he
        )
        citations.append(RuleCitation(
            rule_id=_R_HE_GAN.id,
            reason=f"天干五合检测到：{pairs}",
            conclusion=f"共 {len(gan_he)} 组天干合",
        ))

    if san_he_full:
        sets = "、".join(
            f"+".join(i.elements) + f"→{i.resulting_element}"
            for i in san_he_full
        )
        citations.append(RuleCitation(
            rule_id=_R_SAN_HE.id,
            reason=f"地支三合（全）：{sets}",
            conclusion=f"共 {len(san_he_full)} 组三合局",
        ))

    if san_he_half:
        sets = "、".join(
            f"+".join(i.elements) + f"→{i.resulting_element}（{i.note}）"
            for i in san_he_half
        )
        citations.append(RuleCitation(
            rule_id=_R_SAN_HE.id,
            reason=f"地支半三合：{sets}",
            conclusion=f"共 {len(san_he_half)} 组半三合",
        ))

    if san_hui_full:
        sets = "、".join(
            f"+".join(i.elements) + f"→{i.resulting_element}"
            for i in san_hui_full
        )
        citations.append(RuleCitation(
            rule_id=_R_SAN_HUI.id,
            reason=f"地支三会（全）：{sets}",
            conclusion=f"共 {len(san_hui_full)} 组三会方",
        ))

    if san_hui_half:
        sets = "、".join(
            f"+".join(i.elements) + f"→{i.resulting_element}（{i.note}）"
            for i in san_hui_half
        )
        citations.append(RuleCitation(
            rule_id=_R_SAN_HUI.id,
            reason=f"地支半三会：{sets}",
            conclusion=f"共 {len(san_hui_half)} 组半三会",
        ))

    if chong:
        pairs = "、".join(
            f"{i.elements[0]}+{i.elements[1]}"
            for i in chong
        )
        citations.append(RuleCitation(
            rule_id=_R_CHONG.id,
            reason=f"地支六冲：{pairs}",
            conclusion=f"共 {len(chong)} 组相冲",
        ))

    if xing:
        descs = "、".join(
            f"+".join(i.elements) + f"（{i.note}）"
            for i in xing
        )
        citations.append(RuleCitation(
            rule_id=_R_XING.id,
            reason=f"地支相刑：{descs}",
            conclusion=f"共 {len(xing)} 组相刑",
        ))

    if hai:
        pairs = "、".join(
            f"{i.elements[0]}+{i.elements[1]}"
            for i in hai
        )
        citations.append(RuleCitation(
            rule_id=_R_HAI.id,
            reason=f"地支相害：{pairs}",
            conclusion=f"共 {len(hai)} 组相害",
        ))

    if not (gan_he or san_he_full or san_he_half or san_hui_full
            or san_hui_half or chong or xing or hai):
        citations.append(RuleCitation(
            rule_id=_R_HE_GAN.id,
            reason="四柱天干地支之间未检测到任何合冲刑害关系",
            conclusion="无合冲刑害",
        ))

    return InteractionResult(
        gan_he=tuple(gan_he),
        san_he=tuple(san_he_full),
        ban_he=tuple(san_he_half),
        san_hui=tuple(san_hui_full),
        ban_hui=tuple(san_hui_half),
        chong=tuple(chong),
        xing=tuple(xing),
        hai=tuple(hai),
        citations=citations,
    )


__all__ = [
    "InteractionKind",
    "Interaction",
    "InteractionResult",
    "GAN_HE_TABLE",
    "SAN_HE_TABLE",
    "SAN_HUI_TABLE",
    "LIU_CHONG_TABLE",
    "XING_SAN_TYPES",
    "XING_HU_TYPES",
    "ZI_XING_BRANCHES",
    "HAI_TABLE",
    "detect_interactions",
]
