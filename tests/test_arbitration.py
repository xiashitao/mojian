"""Tests for the LLM arbitration layer (v0.3.0)."""
import json
import pytest
from datetime import datetime
from bazibase import (
    cast_chart, diagnose,
    ArbitrationCase, ArbitrationPrompt, ArbitrationResponse, ArbitrationResult,
    ArbitrationParseError,
    DEFAULT_CONFIDENCE_THRESHOLD,
    detect_arbitration_cases, build_arbitration_prompt,
    parse_arbitration_response, prepare_arbitration, attach_response,
)


def _diagnose(dt, lon=116.4, gender="male"):
    return diagnose(cast_chart(dt, lon, gender))


# ---------------------------------------------------------------------------
# Case detection tests
# ---------------------------------------------------------------------------

class TestDetectRescueCases:
    """RESCUE cases: 救应 where 相神 may not control 忌神 in 五行."""

    def test_mao_1893_has_rescue_cases(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        rescue = [c for c in cases if c.category == "RESCUE"]
        # Mao's chart: 甲(木,正印) as rescue, 庚/辛(金) as 忌神
        # 木不克金 → RESCUE case should fire
        assert len(rescue) >= 1
        titles = " ".join(c.title for c in rescue)
        assert "甲" in titles  # rescue god 甲
        assert "庚" in titles or "辛" in titles  # 忌神

    def test_rescue_case_has_correct_evidence(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        rescue = [c for c in cases if c.category == "RESCUE"][0]
        assert "yong_shen" in rescue.evidence
        assert "ji_shen" in rescue.evidence
        assert "rescue_god" in rescue.evidence
        assert "rescue_element" in rescue.evidence
        # 1893 chart: 忌(金)克救(木) → ji_destroys_rescue is True
        assert rescue.evidence["ji_destroys_rescue"] is True
        assert rescue.evidence["rescue_feeds_ji"] is False

    def test_cheng_ge_chart_has_no_rescue_cases(self):
        # 2000-06-15 is 成格 (no 忌神) → no RESCUE cases
        d = _diagnose(datetime(2000, 6, 15, 12, 0))
        cases = detect_arbitration_cases(d)
        rescue = [c for c in cases if c.category == "RESCUE"]
        assert len(rescue) == 0


class TestDetectHeChongCases:
    """HE_CHONG cases: branch in both 三合 and 六冲."""

    def test_1942_chart_has_he_chong(self):
        d = _diagnose(datetime(1942, 1, 8, 6, 0))
        cases = detect_arbitration_cases(d)
        he_chong = [c for c in cases if c.category == "HE_CHONG"]
        assert len(he_chong) >= 1
        title = he_chong[0].title
        # Should mention 冲 and 三合
        assert "冲" in title
        assert "三合" in title


class TestDetectHeHuaCases:
    """HE_HUA cases: 天干五合 detected, 化神 strength unknown."""

    def test_1970_chart_has_he_hua(self):
        d = _diagnose(datetime(1970, 3, 15, 10, 0))
        cases = detect_arbitration_cases(d)
        he_hua = [c for c in cases if c.category == "HE_HUA"]
        assert len(he_hua) >= 1
        assert any("甲" in c.title and "己" in c.title for c in he_hua)


class TestDetectXingChongCases:
    """XING_CHONG cases: 3+ 刑/冲 interactions."""

    def test_1981_chart_has_xing_chong(self):
        d = _diagnose(datetime(1981, 12, 18, 13, 0))
        cases = detect_arbitration_cases(d)
        xc = [c for c in cases if c.category == "XING_CHONG"]
        assert len(xc) >= 1
        assert "动荡" in xc[0].description


class TestNoFalsePositives:
    """Charts with no conflicts produce zero cases."""

    def test_clean_chart_has_zero_cases(self):
        d = _diagnose(datetime(2000, 6, 15, 12, 0))
        cases = detect_arbitration_cases(d)
        assert len(cases) == 0


# ---------------------------------------------------------------------------
# Prompt building tests
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    """build_arbitration_prompt produces structured prompts."""

    def test_prompt_has_system_and_user(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        assert isinstance(prompt, ArbitrationPrompt)
        assert prompt.system_prompt
        assert prompt.user_prompt
        assert prompt.case is cases[0]

    def test_system_prompt_has_json_instruction(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        assert "JSON" in prompt.system_prompt
        assert "confidence" in prompt.system_prompt.lower()

    def test_user_prompt_contains_evidence(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        # Should contain case title and evidence keys
        assert cases[0].title in prompt.user_prompt
        assert "ji_shen" in prompt.user_prompt
        assert "rescue_god" in prompt.user_prompt

    def test_user_prompt_contains_options(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        for opt in cases[0].options:
            assert opt in prompt.user_prompt

    def test_expected_schema_has_required_fields(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        schema = prompt.expected_schema
        assert schema["type"] == "object"
        assert "decision" in schema["required"]
        assert "reasoning" in schema["required"]
        assert "confidence" in schema["required"]
        assert "cited_rules" in schema["required"]

    def test_expected_schema_enum_matches_options(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        cases = detect_arbitration_cases(d)
        prompt = build_arbitration_prompt(cases[0], d)
        schema_enum = set(prompt.expected_schema["properties"]["decision"]["enum"])
        options_set = set(cases[0].options)
        assert schema_enum == options_set


# ---------------------------------------------------------------------------
# Response parsing tests
# ---------------------------------------------------------------------------

class TestParseResponse:
    """parse_arbitration_response validates LLM JSON output."""

    def _make_case(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        return detect_arbitration_cases(d)[0]

    def test_valid_response_parsed(self):
        case = self._make_case()
        raw = json.dumps({
            "decision": case.options[0],
            "reasoning": "五行木不克金，但位置上印可化杀。",
            "confidence": 0.7,
            "cited_rules": ["ZP-JIUYING-001"],
        }, ensure_ascii=False)
        resp = parse_arbitration_response(case, raw)
        assert resp.case_id == case.case_id
        assert resp.decision == case.options[0]
        assert resp.confidence == 0.7
        assert "ZP-JIUYING-001" in resp.cited_rules

    def test_markdown_fenced_json_parsed(self):
        case = self._make_case()
        raw = f"""```json
{json.dumps({
    "decision": case.options[0],
    "reasoning": "test",
    "confidence": 0.5,
    "cited_rules": [],
}, ensure_ascii=False)}
```"""
        resp = parse_arbitration_response(case, raw)
        assert resp.decision == case.options[0]

    def test_invalid_json_raises(self):
        case = self._make_case()
        with pytest.raises(ArbitrationParseError):
            parse_arbitration_response(case, "not json at all")

    def test_missing_key_raises(self):
        case = self._make_case()
        raw = json.dumps({"decision": case.options[0]})  # missing reasoning, confidence
        with pytest.raises(ArbitrationParseError):
            parse_arbitration_response(case, raw)

    def test_invalid_decision_raises(self):
        case = self._make_case()
        raw = json.dumps({
            "decision": "random option not in list",
            "reasoning": "test",
            "confidence": 0.5,
            "cited_rules": [],
        })
        with pytest.raises(ArbitrationParseError):
            parse_arbitration_response(case, raw)

    def test_confidence_out_of_range_raises(self):
        case = self._make_case()
        raw = json.dumps({
            "decision": case.options[0],
            "reasoning": "test",
            "confidence": 1.5,  # > 1.0
            "cited_rules": [],
        })
        with pytest.raises(ArbitrationParseError):
            parse_arbitration_response(case, raw)

    def test_negative_confidence_raises(self):
        case = self._make_case()
        raw = json.dumps({
            "decision": case.options[0],
            "reasoning": "test",
            "confidence": -0.1,
            "cited_rules": [],
        })
        with pytest.raises(ArbitrationParseError):
            parse_arbitration_response(case, raw)

    def test_unresolvable_decision_accepted(self):
        # "无法判定" is always valid even if not in options
        case = self._make_case()
        raw = json.dumps({
            "decision": "无法判定",
            "reasoning": "证据不足",
            "confidence": 0.3,
            "cited_rules": [],
        }, ensure_ascii=False)
        resp = parse_arbitration_response(case, raw)
        assert resp.decision == "无法判定"
        assert resp.is_unresolved() is True

    def test_fuzzy_match_shortened_option(self):
        # LLMs often shorten options by dropping the parenthetical
        # explanation. The parser should match the core keyword.
        case = self._make_case()
        # Pick an option with a parenthetical, use its core only
        full_opt = case.options[0]
        core = full_opt.split("（")[0].split("(")[0].strip()
        raw = json.dumps({
            "decision": core,
            "reasoning": "test",
            "confidence": 0.8,
            "cited_rules": [],
        }, ensure_ascii=False)
        resp = parse_arbitration_response(case, raw)
        # Should be normalized to the full option
        assert resp.decision == full_opt


# ---------------------------------------------------------------------------
# ArbitrationResponse behavior
# ---------------------------------------------------------------------------

class TestArbitrationResponse:
    """ArbitrationResponse.is_unresolved threshold logic."""

    def test_high_confidence_not_unresolved(self):
        case = detect_arbitration_cases(
            _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        )[0]
        resp = ArbitrationResponse(
            case_id=case.case_id,
            decision=case.options[0],
            reasoning="ok",
            confidence=0.9,
        )
        assert resp.is_unresolved() is False

    def test_low_confidence_is_unresolved(self):
        case = detect_arbitration_cases(
            _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        )[0]
        resp = ArbitrationResponse(
            case_id=case.case_id,
            decision=case.options[0],
            reasoning="not sure",
            confidence=0.3,
        )
        assert resp.is_unresolved() is True

    def test_custom_threshold(self):
        case = detect_arbitration_cases(
            _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        )[0]
        resp = ArbitrationResponse(
            case_id=case.case_id,
            decision=case.options[0],
            reasoning="ok",
            confidence=0.7,
        )
        # 0.7 > default (0.6) → not unresolved at default
        assert resp.is_unresolved() is False
        # 0.7 < 0.8 → unresolved at 0.8 threshold
        assert resp.is_unresolved(threshold=0.8) is True


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestPrepareArbitration:
    """prepare_arbitration: full detect + build pipeline."""

    def test_returns_arbitration_result(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        result = prepare_arbitration(d)
        assert isinstance(result, ArbitrationResult)
        assert len(result.cases) > 0
        assert len(result.prompts) == len(result.cases)
        assert result.responses == {}  # empty until attach

    def test_has_cases_true_when_cases_exist(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        result = prepare_arbitration(d)
        assert result.has_cases() is True

    def test_has_cases_false_when_no_cases(self):
        d = _diagnose(datetime(2000, 6, 15, 12, 0))
        result = prepare_arbitration(d)
        assert result.has_cases() is False
        assert len(result.cases) == 0

    def test_clean_chart_empty_result(self):
        d = _diagnose(datetime(2000, 6, 15, 12, 0))
        result = prepare_arbitration(d)
        assert len(result.cases) == 0
        assert len(result.prompts) == 0


class TestAttachResponse:
    """attach_response: add a response to a result."""

    def test_attach_returns_new_instance(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        result = prepare_arbitration(d)
        case = result.cases[0]
        resp = ArbitrationResponse(
            case_id=case.case_id,
            decision=case.options[0],
            reasoning="test",
            confidence=0.8,
        )
        new_result = attach_response(result, case.case_id, resp)
        # Original unchanged
        assert len(result.responses) == 0
        # New has the response
        assert case.case_id in new_result.responses

    def test_unresolved_cases_includes_unanswered(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        result = prepare_arbitration(d)
        # No responses attached → all cases are unresolved
        unresolved = result.unresolved_cases()
        assert len(unresolved) == len(result.cases)

    def test_unresolved_cases_excludes_answered_high_conf(self):
        d = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        result = prepare_arbitration(d)
        # Attach high-confidence response to first case
        case = result.cases[0]
        resp = ArbitrationResponse(
            case_id=case.case_id,
            decision=case.options[0],
            reasoning="confident",
            confidence=0.9,
        )
        result = attach_response(result, case.case_id, resp)
        unresolved = result.unresolved_cases()
        assert case not in unresolved
        # But other cases (if any) should still be unresolved
        if len(result.cases) > 1:
            assert len(unresolved) == len(result.cases) - 1


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Same chart → same cases."""

    def test_same_chart_same_cases(self):
        d1 = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        d2 = _diagnose(datetime(1893, 12, 26, 8, 0), 112.9)
        r1 = prepare_arbitration(d1)
        r2 = prepare_arbitration(d2)
        assert r1.cases == r2.cases
