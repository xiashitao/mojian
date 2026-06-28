"""
bazibase.changsheng
====================

十二长生 (the twelve growth stages) — a 天干's state on a given 地支 along the
长生 → 沐浴 → … → 养 cycle. 阳干 run forward through the branches from their
长生 branch; 阴干 run backward. Classical and deterministic.

Used for 星运 (日主 on each pillar's branch) and 自坐 (each pillar's own 天干 on
its own branch).
"""
from __future__ import annotations

from .constants import BRANCHES, STEM_POLARITY

_STAGES = (
    "长生", "沐浴", "冠带", "临官", "帝旺", "衰",
    "病", "死", "墓", "绝", "胎", "养",
)

# 每个天干的「长生」起点地支。
_CHANG_SHENG_START = {
    "甲": "亥", "乙": "午", "丙": "寅", "丁": "酉", "戊": "寅",
    "己": "酉", "庚": "巳", "辛": "子", "壬": "申", "癸": "卯",
}


def twelve_stage(stem: str, branch: str) -> str:
    """The 十二长生 stage of `stem` sitting on `branch` (e.g. 戊 on 午 → 帝旺).

    Returns "" if either char is unknown. 阳干 count forward from 长生, 阴干 backward.
    """
    start = _CHANG_SHENG_START.get(stem)
    if start is None or branch not in BRANCHES:
        return ""
    si = BRANCHES.index(start)
    bi = BRANCHES.index(branch)
    yang = STEM_POLARITY.get(stem) == 0  # 0 = 阳, 1 = 阴
    offset = (bi - si) % 12 if yang else (si - bi) % 12
    return _STAGES[offset]


__all__ = ["twelve_stage"]
