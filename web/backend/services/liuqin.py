"""六亲（十神 → 家庭关系）映射。"""

# 男命六亲映射
_MALE_RELATIVES = {
    "比肩": "兄弟",
    "劫财": "姐妹",
    "食神": "祖父",
    "伤官": "祖母",
    "偏财": "父亲",
    "正财": "妻子",
    "七杀": "儿子",
    "正官": "女儿",
    "偏印": "继母",
    "正印": "母亲",
}

# 女命六亲映射
_FEMALE_RELATIVES = {
    "比肩": "姐妹",
    "劫财": "兄弟",
    "食神": "女儿",
    "伤官": "儿子",
    "偏财": "婆婆",
    "正财": "父亲",
    "七杀": "偏夫",
    "正官": "丈夫",
    "偏印": "继母",
    "正印": "母亲",
}


def ten_god_to_relative(ten_god: str, gender: str) -> str:
    """将十神转换为六亲名称。

    Args:
        ten_god: 十神名（如 '正印'）
        gender: 'male' | 'female'

    Returns:
        六亲名（如 '母亲'）
    """
    table = _MALE_RELATIVES if gender == "male" else _FEMALE_RELATIVES
    return table.get(ten_god, "")


def get_luck_relative(ten_god_text: str, gender: str) -> str:
    """大运/流年的十神标注转为六亲。

    ten_god_text 可能是 '七杀 · 比肩' 这种合并格式，只取第一个。
    """
    first_god = ten_god_text.split("·")[0].split("·")[0].strip()
    return ten_god_to_relative(first_god, gender)
