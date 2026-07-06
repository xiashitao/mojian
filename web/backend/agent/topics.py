"""话题注册表：topic-as-data。

一个话题 = 一份声明式配置（TopicSpec）。加话题/改侧重不再散改 responder /
tools / context——改这一张表。当前有三个消费者：

- responder 把 `emphasis` 注入 prompt 的易变尾部（本轮分析侧重）；
- tools 用 `key_ages` 的**全话题并集**算「关键年份·流年透视」；
- responder 的兜底追问从 `followups` 取。

【为什么 emphasis 不进 system prompt、key_ages 要取并集——缓存约束】
system prompt 与「结构化分析结果」大 JSON 构成 DeepSeek 前缀缓存的稳定段；
若按话题改动其中任何一段，用户一换话题整条缓存报废。因此话题信号一律走
prompt 末尾的易变段（emphasis），而 timeline 数据按并集生成、跨话题字节
一致——"选择"由侧重段引导模型注意力完成，不靠裁剪数据。

注意：新增话题 key 需同步 models.py 的 Topic Literal 与 extractor 的分类
prompt（tests/test_topics.py 有同步检查）。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TopicSpec:
    key: str
    label_cn: str
    # 本轮分析侧重段。写给模型的内部指引：这个话题看哪些宫位/十神/通路。
    # 约束与 system prompt 一致：不出现干支字样、粒度到流年为止。
    emphasis: str
    # 该话题关心的人生节点（周岁约），进 timeline 关键年份。取并集，见模块注释。
    key_ages: tuple[int, ...] = ()
    # LLM 不可用时的兜底追问池。
    followups: tuple[str, ...] = ()


DEFAULT_TOPIC = "personality"

TOPICS: dict[str, TopicSpec] = {
    "career": TopicSpec(
        key="career",
        label_cn="事业",
        emphasis=(
            "本轮看事业：以月柱（格局与事业宫）为轴，看官杀（约束与职位）、印（资历与庇护）、"
            "食伤（才干输出）、财（回报）之间的通路顺不顺，判断适合的方向、位置与节奏；"
            "人生阶段结合大运走向整条来谈。若问题涉及学历、考试、升学，落到求学时段那几年"
            "（关键年份·流年透视里的考试节点）逐年分析，说清哪一年顺、哪一年紧。"
        ),
        # 升学考节点（周岁约）：中考~15、高考~18、考研~22。
        key_ages=(15, 18, 22),
        followups=(
            "我适合什么行业？", "适合单干还是合伙？", "现在更适合创业还是上班？",
            "我适合什么样的岗位？", "事业上最该避开什么？", "怎么发挥我的长处？",
        ),
    ),
    "relationship": TopicSpec(
        key="relationship",
        label_cn="感情",
        emphasis=(
            "本轮看感情：以日支（配偶宫）为轴，看配偶星的强弱与位置、配偶宫与其他柱的刑冲合会"
            "（关系的稳定与扰动信号），结合大运走向指出感情上比较顺、或需要用心经营的时段；"
            "谈相处方式时结合命主的性格张力给具体建议，而不是泛泛的情感鸡汤。"
        ),
        followups=(
            "我适合怎样的伴侣？", "感情里最需要注意什么？", "我容易遇到什么样的人？",
            "怎么经营好长期关系？", "我的感情短板在哪？",
        ),
    ),
    "wealth": TopicSpec(
        key="wealth",
        label_cn="财务",
        emphasis=(
            "本轮看财务：围绕财星的强弱与通路——食伤生财接不接得上、比劫是否夺财、"
            "身能不能任财——判断求财方式（靠专业、靠经营、还是靠合作）与主要风险点；"
            "结合大运流年指出财上偏顺与需要收敛的年份。"
        ),
        followups=(
            "我适合靠什么赚钱？", "合作和投资要注意什么？", "我更适合正财还是偏财？",
            "怎么守住已有的财？", "我的财务风险点在哪？",
        ),
    ),
    "personality": TopicSpec(
        key="personality",
        label_cn="性格",
        emphasis=(
            "本轮看性格：从日主强弱与格局气质入手，结合五行偏枯看性格的张力与盲点，"
            "按宫位（年=根基早年，月=社会面与事业倾向，日支=亲密关系中的自己，时=晚年与传承）"
            "把性格放进人生结构里谈，并给出扬长避短的具体方式。"
        ),
        followups=(
            "我的优势在哪里？", "压力大的时候怎么调整？", "我的短板是什么？",
            "我适合怎样的成长方式？", "别人通常怎么看我？",
        ),
    ),
}


def topic_spec(topic: str | None) -> TopicSpec:
    return TOPICS.get(topic or DEFAULT_TOPIC, TOPICS[DEFAULT_TOPIC])


def topic_cn(topic: str | None) -> str:
    # None → "事业"：沿用原 context.topic_cn 的默认（缺话题时按事业方向措辞）。
    spec = TOPICS.get(topic or "career")
    return spec.label_cn if spec else "这个问题"


def all_key_ages() -> tuple[int, ...]:
    """全话题关键年龄的并集——timeline 必须话题无关（缓存约束，见模块注释）。"""
    ages: set[int] = set()
    for spec in TOPICS.values():
        ages.update(spec.key_ages)
    return tuple(sorted(ages))
