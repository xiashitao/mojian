"""Tests for the bazibase CLI (v0.4.0)."""
import json
import pytest

from bazibase.cli import main


# ---------------------------------------------------------------------------
# Default output mode
# ---------------------------------------------------------------------------

class TestDefaultOutput:
    """Default mode: one-line summary to stdout."""

    def test_outputs_summary_line(self, capsys):
        rc = main(["diagnose", "1893-12-26", "08:00",
                   "--lon", "112.9", "--gender", "male"])
        out = capsys.readouterr().out
        assert rc == 0
        # Summary contains the four pillars and key diagnosis terms
        assert "癸巳年" in out
        assert "甲子月" in out
        assert "丁酉日" in out
        assert "甲辰时" in out
        assert "日主丁" in out
        # Single line (no newlines in the middle)
        assert out.strip().count("\n") == 0

    def test_female_gender_accepted(self, capsys):
        rc = main(["diagnose", "2000-06-15", "12:00",
                   "--lon", "116.4", "--gender", "female"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "日主" in out

    def test_seconds_in_time_accepted(self, capsys):
        rc = main(["diagnose", "1893-12-26", "08:00:30",
                   "--lon", "112.9", "--gender", "male"])
        assert rc == 0


# ---------------------------------------------------------------------------
# --explain mode
# ---------------------------------------------------------------------------

class TestExplainOutput:
    """--explain: teaching mode with full reasoning chain."""

    def test_explain_has_sections(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--explain"])
        out = capsys.readouterr().out
        assert "=== 八字诊断 ===" in out
        assert "--- 用神 ---" in out
        assert "--- 格局 ---" in out
        assert "--- 相神 / 忌神 ---" in out
        assert "--- 格局成败 ---" in out

    def test_explain_has_rule_citations(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--explain"])
        out = capsys.readouterr().out
        # Should cite at least one rule with source text
        assert "ZP-" in out
        assert "原文:" in out
        assert "现状:" in out
        assert "结论:" in out

    def test_explain_and_json_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            main(["diagnose", "1893-12-26", "08:00",
                  "--lon", "112.9", "--gender", "male",
                  "--explain", "--json"])


# ---------------------------------------------------------------------------
# --json mode
# ---------------------------------------------------------------------------

class TestJsonOutput:
    """--json: structured JSON output."""

    def test_json_has_chart_and_diagnosis(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--json"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "chart" in data
        assert "diagnosis" in data

    def test_json_chart_has_expected_keys(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--json"])
        data = json.loads(capsys.readouterr().out)
        chart = data["chart"]
        for key in ("input", "true_solar_time", "day_master",
                     "four_pillars", "strength", "luck"):
            assert key in chart

    def test_json_diagnosis_has_expected_keys(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--json"])
        data = json.loads(capsys.readouterr().out)
        diag = data["diagnosis"]
        for key in ("chart_summary", "day_master", "yong_shen",
                     "ge_ju", "xiang_shen", "cheng_bai",
                     "interactions", "all_citations"):
            assert key in diag

    def test_json_is_valid_json(self, capsys):
        main(["diagnose", "2000-06-15", "12:00",
              "--lon", "116.4", "--gender", "male", "--json"])
        out = capsys.readouterr().out
        # Should not raise
        json.loads(out)


# ---------------------------------------------------------------------------
# --chart-only mode
# ---------------------------------------------------------------------------

class TestChartOnly:
    """--chart-only: limit to Layer 1."""

    def test_chart_only_summary(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--chart-only"])
        out = capsys.readouterr().out
        # Chart summary only — should NOT have diagnosis terms like 用神/格局
        assert "癸巳年" in out
        assert "日主丁" in out
        assert "用神" not in out

    def test_chart_only_json(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male",
              "--chart-only", "--json"])
        data = json.loads(capsys.readouterr().out)
        # Should be chart only, no diagnosis key
        assert "four_pillars" in data
        assert "diagnosis" not in data

    def test_chart_only_explain_falls_back_to_summary(self, capsys):
        # --explain requires diagnosis; --chart-only takes priority
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male",
              "--chart-only", "--explain"])
        out = capsys.readouterr().out
        # No diagnosis sections since chart-only wins
        assert "--- 用神 ---" not in out


# ---------------------------------------------------------------------------
# --arbitrate mode
# ---------------------------------------------------------------------------

class TestArbitrateOutput:
    """--arbitrate: LLM arbitration prompts as JSON array."""

    def test_mao_chart_has_cases(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--arbitrate"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert isinstance(data, list)
        assert len(data) >= 1
        # Each entry should have the prompt fields
        entry = data[0]
        for key in ("case_id", "category", "title", "system_prompt",
                     "user_prompt", "expected_schema", "options"):
            assert key in entry

    def test_clean_chart_empty_array(self, capsys):
        main(["diagnose", "2000-06-15", "12:00",
              "--lon", "116.4", "--gender", "male", "--arbitrate"])
        out = capsys.readouterr().out
        data = json.loads(out)
        assert data == []

    def test_arbitrate_has_system_and_user_prompt(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--arbitrate"])
        data = json.loads(capsys.readouterr().out)
        for entry in data:
            assert "JSON" in entry["system_prompt"]
            assert "confidence" in entry["system_prompt"].lower()
            assert entry["user_prompt"]

    def test_arbitrate_has_evidence(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--arbitrate"])
        data = json.loads(capsys.readouterr().out)
        for entry in data:
            assert isinstance(entry["evidence"], dict)
            assert len(entry["evidence"]) > 0

    def test_arbitrate_expected_schema_has_required_fields(self, capsys):
        main(["diagnose", "1893-12-26", "08:00",
              "--lon", "112.9", "--gender", "male", "--arbitrate"])
        data = json.loads(capsys.readouterr().out)
        for entry in data:
            schema = entry["expected_schema"]
            assert "decision" in schema["required"]
            assert "confidence" in schema["required"]


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Invalid inputs produce non-zero exit codes and stderr messages."""

    def test_invalid_date_format(self, capsys):
        rc = main(["diagnose", "not-a-date", "08:00",
                   "--lon", "116.4", "--gender", "male"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "错误" in err or "无法解析" in err

    def test_invalid_time_format(self, capsys):
        rc = main(["diagnose", "1893-12-26", "25:99",
                   "--lon", "116.4", "--gender", "male"])
        err = capsys.readouterr().err
        assert rc == 2

    def test_no_subcommand_exits(self):
        with pytest.raises(SystemExit):
            main([])

    def test_missing_required_args_exits(self):
        with pytest.raises(SystemExit):
            main(["diagnose", "1893-12-26", "08:00"])  # no --lon, --gender


# ---------------------------------------------------------------------------
# Optional flags
# ---------------------------------------------------------------------------

class TestOptionalFlags:
    """--tz, --no-solar, --luck are accepted and functional."""

    def test_tz_offset_accepted(self, capsys):
        rc = main(["diagnose", "2000-06-15", "12:00",
                   "--lon", "-74.0", "--gender", "male",
                   "--tz", "-5.0"])
        assert rc == 0
        assert "日主" in capsys.readouterr().out

    def test_no_solar_flag_accepted(self, capsys):
        rc = main(["diagnose", "2000-06-15", "12:00",
                   "--lon", "116.4", "--gender", "male", "--no-solar"])
        assert rc == 0

    def test_luck_count_accepted(self, capsys):
        rc = main(["diagnose", "2000-06-15", "12:00",
                   "--lon", "116.4", "--gender", "male",
                   "--luck", "4", "--json"])
        data = json.loads(capsys.readouterr().out)
        assert len(data["chart"]["luck"]["pillars"]) == 4


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Same input → same output."""

    def test_same_input_same_output(self, capsys):
        args = ["diagnose", "1893-12-26", "08:00",
                "--lon", "112.9", "--gender", "male"]
        main(args)
        out1 = capsys.readouterr().out
        main(args)
        out2 = capsys.readouterr().out
        assert out1 == out2
