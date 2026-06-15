# bazibase 架构文档

## 一句话定位

`bazibase` 是命理 agent 项目的**事实层 + 规则引擎层**——一个**确定性、可验证、零 LLM 调用**的八字排盘与诊断库。它回答"这个出生时间对应什么四柱、十神、强弱、大运"（Layer 1），并进一步给出"用神是谁、什么格局、成败如何、有哪些刑冲合化"（Layer 2）。**本库不做自然语言解读、不做多流派对比、不做吉凶预测**——那些属于解读层（Layer 3），是另一个项目。

规则冲突时本库**只产出 prompt 和解析 response，不在库内调用 LLM**——LLM 调用由调用方负责，以保持核心库的确定性与可测试性。

## 长期三层架构（整体项目蓝图）

```
┌─────────────────────────────────────────────────────────┐
│ Layer 3  解读层（未来，不在 bazibase 内）               ⏳ │
│   - 多流派对比（格局派 / 调候派 / 滴天髓派）             │
│   - LLM 把规则结果翻译成自然语言                         │
│   - 严格约束：引用规则编号、标注置信度、禁止巴纳姆话术   │
└─────────────────────────────────────────────────────────┘
                       ↑ 消费 bazibase 的 Diagnosis
┌─────────────────────────────────────────────────────────┐
│ Layer 2  规则引擎层（bazibase 已实现）                 ✅ │
│   - 《子平真诠》规则编码成结构化规则集（27 条）          │
│   - 用神取法 / 格局判定 / 相神忌神 / 格局成败 / 刑冲合化 │
│   - 规则冲突检测 + LLM 仲裁 prompt 生成（库内不调 LLM） │
└─────────────────────────────────────────────────────────┘
                       ↑ 消费 bazibase 的 Chart
┌─────────────────────────────────────────────────────────┐
│ Layer 1  事实层（bazibase 已实现）                     ✅ │
│   - 排盘 / 真太阳时 / 藏干 / 十神 / 大运 / 强弱          │
│   - 100% 确定性，可单测，可回归                          │
│   - 输入相同 ⇒ 输出永远相同                              │
└─────────────────────────────────────────────────────────┘
```

每一层只依赖下一层，不跨层。这样：
- Layer 1 错了，下面全废——所以它必须**朴素、可验证**。
- Layer 2 的规则错了，仍然能定位到具体规则编号去修。
- Layer 3 出问题（幻觉、忽悠），不会污染下面的事实层与规则层。

> **命名澄清**：早期版本的本文档曾把 bazibase 定位为"仅 Layer 1"，并把 LLM 仲裁称作"Layer 3"。这与代码现状不符。按原始设计意图，LLM 仲裁本就是 Layer 2"规则冲突仲裁"的组成部分；真正的 Layer 3 是解读层（多流派 + 自然语言生成），至今未实装。

## 当前实现状态（v0.4.0）

| 模块 | 状态 | 说明 |
|------|------|------|
| Layer 1 事实层 | ✅ 完整 | 7 个核心模块，回归锚点全部通过 |
| Layer 2 规则引擎 | ✅ 完整 | 5 个规则子模块，27 条规则注册在案 |
| Layer 2 LLM 仲裁 | ✅ 完整 | 5 种冲突类型，4 种已实装检测器（`GE_JU_ZHEN_JIA` 为空壳） |
| CLI 工具 | ✅ 完整 | `bazibase diagnose` 5 种输出模式 |
| Layer 3 解读层 | ⏳ 未开始 | 多流派对比、自然语言生成 |

**测试**：263 个测试全部通过。详见 `PROGRESS.md`。

## 模块清单

### Layer 1：事实层

| 文件 | 职责 | 关键数据结构 |
|------|------|--------------|
| `constants.py` | 所有静态查表数据（天干、地支、藏干、十神推导、五鼠遁、大运方向） | 各种 `dict` / `tuple` 常量 |
| `solar_time.py` | 真太阳时校正（经度修正 + 均时差） | `to_true_solar_time()` |
| `pillars.py` | 四柱排盘（年/月/日/时） | `Pillar`, `FourPillars`, `compute_four_pillars()` |
| `luck.py` | 大运起算（顺逆 + 起运岁数 + 干支序列） | `LuckPillar`, `LuckInfo`, `compute_luck()` |
| `ten_gods.py` | 十神标注（天干 + 地支藏干全部位置） | `TenGodLabels`, `label_ten_gods()` |
| `strength.py` | 日主旺衰评分（得令/得地/得势三路加权） | `StrengthAssessment`, `assess_strength()` |
| `chart.py` | Layer 1 顶层入口，把上述模块串起来 | `Chart`, `cast_chart()` |

