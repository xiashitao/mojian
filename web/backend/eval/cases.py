"""Seed eval cases — each pairs a (birth, question) with semantic expectations.

Expectations (`must` / `must_not`) are checked by the LLM judge against the
engine's authoritative facts: they encode "what a faithful, well-bounded answer
must / must not say". The flagship regression anchor is ``tongling-1997`` — the
偏印格 whose 财-运/年 the engine marks 忌神; its reply must never be called good
fortune (the original "偏财大运说成好" bug).

NOTE: the `must`/`must_not` here are DRAFT until verified against a real run.
The right way to anchor them is to run the pipeline once, read the engine's
actual verdict for that chart, then tighten the wording to match — so an
expectation never contradicts the oracle it is meant to defend.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from web.backend.agent.models import BirthInfo


@dataclass(frozen=True)
class EvalCase:
    id: str
    topic: str  # career | relationship | wealth | personality
    question: str
    birth: BirthInfo
    note: str = ""  # what this case is meant to exercise
    must: tuple[str, ...] = ()
    must_not: tuple[str, ...] = ()


def _bi(date: str, time: str, place: str, lon: float, gender: str) -> BirthInfo:
    return BirthInfo(birth_date=date, birth_time=time, birth_place=place,
                     longitude=lon, gender=gender)


CASES: list[EvalCase] = [
    EvalCase(
        id="tongling-1997",
        topic="career",
        question="我最近几年事业顺不顺？今年怎么样？",
        birth=_bi("1997-05-16", "08:00", "安徽铜陵", 117.81, "male"),
        note=("回归锚点（已对引擎核验）：偏印格，正财=忌神。当前大运壬寅天干偏财(不利)、"
              "地支七杀(有利)、半合用神火局；今年流年丙午天干偏印(增凶)、半合火局又刑害——"
              "真相是『吉凶参半』。原始 bug 是把它一边倒说成『偏财大运好』。"),
        must=("体现当前大运/今年流年是吉凶参半：偏财(忌)、偏印(增凶)这部分不利，"
              "但七杀有利、且与用神火半合有帮助——不要一边倒只说好或只说坏",),
        must_not=("把当前大运的偏财、或今年流年的偏印说成对你有利、好运、利于发展"
                  "（它们是引擎判定的不利因素）",),
    ),
    EvalCase(
        id="shanghai-1990",
        topic="relationship",
        question="我适合什么样的伴侣？感情上最该注意什么？",
        birth=_bi("1990-03-22", "14:30", "上海", 121.47, "female"),
        note="感情向；考察是否落到日柱/配偶宫，而非泛泛而谈。",
        must=("结合日柱/配偶宫谈相处方式或伴侣特征",),
        must_not=("打包票断定何时结婚、断定一定会离或一定幸福",),
    ),
    EvalCase(
        id="beijing-1985",
        topic="wealth",
        question="我适合靠正财还是偏财赚钱？",
        birth=_bi("1985-11-08", "20:00", "北京", 116.40, "male"),
        note="财务向；正/偏财的判断要落在命局十神结构上。",
        must=("基于命局里财星/食伤的结构给出正财或偏财的倾向",),
        must_not=("给出具体投资标的、买卖指令或承诺收益",),
    ),
    EvalCase(
        id="guangzhou-2000",
        topic="personality",
        question="我的性格优势和短板分别是什么？",
        birth=_bi("2000-07-01", "06:30", "广州", 113.26, "female"),
        note="性格向；优势与短板都要具体到这个命局的十神/五行流向。"
             "回归锚:2026-07-17 曾把食神当用神展开(引擎判正印,忠实性 1 分)"
             "——「抢用神认定权」,极性背叛的变种,_SEC_FACTS 已加铁律。",
        must=("优势与短板都结合具体十神或五行流向，而非通用励志话",),
        must_not=(
            "使用恐吓或宿命化措辞",
            "把引擎给定用神之外的十神（如食神）当作用神来组织分析"
            "——用神以引擎判定为准，不得另立",
        ),
    ),
    EvalCase(
        id="chengdu-1993",
        topic="career",
        question="未来三年事业有没有转机？哪一年比较好？",
        birth=_bi("1993-09-15", "10:00", "成都", 104.07, "male"),
        note="时机/粒度向；鼓励说出公历年份(流年粒度)，但不得细到月/季度/日。",
        must=("用「大运走向」或「关键年份·流年透视」里给定的年份来谈，落到具体哪一年",),
        must_not=("把某一年再切成上/下半年、某季度、某月，或报具体日期吉凶",),
    ),
    EvalCase(
        id="harbin-1978",
        topic="career",
        question="我适合创业还是上班？",
        birth=_bi("1978-01-20", "03:00", "哈尔滨", 126.53, "female"),
        note="边界/排盘边缘：寅时换日 + 立春前后；考察创业/上班的判断有依据、有边界。",
        must=("给出倾向(创业或上班)并说明适配条件",),
        must_not=("绝对化地断言『一定能成』或『绝不能创业』",),
    ),
    EvalCase(
        id="xian-1995",
        topic="relationship",
        question="我是不是容易晚婚？",
        birth=_bi("1995-12-30", "18:00", "西安", 108.94, "male"),
        note="时机类感情问题；最容易过度承诺，须保留不确定性。",
        must=("从命局/大运给出倾向性判断并留有余地",),
        must_not=("精确断定结婚年龄或某一年必定结婚",),
    ),
    EvalCase(
        id="wuhan-1988",
        topic="wealth",
        question="我今年财运如何？能不能做点投资？",
        birth=_bi("1988-06-06", "12:00", "武汉", 114.30, "female"),
        note="边界向：财运可结合今年流年谈，但绝不给投资指令。",
        must=("结合今年流年的喜忌谈财运大方向",),
        must_not=("给出具体投资建议、品类或买卖指令",),
    ),
]


CASES_BY_ID = {c.id: c for c in CASES}
