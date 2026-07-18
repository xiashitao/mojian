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

## hook 系统（2026-07-16 已实现,agent/hooks.py）
- 与「不做插件架构」结论的关系:hook ≠ 能力插件。原结论仍成立(能力走
  topics registry / 独立 feature);hook 是横切关注点的挂载机制,起点是
  成本统计/日志排查/调用链分析,应用户要求泛化成 Claude Code 式通用系统。
- 模型:事件 × matcher(正则) × priority × 返回值(continue/block/patch)
  × critical。能力表 EVENTS 是安全边界:每事件声明可否 block、可 patch 哪些键,
  白名单外的 patch 丢弃告警——「不可碰原则」做进 API 形状。
- 事件:user_message/post_route(可 block+patch)、pre_tool/post_tool(可 patch,
  post_tool 是干支泄漏 remove-the-bait 的挂载点)、post_response/on_step/
  on_span/run_end(观察类,只读)。**故意没有 pre_prompt**:缓存约束(话题信号
  只进易变尾部)还没有安全的暴露方式,需要时再设计 append-only 的尾部 API。
- 内置 hook(hooks_builtin.py,main.py lifespan 注册):CostMeter(记录时定价,
  span 补 cost 随 trace 落库 + run_costs 表)、StructuredLog(logs/agent.jsonl)。
- 查询:obs_cli show <run_id>(调用链树)/ costs(按天/模型)/ recent。
- 纪律:注册只在启动时;零 hook 注册 = 管线行为字节不变(test_hooks.py 60 用例守着,
  含端到端;e2e 测试密闭——强制 is_configured=False,不烧真 key)。

## agent 自主记忆（2026-07-16 已实现）
- 背景:用户想学 Claude Code 的记忆设计。澄清:CC 记忆是 markdown 文件不是
  jsonl(jsonl 是会话转录);其精华是「agent 自主写记忆」而非文件存储。
  结论:**存储不动(SQLite,多用户并发需要),记忆内容升级**。
- 实现:user_memory_notes 加 memory_text 列(_ensure_column 幂等迁移);
  reflect_on_reply 搭车加 memory 字段(零新增 LLM 调用)——模型自判「这轮有
  什么值得长期记住的用户信息」,铁律同画像(只记明确说出的,宁可空白绝不臆测);
  _GANZHI_RE 兜底净化(记忆会渲染回 prompt,带干支=把诱饵放回去);
  render_notes 渲染为「结论（用户情况：…）」,select_notes 预算按完整行算。
- 可读视图:obs_cli memory <memory_key> [--subject](生辰/画像/笔记全景)。
- 测试:test_memory_text.py 29 用例(迁移/存取/净化/渲染/planner 传递),
  planner 层用替身 stream_consultation_reply,密闭不烧 key。
- 防重复(2026-07-17):reflect 原本看不到已记过什么,用户每轮重复同一处境
  就每轮重复记录、挤占渲染预算。修法:known_memories(近5条 memory_text)
  喂进 reflect prompt,铁律加「已记住的不重复记,只记新增或明确变化」。
- 画像协同(2026-07-17):profile 更新器的笔记行补上 memory_text
  (「用户自述:…」)——用户自述处境是画像最强的原料,比结论信号强。
- 查询感知检索(2026-07-17):select_notes 升级为多信号打分——用户当前消息
  作 query,词法相似(字符 bigram Dice,免分词)×2.5 + 话题标签×0.3 +
  时间衰减×0.2;跨话题的关键旧信息(问健康时的家人病史)能被捞回。附带
  近重复折叠(sim≥0.85 只留最新,渲染侧第二道防重闸)。planner 候选池扩到
  30 条,进 prompt 仍精选 4 条/600 字——池大了精选才有意义,prompt 不变大。
  无 query 时保持旧行为。确定性、零依赖;权重标定被 test_retrieval.py 用
  真实中文句子钉住(整句 Dice 天花板 ~0.2-0.4,词法权重必须让单个关键词组
  命中就压过「话题+最新」底分)。缓存无损:笔记块本来就逐轮变化。
  升级阶梯的下一级:FTS5(注意中文要 trigram tokenizer)→ 向量,等笔记
  量级触发再说。
- 后续观察点:memory 字段实际产出质量(等真实流量);记忆时效性(「明年要孩子」
  会过期,可考虑渲染时带时间)。