### Layer 2：规则引擎层

| 文件 | 职责 | 关键数据结构 |
|------|------|--------------|
| `rules/schema.py` | 规则元数据 + 推理链 + 全局注册表 | `Rule`, `RuleCitation`, `register_rule()` |
| `rules/yong_shen.py` | 用神取法（月令取用 + 比劫另寻）| `YongShenResult`, `determine_yong_shen()` |
| `rules/ge_ju.py` | 格局判定（八大正格 + 建禄/月劫/羊刃）| `GeJuResult`, `determine_ge_ju()` |
| `rules/xiang_shen.py` | 相神 / 忌神识别 | `XiangShenResult`, `identify_xiang_ji()`, `XIANG_JI_TABLE` |
| `rules/ge_ju_cheng_bai.py` | 格局成败三态判定（成/救应/败）| `ChengBaiResult`, `assess_cheng_bai()` |
| `rules/interactions.py` | 刑冲合化检测（天干五合、三合、三会、六冲、三刑、相害）| `Interaction`, `InteractionResult`, `detect_interactions()` |
| `diagnosis.py` | 诊断结果聚合（含 `summary()` / `explain()` / `to_dict()`）| `Diagnosis` |
| `engine.py` | Layer 2 顶层入口，串联所有规则 | `diagnose(chart)` |
| `arbitration.py` | LLM 仲裁层（冲突检测 + prompt 构建 + response 解析）| `ArbitrationCase`, `prepare_arbitration()`, `parse_arbitration_response()` |

### 工具层

| 文件 | 职责 | 关键数据结构 |
|------|------|--------------|
| `cli.py` | 命令行入口（`diagnose` 子命令，5 种输出模式）| `cli_main()` |

## 关键设计决策（这些都是有争议的，文档化以便日后复审）

### Layer 1 决策

#### 1. 真太阳时的作用范围：只影响时柱

**决策**：真太阳时（TST）只用于推导**时支**（hour branch）。年月日柱一律用**输入的标准时间**（北京时间）。

**理由**：
- 时支的本质是"当地太阳所在的方位区间"，必须用本地真太阳时。
- 节气（立春、惊蛰...）是**绝对天文事件**，全球同一瞬间发生。出版历书上的节气时刻是北京时间表达，但事件本身与出生地经度无关。
- 大部分现代八字软件采用此约定；用户拿我们的输出对历书时不会困惑。

**实现**：
- `compute_four_pillars(clock_time, true_solar_time)` 同时接收两个时间。
- 年月日柱喂 `clock_time` 给 `lunar_python`，与节气瞬间比对。
- 时支从 `true_solar_time` 推导；时干通过**五鼠遁**从日干推（不用 `lunar_python` 的时柱）。

**已知限制**（v1）：
- 如果出生地经度极端偏西（如新疆 87°E），TST 可能比北京时间晚 2 小时以上；若把时钟 00:30 拉回到 22:30，日柱和时支会出现"日柱属于今日 / 时支属于昨日"的错位。这种边界 case 在 v1 不专门处理，文档标注即可。

#### 2. 子时边界：日界在 00:00

**决策**：子时（23:00–01:00）跨午夜时，**日柱以 00:00 为界**。即 23:30 出生的人，日柱仍属于当日；00:30 出生的人，日柱属于次日。

**理由**：与 `lunar_python` 默认行为一致，也是大多数现代八字软件的做法。

**未实现的另一派**：把 23:00 当作次日之始（"晚子时属于次日"）。这是部分传统派的做法，v1 不实现，但 `pillars.py` 的接口设计允许后续替换。

#### 3. 日主旺衰评分：可解释的加权启发式

**决策**：用透明加权打分，而非"凭感觉"判断。

**权重表**：

| 来源 | 本气 | 中气 | 余气 |
|------|------|------|------|
| 月令 | 4.0 | 2.0 | 1.0 |
| 通根（其他支藏干与日主同五行） | 2.0 | 1.0 | 0.5 |
| 天干透出（生我 / 同我） | — | — | 1.0 each |

**阈值**：总分 ≥ 5.0 → 身强，否则身弱。距阈值 ±1.0 以内标记为 `borderline`。

**为什么这样设计**：
- 真实的 弱强 判断需要看 用神选取、相神配合、刑冲合化——这些是 Layer 2 的事。
- v1 的目标是给一个**可解释的、用户能审计每一条贡献**的近似值。`StrengthAssessment.breakdown` 列出每一项加分原因，错了能找到原因。
- 这个评分**不能**作为最终判断，只能作为 Layer 2 的输入之一。

