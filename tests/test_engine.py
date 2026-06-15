"""End-to-end tests for the Layer 2 engine (diagnose)."""
from datetime import datetime
import json
import pytest
from bazibase import cast_chart
from bazibase.engine import diagnose
from bazibase.diagnosis import Diagnosis
from bazibase.rules import get_rule


class TestDiagnoseReturnsDiagnosis:
    def test_returns_diagnosis_instance(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        assert isinstance(d, Diagnosis)

    def test_summary_contains_key_info(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        s = d.summary()
        assert "用神癸" in s
        assert "七杀" in s
        assert "七杀格" in s

    def test_summary_for_resolved_bi_jie(self):
        # 建禄格 case — v0.2.1 后用神会被自动找到
        c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
        d = diagnose(c)
        s = d.summary()
        assert "建禄格" in s
        assert "用神庚" in s
        assert "七杀" in s
        # v0.2.1 后此格局已定，不再出现"需进一步分析"
        assert "需进一步分析" not in s


class TestExplainOutput:
    def test_explain_contains_citations(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        text = d.explain()
        # Must cite the original 子平真诠 text
        assert "ZP-YONG-001" in text
        assert "月令本气透出天干者" in text
        assert "ZP-GE-MAP" in text

    def test_explain_contains_chart_summary(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        text = d.explain()
        assert "癸巳" in text
        assert "丁" in text  # day master

    def test_explain_for_bi_jie_shows_alternative(self):
        # v0.2.1: 建禄格的 explain 现在应显示另寻用神的推理链
        c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
        d = diagnose(c)
        text = d.explain()
        # Should mention 建禄 and the alternative 用神 (七杀)
        assert "建禄" in text
        assert "ZP-YONG-005" in text  # 比劫当令规则
        assert "ZP-YONG-007" in text  # 七杀另寻规则
        assert "庚" in text
        assert "七杀" in text
        assert "月令之外" in text or "另寻" in text


class TestSerialization:
    def test_to_dict_is_json_serializable(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        d_dict = d.to_dict()
        s = json.dumps(d_dict, ensure_ascii=False)
        d2 = json.loads(s)
        assert d2["day_master"] == "丁"
        assert d2["yong_shen"]["stem"] == "癸"

    def test_to_dict_has_expected_keys(self):
        c = cast_chart(datetime(2000, 6, 15, 12, 0), 116.4, "male")
        d = diagnose(c)
        d_dict = d.to_dict()
        assert set(d_dict.keys()) == {
            "chart_summary", "day_master",
            "yong_shen", "ge_ju",
            "xiang_shen", "cheng_bai",
            "interactions",
            "all_citations",
        }
        assert set(d_dict["yong_shen"].keys()) == {
            "stem", "ten_god", "source_rule_id", "is_bi_jie",
            "unresolved", "alternative_source",
            "transparent_stems", "citations",
        }
        assert set(d_dict["xiang_shen"].keys()) == {
            "xiang_shen", "ji_shen", "notes", "citations",
        }
        assert set(d_dict["cheng_bai"].keys()) == {
            "verdict", "source_rule_id", "rescue_gods",
            "unresolved", "citations",
        }

    def test_citations_include_original_text(self):
        c = cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male")
        d = diagnose(c)
        for cite_dict in d.to_dict()["all_citations"]:
            # Each citation must include the original 子平真诠 source text
            assert "source_text" in cite_dict
            assert cite_dict["source_text"]  # non-empty
            assert "chapter" in cite_dict


class TestRuleRegistry:
    def test_registered_rules_are_retrievable(self):
        from bazibase.rules import all_rules
        rules = all_rules()
        rule_ids = {r.id for r in rules}
        # Must include the 用神 rules and at least the mapping rule
        assert "ZP-YONG-000" in rule_ids
        assert "ZP-YONG-001" in rule_ids
        assert "ZP-YONG-005" in rule_ids
        assert "ZP-GE-MAP" in rule_ids
        assert "ZP-GE-JIANLU" in rule_ids

    def test_get_rule_by_id(self):
        r = get_rule("ZP-YONG-001")
        assert r.id == "ZP-YONG-001"
        assert r.chapter == "子平真诠·论用神"
        assert "月令本气透出天干" in r.source_text

    def test_unknown_rule_raises(self):
        with pytest.raises(KeyError):
            get_rule("DOES-NOT-EXIST")


class TestEngineDeterminism:
    def test_same_chart_same_diagnosis(self):
        c1 = cast_chart(datetime(2000, 6, 15, 12, 0), 116.4, "male")
        c2 = cast_chart(datetime(2000, 6, 15, 12, 0), 116.4, "male")
        d1 = diagnose(c1)
        d2 = diagnose(c2)
        assert d1.to_dict() == d2.to_dict()