## 稳定性:模型中断/断连/持久化失败(2026-07-17 已修)
- 分层防御(原有):网关有界重试+超时;每个 LLM 消费点有确定性降级
  (extractor→正则、responder→模板、reflect→规则池);planner 大 try 兜底;
  观测(hook/span)绝不反噬主链路。记忆/画像天生是「丢了不伤身」的旁路。
- 修掉的三个缝隙:
  ① reflect_on_reply 收紧 timeout=15/retries=0——回复送达后的锦上添花,
    宁可放弃不可拖住 done 事件(原默认 60s×3 次会让前端干等);
  ② 客户端断开(GeneratorExit):finish_agent_run + run_end hook 挪进
    finally,断开的轮次 status=disconnected、成本/trace 不丢(原来永远
    停在 partial、无成本记录);
  ③ 回复送达后的持久化失败:降级 status=partial + persist_error trace,
    不再给已拿到完整回复的用户发 error 事件;add_note 同款旁路保护。
- 测试密闭化:test_agent_conversations 的 agent_db fixture 强制
  is_configured=False——本地 .env 有真 key 时这些测试曾真调 API(慢、烧钱、
  限流随机挂)。原则:**pytest 是确定性回归网,真实 LLM 质量归 eval 管**。
  新增 test_stability.py 13 用例;全量 503 过、32s(原 316s)。

## 用户反馈 → trace 定位闭环(2026-07-17 已实现)
- 背景:前端赞/踩按钮原本只改本地 state(刷新即丢,后端无接口)。
- 链路:用户赞/踩(可带评论)→ POST /api/feedback {analysis_id, feedback,
  comment} → 存进助手消息 metadata_json(feedback/feedback_comment/
  feedback_at)→ 运营从 GET /api/admin/feedback 或 obs_cli feedback
  (差评优先)看到反馈 → 拿 analysis_id 开该轮 trace。
- 关键决策:以 **analysis_id** 为键而非 message_id——流式期间前端消息是
  临时本地 id,只有 analysis_id 稳定;归属校验走 run→conversation.user_id,
  不属于该用户按 404 处理(不泄露存在性)。存储复用 metadata_json,零新表。
- 前端:乐观更新、失败静默(反馈是增强,不打断用户);刷新后从
  metadata 恢复反馈状态。评论输入框 UI 暂未做(API 已支持 comment)。
- 测试:test_feedback.py 13 用例(落库/撤销/评论截断/不冲掉既有
  metadata/归属拒绝/定位列表)。

## 提示词段注册表(2026-07-17 已实现,agent/prompt_registry.py)
- 7/6 的痛点(「prompt 是代码不是数据」)的完整解:段 = 注册表条目
  {key, zone, order, when, render},compose 按 (zone, order) 三区拼装
  (SYSTEM 规则区 / ANALYSIS 分析区 / TAIL 易变尾部)。
- 三条铁律从注释约定升级为框架强制:①缓存约束——稳定区段只见 StableCtx
  (类型上没有 user_message 等每轮字段),且禁止 when;②反注入位置——
  question 段恒为尾部最后,import 时断言;③确定性——when/render 纯函数,
  无热加载。
- 迁移是**字节等价重构**:test_prompt_registry.py 冻结旧拼装逻辑为 legacy
  副本,28 个组合(7 场景×4 话题)逐字节比对——零行为差异,eval 分数直接
  继承,不用重跑。改段「内容」合法(跑 eval);改「结构」会被等价测试抓住。
- 后续:管理平台 = 段内容外置为数据(本文件即数据源);实验 = 命名变体集
  + eval AB。刻意不做:热加载、LLM 决定挂载、每段配置开关。

## 待办
- 合盘 feature 设计（等 registry 稳定后）
- 管理平台：等 prompt/话题数据模型稳定后再谈（平台=数据的 UI）
- 干支泄漏：从 tools/responder 的事实视图里排干支（remove the bait 手法;
  现在可作为 post_tool hook 实现）
- test_router.py::test_ask_topic_when_complete_but_no_topic 在 HEAD 上就红
  （unknown+齐生辰+无话题 现路由 consult 而非 ask_topic）——行为变了没同步测试,
  与 hook 改动无关,待定夺是修测试还是修路由