#### 4. 大运方向：阳男阴女顺、阴男阳女逆

**决策**：遵循《子平真诠·论行运》的标准规则。具体计算交给 `lunar_python`（其内部用 VSOP87 级别星历表算节气距离，精度到秒）。

**起运岁数规则**：从出生日到下一个（顺行）或上一个（逆行）节的天数，3 天 = 1 岁。余数 → 月、日。

**虚岁约定**：大运的 `start_age` / `end_age` 都是虚岁（出生即 1 岁），与中国传统一致。

#### 5. 地支藏干：采用子平派标准表

**决策**：用 `子平真诠·论地支藏干` 的标准表（不是坊间一些"新派"的变体）。

| 地支 | 本气 | 中气 | 余气 |
|------|------|------|------|
| 子 | 癸 | — | — |
| 丑 | 己 | 癸 | 辛 |
| 寅 | 甲 | 丙 | 戊 |
| 卯 | 乙 | — | — |
| 辰 | 戊 | 乙 | 癸 |
| 巳 | 丙 | 庚 | 戊 |
| 午 | 丁 | 己 | — |
| 未 | 己 | 丁 | 乙 |
| 申 | 庚 | 壬 | 戊 |
| 酉 | 辛 | — | — |
| 戌 | 戊 | 辛 | 丁 |
| 亥 | 壬 | 甲 | — |

#### 6. 强制使用 naive datetime

**决策**：所有 `datetime` 参数必须是 naive（无 `tzinfo`）。时区通过 `tz_offset_hours` 参数单独传。

**理由**：避免"naive vs aware"的隐性 bug。Python 的 `datetime` 会让两者在某些操作下抛错，在另一些操作下静默错误——这种不确定性在命理计算里不能容忍。

#### 7. Layer 1 全程不引入 LLM

**决策**：Layer 1 完全没有 LLM 调用，纯算法 + 查表。

**理由**：
- 确定性：同一输入永远同一输出，可写回归测试。
- 可验证：每一步都能对照公开历书。
- 可信：用户能审计到代码层面，不存在"AI 编出来的规则"。
- 一旦 Layer 1 引入 LLM，整个项目的可信度就崩了。

### Layer 2 决策

#### 8. 规则必须有"身份证"：`Rule` + `RuleCitation`

**决策**：每条规则在 `rules/schema.py` 里注册一个全局唯一 ID（如 `ZP-YONG-001`），并标注出处（《子平真诠·论用神》原文）。任何诊断结论都必须通过 `RuleCitation` 回溯到具体规则与原文。

**理由**：
- 命理最大问题是"大师拍脑袋"。每条结论引用具体规则编号，错了能定位到规则去修，而不是"算法玄学失败"。
- 规则原文锚点让用户可以自己去核对，建立信任。
- 后续如果换流派（比如换成调候派），只需新增一套 ID 前缀（如 `TH-YONG-***`），不必破坏既有规则。

#### 9. 用神取法：月令优先，比劫另寻走优先级链

**决策**：
- 月令本气不透则用中气、再不透用余气、三气俱不透暗用本气（ZP-YONG-001~004）。
- 月令为比劫（建禄/月劫/羊刃）时，按固定优先级另寻：**正官 → 七杀 → 财星 → 印星 → 食伤 → 无**（ZP-YONG-006~011）。
- 每个优先级内，天干透出优先于地支藏干。

**理由**：月令是用神的"首选来源"是《子平真诠》的核心主张；比劫当令时另寻的优先级则综合了《论建禄月劫》《论羊刃》两篇。优先级链保证算法确定性（同一八字永远取到同一个用神），而不是"看哪个顺眼"。

**已知简化**：羊刃格理应最喜七杀制刃，但当前算法在正官存在时仍优先取正官。后续版本可加格局特定的优先级覆盖。

#### 10. 格局成败：三态而非二态

**决策**：不用"成 / 败"二态，而是**成格 / 救应 / 败格 / 未定**四态（实务上称"三态判定"，"未定"是兜底）。
- 成格：用神已立 + 无忌神破坏
- 救应：忌神现 + 相神可制忌神（反败为成）
- 败格：忌神现 + 无相神可救
- 未定：用神未定或十神不在八大正格之列

**理由**："救应"是子平派的精华——忌神不一定坏事，有相神救应反而成格。强行二态会丢失这层信息。三态判定让"败中有救"的八字不会被一刀切为"坏命"。

