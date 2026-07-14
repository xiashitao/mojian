"""干支泄漏净化 (_GanzhiStreamFilter) 与 check_grounding 的确定性护栏测试。

净化只剔『这盘实际出现过的干支』：精确、跨 chunk 安全、不误伤非命盘字词。
check_grounding 仍对原始输出打分——净化是给用户的护栏，不掩盖模型仍在泄漏。
"""
from web.backend.agent.responder import _GanzhiStreamFilter, check_grounding


def _run(chart_ganzhi, chunks):
    """把分块喂给过滤器，返回(净化后全文, 剔除计数)。"""
    f = _GanzhiStreamFilter(set(chart_ganzhi))
    out = [f.feed(c) for c in chunks]
    out.append(f.flush())
    return "".join(out), f.removed


class TestGanzhiStreamFilter:
    def test_drops_chart_ganzhi_within_one_chunk(self):
        text, n = _run({"壬寅"}, ["今年正行壬寅大运，压力偏大"])
        assert text == "今年正行大运，压力偏大"
        assert n == 1

    def test_drops_ganzhi_split_across_chunks(self):
        # 干支被切成两个 chunk：天干先到、地支后到，仍要整对剔掉。
        text, n = _run({"壬寅"}, ["今年正行壬", "寅大运"])
        assert text == "今年正行大运"
        assert n == 1

    def test_keeps_ganzhi_not_in_chart(self):
        # 丙午不在这盘里 → 不是后台标记的照抄，保留(避免误伤)。
        text, n = _run({"壬寅"}, ["丙午年出生的朋友"])
        assert text == "丙午年出生的朋友"
        assert n == 0

    def test_lone_stem_char_is_preserved(self):
        # 「自己」的己是天干字，但后面不接命盘地支 → 不成对，原样保留。
        text, n = _run({"己丑"}, ["这件事你自己午睡时想想"])
        assert text == "这件事你自己午睡时想想"
        assert n == 0

    def test_trailing_stem_flushed(self):
        # 末字恰是天干、且没有后续 → flush 时原样吐出，不吞字。
        text, n = _run({"壬寅"}, ["结论先讲到这，壬"])
        assert text == "结论先讲到这，壬"
        assert n == 0

    def test_multiple_and_year_prefix_reads_clean(self):
        # 真实泄漏形态：年份+干支冗余尾巴，剔掉后句子通顺。
        text, n = _run(
            {"壬子", "己酉"},
            ["到了2032年壬", "子食伤再起，2029年己酉也有帮助"],
        )
        assert text == "到了2032年食伤再起，2029年也有帮助"
        assert n == 2

    def test_empty_chart_set_is_identity(self):
        # 无命盘(模板兜底)时不持有、不改写，完全透传。
        text, n = _run(set(), ["随便什么文字壬寅甲子"])
        assert text == "随便什么文字壬寅甲子"
        assert n == 0

    def test_stream_reassembly_char_by_char(self):
        # 逐字喂(最刁钻的分块)也要正确重组并剔净。
        src = "起于甲寅止于壬寅，甲寅那步最关键"
        text, n = _run({"甲寅", "壬寅"}, list(src))
        assert "甲寅" not in text and "壬寅" not in text
        assert text == "起于止于，那步最关键"
        assert n == 3


class TestCheckGroundingStillFlagsRaw:
    def test_raw_ganzhi_leak_recorded(self):
        # 净化不改 check_grounding：它仍对原始输出打分,保留回归信号。
        violations = check_grounding("今年壬寅大运不顺", {})
        assert any("泄漏干支" in v for v in violations)

    def test_clean_text_has_no_violation(self):
        violations = check_grounding("今年这步大运不顺", {})
        assert not any("泄漏干支" in v for v in violations)
