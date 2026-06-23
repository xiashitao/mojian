"""Rule-based MVP extraction for chat intent, topic, and birth info."""
from __future__ import annotations

import re

from .models import BirthInfo, ExtractionResult, Intent, Topic


CITY_LONGITUDE: dict[str, float] = {
    "北京": 116.4,
    "上海": 121.5,
    "广州": 113.3,
    "深圳": 114.1,
    "杭州": 120.2,
    "南京": 118.8,
    "成都": 104.1,
    "重庆": 106.6,
    "武汉": 114.3,
    "西安": 108.9,
    "天津": 117.2,
    "苏州": 120.6,
    "长沙": 112.9,
    "郑州": 113.6,
    "青岛": 120.4,
    "厦门": 118.1,
    "福州": 119.3,
    "昆明": 102.8,
    "沈阳": 123.4,
    "哈尔滨": 126.6,
    "乌鲁木齐": 87.6,
    "香港": 114.2,
    "澳门": 113.5,
    "台北": 121.6,
}

_TOPIC_KEYWORDS: list[tuple[Topic, tuple[str, ...]]] = [
    ("career", ("事业", "职业", "工作", "创业", "行业", "合伙", "上班", "跳槽")),
    ("relationship", ("感情", "婚恋", "婚姻", "恋爱", "对象", "伴侣", "另一半")),
    ("wealth", ("财", "钱", "收入", "求财", "投资", "现金流", "赚钱")),
    ("personality", ("性格", "优势", "短板", "缺点", "特点", "人格")),
]


def extract_message(message: str) -> ExtractionResult:
    text = message.strip()
    topic = _detect_topic(text)
    intent = _detect_intent(text, topic)
    birth_info = _extract_birth_info(text)
    return ExtractionResult(
        intent=intent,
        topic=topic,
        birth_info=birth_info,
        raw_text=message,
    )


def merge_birth_info(current: BirthInfo, incoming: BirthInfo) -> BirthInfo:
    data = current.dict()
    for key, value in incoming.dict().items():
        if key in ("missing_fields", "confidence"):
            continue
        if value not in (None, "", []):
            data[key] = value
    confidence = max(current.confidence, incoming.confidence)
    data.pop("confidence", None)
    data.pop("missing_fields", None)
    merged = BirthInfo(**data, confidence=confidence)
    merged.missing_fields = merged.complete_missing_fields()
    return merged


def _detect_topic(text: str) -> Topic | None:
    for topic, keywords in _TOPIC_KEYWORDS:
        if any(k in text for k in keywords):
            return topic
    return None


def _detect_intent(text: str, topic: Topic | None) -> Intent:
    if any(k in text for k in ("为什么", "依据", "怎么说", "原因", "展开")):
        return "clarify_previous"
    if _has_birth_signal(text) and not topic:
        return "collect_birth_info"
    if topic:
        return topic
    if _has_birth_signal(text):
        return "collect_birth_info"
    return "unknown"


def _extract_birth_info(text: str) -> BirthInfo:
    birth_date = _extract_date(text)
    birth_time = _extract_time(text)
    birth_place, longitude = _extract_place(text)
    gender = _extract_gender(text)

    confidence = 0.0
    for value in (birth_date, birth_time, longitude, gender):
        if value is not None:
            confidence += 0.22
    if birth_place:
        confidence += 0.12

    info = BirthInfo(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        longitude=longitude,
        gender=gender,
        confidence=min(confidence, 1.0),
    )
    info.missing_fields = info.complete_missing_fields()
    return info


def _extract_date(text: str) -> str | None:
    patterns = (
        r"(?P<y>\d{4})[-/.](?P<m>\d{1,2})[-/.](?P<d>\d{1,2})",
        r"(?P<y>\d{4})年(?P<m>\d{1,2})月(?P<d>\d{1,2})[日号]?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            y = int(match.group("y"))
            m = int(match.group("m"))
            d = int(match.group("d"))
            return f"{y:04d}-{m:02d}-{d:02d}"
    return None


def _extract_time(text: str) -> str | None:
    match = re.search(r"(?P<h>\d{1,2})[:：](?P<m>\d{1,2})", text)
    if match:
        h = int(match.group("h"))
        m = int(match.group("m"))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    match = re.search(r"(?P<h>\d{1,2})点(?P<m>\d{1,2})?分?", text)
    if match:
        h = int(match.group("h"))
        m = 30 if "半" in text[match.start():match.end() + 2] else int(match.group("m") or 0)
        if "下午" in text or "晚上" in text or "傍晚" in text:
            if 1 <= h <= 11:
                h += 12
        if "中午" in text and h < 12:
            h = 12
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    rough = (
        ("凌晨", "03:00"),
        ("早上", "08:00"),
        ("上午", "09:00"),
        ("中午", "12:00"),
        ("下午", "15:00"),
        ("傍晚", "18:00"),
        ("晚上", "20:00"),
    )
    for keyword, value in rough:
        if keyword in text:
            return value
    return None


def _extract_place(text: str) -> tuple[str | None, float | None]:
    for city, longitude in CITY_LONGITUDE.items():
        if city in text:
            return city, longitude

    match = re.search(r"经度\s*(?P<lon>-?\d+(?:\.\d+)?)", text)
    if match:
        return None, float(match.group("lon"))
    return None, None


def _extract_gender(text: str) -> str | None:
    if re.search(r"(男|男性|男生|先生)", text):
        return "male"
    if re.search(r"(女|女性|女生|女士)", text):
        return "female"
    return None


def _has_birth_signal(text: str) -> bool:
    return bool(
        re.search(r"\d{4}年|\d{4}[-/.]\d{1,2}", text)
        or any(city in text for city in CITY_LONGITUDE)
        or any(k in text for k in ("出生", "生日", "男", "女"))
    )