#### 11. 刑冲合化只检测不判定"化与不化"

**决策**：`interactions.py` 只输出"结构上存在合 / 冲 / 刑 / 害"，**不判定合化是否成立**（如甲己合是否真化土，需要月令支持）。

**理由**：合化成立涉及月令、化神强弱、周边天干地支配合——这些判断有流派差异，且容易触发规则冲突。库内只做"结构检测"这一确定性的部分；"是否真化"留给 Layer 2 的仲裁层（`HE_HUA` 冲突类型）让 LLM 判定。

#### 12. 仲裁层不调 LLM，只产 prompt 和解析 response

**决策**：`arbitration.py` 提供 `prepare_arbitration()` 产出 prompt、`parse_arbitration_response()` 解析 LLM 回应，但**库内不发起任何 LLM 调用**。

**理由**：
- 保持核心库的确定性：同一输入永远同一 prompt，可写单测。
- 解耦运行时依赖：库本身不需要 API key、网络、重试逻辑；调用方可以在任意环境（CLI、Web、批处理）里自由集成 LLM。
- 测试友好：`parse_arbitration_response()` 可用 canned response 单测，无需 mock LLM。
- 一旦库内调 LLM，就失去了"输入相同 ⇒ 输出永远相同"的保证。

#### 13. 仲裁结果不回写 `Diagnosis`

**决策**：`ArbitrationResult` 是独立结构，**不会自动修改**原始 `Diagnosis` 的 `cheng_bai.verdict` 等字段。调用方需自行根据仲裁结果调整展示。

**理由**：`Diagnosis` 是"规则引擎的纯结构化输出"，`ArbitrationResult` 是"对规则冲突的二次裁决"。两者混在一起会让推理链无法审计——用户无法分辨"这条结论是规则给的"还是"这条结论是 LLM 给的"。保持分离，让置信度与来源始终可追溯。

#### 14. 强制置信度 + "无法判定"兜底

**决策**：`parse_arbitration_response()` 强制要求 LLM 回应包含 `confidence ∈ [0.0, 1.0]`；低于阈值（默认 0.6）等同于"无法判定"（`is_unresolved()` 返回 True）。Response schema 严格校验，格式错误抛 `ArbitrationParseError`。

**理由**：
- LLM 最危险的失败模式是"一本正经地胡说"。强制置信度让"不确定"显式化。
- "无法判定"是合法输出——比"编一个答案"更可信。
- 严格 schema 校验防止 LLM 输出格式漂移导致下游静默错误。

## 数据流

### Layer 1：一次 `cast_chart` 调用

```
birth_time (naive) + longitude + gender + tz_offset
    │
    ├─→ to_true_solar_time()  →  tst
    │
    ├─→ compute_four_pillars(clock_time=birth_time, true_solar_time=tst)
    │       │
    │       ├─→ lunar_python(clock_time) → 年/月/日干支
    │       ├─→ hour_branch_from_time(tst) → 时支
    │       └─→ hour_stem_from_day_stem(日干, 时支) via 五鼠遁 → 时干
    │
    ├─→ label_ten_gods(four_pillars) → 十神标注
    │       └─→ 对每个天干、每个藏干，调 ten_god(日主, other)
    │
    ├─→ assess_strength(four_pillars) → 旺衰评分 + 明细
    │
    └─→ compute_luck(birth_time, year_stem, gender)
            │
            └─→ lunar_python.getYun() → 起运岁数 + 大运序列
    │
    └─→ Chart(...) 汇总所有结果，提供 to_dict() / summary()
```

### Layer 2：一次 `diagnose` 调用

```
Chart
    │
    ├─→ determine_yong_shen(chart)
    │       │
    │       ├─→ 月令本/中/余气是否透干？→ ZP-YONG-001~004
    │       └─→ 月令为比劫？→ ZP-YONG-005 → 优先级链 ZP-YONG-006~011
    │       └─→ YongShenResult（含 source_rule_id + citations + alternative_source）
    │
    ├─→ determine_ge_ju(chart, yong_shen)
    │       │
    │       ├─→ 用神十神映射八大正格 / 比劫映射建禄月劫羊刃
    │       └─→ GeJuResult（含 name + source_rule_id + unresolved flag）
    │
    ├─→ identify_xiang_ji(chart, yong_shen)
    │       │
    │       ├─→ 查 XIANG_JI_TABLE 得相神/忌神十神集合
    │       └─→ 扫描所有天干 + 藏干 → XiangShenResult（xiang_list / ji_list / notes）
    │
    ├─→ assess_cheng_bai(yong_shen, xiang_ji)
    │       │
    │       └─→ 三态判定：成 / 救应 / 败 / 未定 → ChengBaiResult
    │
    ├─→ detect_interactions(four_pillars)
    │       │
    │       └─→ 天干五合 / 三合 / 三会 / 六冲 / 三刑 / 相害 → InteractionResult
    │
    └─→ Diagnosis(...) 聚合所有结果，提供 summary() / explain() / to_dict()
```

