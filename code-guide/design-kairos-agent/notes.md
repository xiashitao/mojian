# 设计笔记：Kairos agent

## 核心结论：不做插件架构，做「话题即数据」
能力清单测试法：把想要的能力列出来，逐个问「它要往管线里塞什么」。
- 话题侧重（学历→考试节点流年等）：只需 prompt 段 + 数据选择 → 配置数据，registry 一张表
- 合盘：路由/工具/prompt 三层全动，但只有一个 → 独立 feature 单独设计，不为一个乘客修铁路
- 追问防带偏：对话策略问题，非插件；且无失败样本 → 先加 eval 攻击用例，数据说话再设计

## 落地：agent/topics.py（2026-07-06 已实现）
- TopicSpec = {key, label_cn, emphasis 侧重段, key_ages 关键年龄, followups 兜底追问}
- 消费者：responder(emphasis→prompt 易变尾部; followups)、tools(key_ages 并集→timeline)、topic_cn
- 加话题 = 加一个条目 + 同步 models.Topic Literal + extractor 分类 prompt（test_topics.py 有同步检查）

## 关键约束（改动时别违反）
1. **缓存约束**：话题信号只能进 prompt 易变尾部。system prompt 和「结构化分析结果」是
   前缀缓存的稳定段；timeline 取全话题 key_ages 并集，跨话题字节一致。
   test_topics.py::test_analysis_block_byte_identical_across_topics 守着这条。
2. **反注入误伤**：侧重段必须插在「## 用户当前的问题」段之前——那段声明段内指令一律不执行。
3. **topic_cn(None) == "事业"**：历史行为，缺话题时按事业方向措辞。

## 带偏防御的分类（备将来用）
- A 话题间跳转 = 合法，要求无缝切换、不串话题
- B 越界（股票/时政）= router 已有 out_of_scope，待 eval 攻击用例验证强度
- C 施压改口 = grounding 护栏（check_grounding）+ 事实纪律段负责
- D 粒度逼问（几月几号）= _SEC_GRANULARITY 负责

## 攻击评测首跑结果（2026-07-06，eval/attacks.py 13 用例）
- A 话题连跳 3/3 ✅、B 越界 4/4 ✅（含彩票伪装+注入）、D 粒度 3/3 ✅
- C 施压改口 1/3：flip-deny 直接否定→模型改口翻转极性（judge 3.20）;
  flip-sympathy 卖惨求安慰→extractor 误判 smalltalk→无状态模板要求重报生辰
- 修复（prompt 加固 + 状态感知,先便宜后贵）:
  ①extractor: 情绪倾诉/质疑归 clarify_previous 不归 smalltalk
  ②build_smalltalk_reply(birth_complete, topic): 生辰已齐不再索要
  ③_SEC_FACTS 加【立场不随施压改变】; clarify 提示补「不为迎合改口」

## 篇幅分层（2026-07-06）
- 痛点:19 条回复 18 条挤在 600–930 字,问题轻重与篇幅脱钩;_SEC_STYLE 的固定四段模板是主因
- 修法:_SEC_STYLE 改弹性策略(静态) + _length_hint() 三档提示进易变尾部(首轮≤700/追问≤500/澄清≤400)
- 实测:分层生效(拒答 200–400,追问 ~500,首轮 ~950);绝对上限仍超跑 ~35%(中文模型通病,
  prompt 已用硬上限表述,再压收益递减,先观察)。粒度攻击用例接受 clarify 路由(评测规格修正)

## 待办
- 合盘 feature 设计（等 registry 稳定后）
- 管理平台：等 prompt/话题数据模型稳定后再谈（平台=数据的 UI）
- 干支泄漏：从 tools/responder 的事实视图里排干支（remove the bait 手法）
