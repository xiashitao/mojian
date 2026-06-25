"""
bazibase
========

Deterministic Ba Zi chart casting (Layer 1).

Public API:

    cast_chart(birth_time, longitude, gender, ...) -> Chart

See `chart.cast_chart` for full signature. See `Chart` for the
returned data structure.

Modules:
    constants    — static reference tables
    solar_time   — true solar time correction
    pillars      — four-pillar computation
    luck         — luck pillar (大运) computation
    ten_gods     — ten-god labeling
    strength     — day-master strength assessment
    chart        — Chart dataclass and cast_chart entry point
"""
from __future__ import annotations

from .chart import Chart, cast_chart
from .pillars import Pillar, FourPillars, compute_four_pillars
from .luck import LuckPillar, LuckInfo, compute_luck
from .ten_gods import TenGodLabels, label_ten_gods, StemTenGod, HiddenStemTenGod
from .strength import StrengthAssessment, assess_strength
from .solar_time import to_true_solar_time, equation_of_time_minutes
from .dst import is_china_dst, to_standard_time, CHINA_DST_PERIODS
from .timeline import (
    PeriodResolution, resolve_period, liunian_pillar, solar_ganzhi_year,
    STATUS_PRE_LUCK, STATUS_ACTIVE, STATUS_BEYOND_RANGE,
)
from .constants import (
    STEMS, BRANCHES, STEM_INDEX, BRANCH_INDEX,
    STEM_ELEMENT, BRANCH_ELEMENT, STEM_POLARITY, BRANCH_POLARITY,
    BRANCH_HIDDEN_STEMS, BRANCH_ANIMAL, BRANCH_HOUR_RANGE,
    TEN_GODS, ten_god,
)

# Layer 2 — rule engine (v0.2.0+)
from .diagnosis import Diagnosis
from .engine import diagnose
from .rules import (
    Rule, RuleCitation, register_rule, get_rule, all_rules,
    YongShenResult, TransparentStem, determine_yong_shen,
    GeJuResult, determine_ge_ju, GE_JU_NAME_BY_TEN_GOD,
    StemOccurrence, XiangShenResult, XIANG_JI_TABLE, identify_xiang_ji,
    ChengBaiResult, assess_cheng_bai,
    Interaction, InteractionResult, InteractionKind,
    GAN_HE_TABLE, SAN_HE_TABLE, SAN_HUI_TABLE,
    LIU_CHONG_TABLE, XING_SAN_TYPES, XING_HU_TYPES,
    ZI_XING_BRANCHES, HAI_TABLE,
    detect_interactions,
)

# Layer 3 — LLM arbitration (v0.3.0+)
from .arbitration import (
    ArbitrationCase, ArbitrationPrompt, ArbitrationResponse,
    ArbitrationResult, ArbitrationParseError,
    CaseCategory,
    DEFAULT_CONFIDENCE_THRESHOLD,
    detect_arbitration_cases,
    build_arbitration_prompt,
    parse_arbitration_response,
    prepare_arbitration,
    attach_response,
)

# CLI (v0.4.0+)
from .cli import main as cli_main

__version__ = "0.4.0"

__all__ = [
    # entry points (Layer 1)
    "cast_chart", "Chart",
    # pillars
    "Pillar", "FourPillars", "compute_four_pillars",
    # luck
    "LuckPillar", "LuckInfo", "compute_luck",
    # ten gods
    "TenGodLabels", "label_ten_gods", "StemTenGod", "HiddenStemTenGod",
    # strength
    "StrengthAssessment", "assess_strength",
    # solar time
    "to_true_solar_time", "equation_of_time_minutes",
    # daylight saving time
    "is_china_dst", "to_standard_time", "CHINA_DST_PERIODS",
    # timeline (大运/流年 resolution)
    "PeriodResolution", "resolve_period", "liunian_pillar", "solar_ganzhi_year",
    "STATUS_PRE_LUCK", "STATUS_ACTIVE", "STATUS_BEYOND_RANGE",
    # constants
    "STEMS", "BRANCHES", "STEM_INDEX", "BRANCH_INDEX",
    "STEM_ELEMENT", "BRANCH_ELEMENT", "STEM_POLARITY", "BRANCH_POLARITY",
    "BRANCH_HIDDEN_STEMS", "BRANCH_ANIMAL", "BRANCH_HOUR_RANGE",
    "TEN_GODS", "ten_god",
    # Layer 2 — rule engine
    "Diagnosis", "diagnose",
    "Rule", "RuleCitation", "register_rule", "get_rule", "all_rules",
    "YongShenResult", "TransparentStem", "determine_yong_shen",
    "GeJuResult", "determine_ge_ju", "GE_JU_NAME_BY_TEN_GOD",
    "StemOccurrence", "XiangShenResult", "XIANG_JI_TABLE", "identify_xiang_ji",
    "ChengBaiResult", "assess_cheng_bai",
    # interactions (v0.2.3)
    "Interaction", "InteractionResult", "InteractionKind",
    "GAN_HE_TABLE", "SAN_HE_TABLE", "SAN_HUI_TABLE",
    "LIU_CHONG_TABLE", "XING_SAN_TYPES", "XING_HU_TYPES",
    "ZI_XING_BRANCHES", "HAI_TABLE",
    "detect_interactions",
    # Layer 3 — LLM arbitration (v0.3.0)
    "ArbitrationCase", "ArbitrationPrompt", "ArbitrationResponse",
    "ArbitrationResult", "ArbitrationParseError",
    "CaseCategory",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "detect_arbitration_cases",
    "build_arbitration_prompt",
    "parse_arbitration_response",
    "prepare_arbitration",
    "attach_response",
    # CLI (v0.4.0)
    "cli_main",
]
