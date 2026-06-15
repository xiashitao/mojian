"""
bazibase.constants
==================

All static reference tables for Ba Zi computation. This is the single
source of truth for stems, branches, hidden stems, and ten-god mapping.

Every table here should be considered "fixed" — they encode the canonical
子平派 conventions. If you find yourself wanting to change a value here,
you are almost certainly changing schools, not fixing a bug.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 天干 (Heavenly Stems)
# ---------------------------------------------------------------------------

# Ordered list, index 0..9. Use STEMS[i] to get the Chinese character.
# Use STEM_INDEX["甲"] to get 0.
STEMS: tuple[str, ...] = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")

STEM_INDEX: dict[str, int] = {s: i for i, s in enumerate(STEMS)}

# Polarity: 0 = yang (阳), 1 = yin (阴). Stems alternate.
# 甲(0)=阳, 乙(1)=阴, 丙(2)=阳, ...
STEM_POLARITY: dict[str, int] = {s: i % 2 for i, s in enumerate(STEMS)}

# Five-element assignment for each stem.
# 甲乙木, 丙丁火, 戊己土, 庚辛金, 壬癸水
STEM_ELEMENT: dict[str, str] = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}

# Element cycle: 木→火→土→金→水→木 (production)
# Conquest: 木→土→水→火→金→木 (destruction)
ELEMENTS: tuple[str, ...] = ("木", "火", "土", "金", "水")
ELEMENT_PRODUCTION: dict[str, str] = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
ELEMENT_CONQUEST: dict[str, str] = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


# ---------------------------------------------------------------------------
# 地支 (Earthly Branches)
# ---------------------------------------------------------------------------

# Ordered by zodiac sequence (子 first), index 0..11.
BRANCHES: tuple[str, ...] = (
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
)

BRANCH_INDEX: dict[str, int] = {b: i for i, b in enumerate(BRANCHES)}

# Polarity: 子(0)=阳, 丑(1)=阴, ... — alternates like stems.
BRANCH_POLARITY: dict[str, int] = {b: i % 2 for i, b in enumerate(BRANCHES)}

# Five-element for each branch.
# 寅卯木, 巳午火, 申酉金, 亥子水, 辰戌丑未土
BRANCH_ELEMENT: dict[str, str] = {
    "子": "水", "丑": "土",
    "寅": "木", "卯": "木",
    "辰": "土", "巳": "火",
    "午": "火", "未": "土",
    "申": "金", "酉": "金",
    "戌": "土", "亥": "水",
}

# Zodiac animal for each branch — useful for display only.
BRANCH_ANIMAL: dict[str, str] = {
    "子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔", "辰": "龙", "巳": "蛇",
    "午": "马", "未": "羊", "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪",
}

# Hour-branch to clock-hour ranges (modern convention).
# 子时 spans 23:00–01:00 across midnight.
# Format: (start_hour, end_hour) with end exclusive, using 24-hour clock.
BRANCH_HOUR_RANGE: dict[str, tuple[int, int]] = {
    "子": (23, 1), "丑": (1, 3), "寅": (3, 5), "卯": (5, 7),
    "辰": (7, 9), "巳": (9, 11), "午": (11, 13), "未": (13, 15),
    "申": (15, 17), "酉": (17, 19), "戌": (19, 21), "亥": (21, 23),
}


# ---------------------------------------------------------------------------
# 地支藏干 (Hidden Stems in each Branch)
# ---------------------------------------------------------------------------
# Canonical 子平派 table. Each branch has a 本气 (primary),
# optionally 中气 (middle), optionally 余气 (residual).
#
# Some branches have only one hidden stem (子卯酉), some have two (午亥),
# some have three (丑寅辰巳未申戌).
#
# Source: 《子平真诠·论地支藏干》
BRANCH_HIDDEN_STEMS: dict[str, tuple[str, ...]] = {
    "子": ("癸",),
    "丑": ("己", "癸", "辛"),
    "寅": ("甲", "丙", "戊"),
    "卯": ("乙",),
    "辰": ("戊", "乙", "癸"),
    "巳": ("丙", "庚", "戊"),
    "午": ("丁", "己"),
    "未": ("己", "丁", "乙"),
    "申": ("庚", "壬", "戊"),
    "酉": ("辛",),
    "戌": ("戊", "辛", "丁"),
    "亥": ("壬", "甲"),
}


# ---------------------------------------------------------------------------
# 十神 (Ten Gods)
# ---------------------------------------------------------------------------
# Names — the order matters for some downstream logic.
TEN_GODS: tuple[str, ...] = (
    "比肩", "劫财",       # same element (同我)
    "食神", "伤官",       # I produce (我生)
    "偏财", "正财",       # I conquer (我克)
    "七杀", "正官",       # conquers me (克我)
    "偏印", "正印",       # produces me (生我)
)


def ten_god(day_master: str, other: str) -> str:
    """
    Compute the ten-god (十神) of `other` relative to `day_master`.

    Both arguments must be single stem characters from STEMS.

    Rules:
        - Same element, same polarity -> 比肩
        - Same element, opposite polarity -> 劫财
        - I produce, same polarity -> 食神
        - I produce, opposite polarity -> 伤官
        - I conquer, same polarity -> 偏财
        - I conquer, opposite polarity -> 正财
        - Conquers me, same polarity -> 七杀
        - Conquers me, opposite polarity -> 正官
        - Produces me, same polarity -> 偏印
        - Produces me, opposite polarity -> 正印

    Day master vs itself is 比肩 (same element, same polarity).
    """
    if day_master not in STEM_INDEX:
        raise ValueError(f"Invalid day master: {day_master!r}")
    if other not in STEM_INDEX:
        raise ValueError(f"Invalid stem: {other!r}")

    if day_master == other:
        return "比肩"

    dm_el = STEM_ELEMENT[day_master]
    oth_el = STEM_ELEMENT[other]
    dm_pol = STEM_POLARITY[day_master]
    oth_pol = STEM_POLARITY[other]
    same_polarity = dm_pol == oth_pol

    if dm_el == oth_el:
        return "比肩" if same_polarity else "劫财"
    if ELEMENT_PRODUCTION[dm_el] == oth_el:
        # 我生
        return "食神" if same_polarity else "伤官"
    if ELEMENT_CONQUEST[dm_el] == oth_el:
        # 我克
        return "偏财" if same_polarity else "正财"
    if ELEMENT_CONQUEST[oth_el] == dm_el:
        # 克我
        return "七杀" if same_polarity else "正官"
    if ELEMENT_PRODUCTION[oth_el] == dm_el:
        # 生我
        return "偏印" if same_polarity else "正印"

    # Should be unreachable.
    raise RuntimeError(f"Ten-god computation fell through for {day_master} vs {other}")


# ---------------------------------------------------------------------------
# 大运方向 (Luck pillar direction)
# ---------------------------------------------------------------------------
# Rule: 阳男阴女顺行, 阴男阳女逆行.
# Returns +1 for 顺 (forward) or -1 for 逆 (backward).
def luck_direction(year_stem_polarity: int, gender: str) -> int:
    """
    Determine luck pillar direction.

    Args:
        year_stem_polarity: 0 = yang, 1 = yin (use STEM_POLARITY[year_stem])
        gender: "male" or "female"

    Returns:
        +1 for 顺行 (forward), -1 for 逆行 (backward)
    """
    if gender not in ("male", "female"):
        raise ValueError(f"gender must be 'male' or 'female', got {gender!r}")
    is_yang = year_stem_polarity == 0
    is_male = gender == "male"
    # 阳男 / 阴女 -> 顺
    # 阴男 / 阳女 -> 逆
    if (is_yang and is_male) or (not is_yang and not is_male):
        return 1
    return -1


# ---------------------------------------------------------------------------
# 五鼠遁起时 (Hour stem derivation from day stem)
# ---------------------------------------------------------------------------
# Used for computing the hour pillar's stem when only the branch is known.
# The 子时 stem depends on the day stem:
#   甲己日 -> 甲子时
#   乙庚日 -> 丙子时
#   丙辛日 -> 戊子时
#   丁壬日 -> 庚子时
#   戊癸日 -> 壬子时
#
# Encoded as: day stem group -> stem offset at 子时.
WU_SHU_DUN: dict[str, int] = {
    # day stem -> index in STEMS that starts 子时
    "甲": 0, "己": 0,   # 甲子时
    "乙": 2, "庚": 2,   # 丙子时
    "丙": 4, "辛": 4,   # 戊子时
    "丁": 6, "壬": 6,   # 庚子时
    "戊": 8, "癸": 8,   # 壬子时
}