### LLM 仲裁：`prepare_arbitration` + 外部 LLM + `attach_response`

```
Diagnosis
    │
    ├─→ detect_arbitration_cases(diagnosis)
    │       │
    │       ├─→ RESCUE：救应成立但相神五行不克忌神五行
    │       ├─→ HE_CHONG：同支既在三合又在六冲
    │       ├─→ HE_HUA：天干五合结构成立，化神是否得月令
    │       ├─→ XING_CHONG：3 组以上刑冲共存
    │       └─→ GE_JU_ZHEN_JIA：空壳（待实装）
    │       └─→ List[ArbitrationCase]
    │
    ├─→ for each case: build_arbitration_prompt(case)
    │       └─→ ArbitrationPrompt（system_prompt + user_prompt + expected_schema）
    │
    ├─→ 调用方把 prompt 发给 LLM，拿回 raw_json
    │
    ├─→ parse_arbitration_response(case, raw_json)
    │       └─→ ArbitrationResponse（decision / reasoning / confidence / cited_rules）
    │       └─→ confidence < 0.6 自动算"无法判定"
    │
    └─→ attach_response(result, case_id, response) → ArbitrationResult
            └─→ unresolved_cases() 标识仍需人工介入的冲突
```

## 依赖与可替换性

**外部依赖**：
- `lunar_python` —— 提供农历转换、节气时刻、60甲子日柱、大运起算。这些是天文历法硬骨头，自己重写不划算。

**可替换性**：
- `lunar_python` 仅在 `pillars.py` 和 `luck.py` 两处被调用，且都封装在单一函数内。如果将来想换成 `sxtwl` 或自研历法库，只改这两个函数的实现即可。
- `constants.py` 是所有规则的单一来源。改流派（比如换成"新派命理"的藏干表），只动这一个文件。
- Layer 2 的规则全部走 `register_rule()` 注册，新增规则不改 engine 主流程。
- LLM 调用完全在库外，换模型（OpenAI / Anthropic / 本地模型）只需调用方改适配层。

## 测试策略

### Layer 1 测试

- **单元测试**（`test_constants/solar_time/pillars/luck/ten_gods/strength/chart.py`）：每个模块独立测试，覆盖正常 case + 边界 + 异常输入。
- **回归测试**（`test_known_charts.py`）：用公开记录的八字做锚点（如 1893-12-26 辰时 → 癸巳/甲子/丁酉/甲辰），任何改动都不能让这些 case 翻车。
- **边界测试**：立春跨年、节气跨月、子时跨日、跨经度时支变化。
- **自洽性测试**：连续两天的日柱在 60甲子里只差一步。
- **确定性测试**：同一输入多次调用，结果必须完全相等。

### Layer 2 测试

- **规则级单测**（`test_yong_shen/ge_ju/xiang_shen/ge_ju_cheng_bai/interactions.py`）：每条规则独立测试，含正反例。
- **路径覆盖测试**：用神取法的 4 条路径（本气透 / 中气透 / 余气透 / 暗用）+ 比劫另寻的 6 条路径，每条都要有用例。
- **回归锚点**：历史名人的八字（1893-12-26 等）作为 Layer 2 的稳定锚点。
- **explain() 输出测试**：教学模式输出必须包含规则原文、现状描述、结论三要素。

### Layer 3 仲裁测试

- **prompt 构建测试**：每种冲突类型的 prompt 都包含证据、规则原文、可选项。
- **response 解析测试**（`test_arbitration.py`）：
  - 正常 JSON 解析
  - markdown 代码块剥离
  - 字段缺失 / confidence 越界 / decision 不在 options 内 → 抛 `ArbitrationParseError`
  - 低置信度 → `is_unresolved()` 返回 True
- **库内不发起任何 LLM 调用**：所有测试用 canned response，保证测试确定性。

### CLI 测试

- 5 种输出模式（summary / explain / json / chart-only / arbitrate）各覆盖一例。
- 错误输入（非法日期、非法 gender）返回 exit code 2 + stderr。

测试是 bazibase 的"宪法"——任何破坏测试的 PR 都不能合并。
