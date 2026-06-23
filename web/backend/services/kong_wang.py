"""空亡（旬空）计算。"""

# 六甲旬对应的空亡地支
_KONG_WANG = {
    "甲子": ("戌", "亥"),
    "甲戌": ("申", "酉"),
    "甲申": ("午", "未"),
    "甲午": ("辰", "巳"),
    "甲辰": ("寅", "卯"),
    "甲寅": ("子", "丑"),
}

# 六十甲子 → 所属旬首
_XUN_SHOU = {}
_stems = "甲乙丙丁戊己庚辛壬癸"
_branches = "子丑寅卯辰巳午未申酉戌亥"
for i in range(60):
    stem = _stems[i % 10]
    branch = _branches[i % 12]
    ganzhi = stem + branch
    # 每旬从甲开始
    xun_index = i % 10
    xun_stem = _stems[xun_index]
    # The 旬首 is the 甲 at position (i // 10) * 10
    xun_start = (i // 10) * 10
    xun_shou_stem = _stems[0]  # always 甲
    xun_shou_branch = _branches[xun_start % 12]
    _XUN_SHOU[ganzhi] = "甲" + xun_shou_branch


def get_kong_wang(stem_branch: str) -> tuple[str, str]:
    """根据干支（如 '丁丑'）返回空亡的两个地支。

    Returns:
        (空亡地支1, 空亡地支2)，如 ('申', '酉')
    """
    xun = _XUN_SHOU.get(stem_branch, "甲子")
    return _KONG_WANG.get(xun, ("戌", "亥"))


def is_void(branch: str, stem_branch: str) -> bool:
    """判断地支是否在 stem_branch 的空亡中。"""
    void1, void2 = get_kong_wang(stem_branch)
    return branch in (void1, void2)
