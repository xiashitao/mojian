"""
bazibase.rules
==============

Layer 2 rule engine — encodes 《子平真诠》 rules as a structured library
and applies them to a Chart to produce a Diagnosis.

Submodules:
    schema         — Rule / RuleCitation dataclasses and registry
    yong_shen      — 用神取法 algorithm
    ge_ju          — 格局判定 algorithm
    xiang_shen     — 相神 / 忌神 identification (v0.2.2)
    ge_ju_cheng_bai — 格局成败 assessment (v0.2.2)
    interactions   — 刑冲合化 detection (v0.2.3)
"""
from .schema import Rule, RuleCitation, register_rule, get_rule, all_rules
from .yong_shen import (
    YongShenResult,
    TransparentStem,
    determine_yong_shen,
)
from .ge_ju import GeJuResult, determine_ge_ju, GE_JU_NAME_BY_TEN_GOD
from .xiang_shen import (
    StemOccurrence,
    XiangShenResult,
    XIANG_JI_TABLE,
    identify_xiang_ji,
)
from .ge_ju_cheng_bai import (
    Verdict,
    ChengBaiResult,
    assess_cheng_bai,
)
from .interactions import (
    Interaction,
    InteractionResult,
    InteractionKind,
    GAN_HE_TABLE,
    SAN_HE_TABLE,
    SAN_HUI_TABLE,
    LIU_CHONG_TABLE,
    XING_SAN_TYPES,
    XING_HU_TYPES,
    ZI_XING_BRANCHES,
    HAI_TABLE,
    detect_interactions,
)

__all__ = [
    # schema
    "Rule",
    "RuleCitation",
    "register_rule",
    "get_rule",
    "all_rules",
    # yong_shen
    "YongShenResult",
    "TransparentStem",
    "determine_yong_shen",
    # ge_ju
    "GeJuResult",
    "determine_ge_ju",
    "GE_JU_NAME_BY_TEN_GOD",
    # xiang_shen (v0.2.2)
    "StemOccurrence",
    "XiangShenResult",
    "XIANG_JI_TABLE",
    "identify_xiang_ji",
    # ge_ju_cheng_bai (v0.2.2)
    "Verdict",
    "ChengBaiResult",
    "assess_cheng_bai",
    # interactions (v0.2.3)
    "Interaction",
    "InteractionResult",
    "InteractionKind",
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
