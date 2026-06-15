# bazibase 进度文档

## 当前状态：v0.4.0 已完成

第一层（事实层）、第二层的用神取法/格局判定/相神忌神/格局成败/刑冲合化、第三层的 LLM 仲裁层、第四层的 CLI 工具全部实现并通过测试。**263 个测试全部通过**。

```
$ pytest -v
============================= 263 passed in 0.38s =============================
```

版本号已升至 `0.4.0`。

## 已完成的功能清单

### 1. 常量表（`constants.py`）
- [x] 十天干 / 十二地支（含阴阳、五行、序号、生肖）
- [x] 地支藏干表（子平派标准）
- [x] 十神推导（`ten_god()` 函数，覆盖所有 100 种干对组合）
- [x] 五鼠遁起时表（用于从日干推时干）
- [x] 大运方向规则（阳男阴女顺 / 阴男阳女逆）
- [x] 五行生克关系

### 2. 真太阳时校正（`solar_time.py`）
- [x] 经度修正（每度差 4 分钟）
- [x] 均时差（Spencer 公式近似，精度 ±0.5 分钟）
- [x] 任意时区支持（通过 `tz_offset_hours` 参数）
- [x] 强制 naive datetime，避免时区隐性 bug

### 3. 四柱排盘（`pillars.py`）
- [x] 年柱（按立春界）
- [x] 月柱（按节界，非中气）
- [x] 日柱（60甲子循环）
- [x] 时柱（时支从真太阳时推，时干用五鼠遁从日干推）
- [x] 自动填入地支藏干

### 4. 大运（`luck.py`）
- [x] 顺逆方向判定
- [x] 起运岁数（精确到年/月/日）
- [x] 大运干支序列（默认输出 8 步 = 80 年）
- [x] 起运阳历日期

### 5. 十神标注（`ten_gods.py`）
- [x] 四柱天干十神
- [x] 所有藏干十神（标注本气/中气/余气）
- [x] 日干标注为"日主"而非"比肩"

### 6. 日主旺衰（`strength.py`）
- [x] 得令评分（月令本气/中气/余气）
- [x] 得地评分（其他支藏干与日主同五行的通根）
- [x] 得势评分（其他天干生我/同我）
- [x] 明细输出（每条加分原因可审计）
- [x] 边界 flag（接近阈值时提醒用户）

### 7. Chart 数据结构（`chart.py`）
- [x] 顶层入口 `cast_chart()`
- [x] 不可变 `Chart` dataclass
- [x] `to_dict()` 序列化为 JSON 友好结构
- [x] `summary()` 一行摘要
- [x] 完整的输入溯源（保存原始出生时间、经度、性别、时区）

### 8. 规则引擎（`rules/` + `engine.py` + `diagnosis.py`）—— Layer 2 v0.2.0

- [x] **规则模式**（`rules/schema.py`）：`Rule` 引用记录、`RuleCitation` 推理链、全局规则注册表
- [x] **用神取法**（`rules/yong_shen.py`）：实现《子平真诠·论用神》5 条规则
    - ZP-YONG-000 用神专凭月令（前置规则）
    - ZP-YONG-001 月令本气透干用本气
    - ZP-YONG-002 本气不透、中气透干用中气
    - ZP-YONG-003 本中气均不透、余气透干用余气
    - ZP-YONG-004 三气俱不透、暗用月令本气
    - ZP-YONG-005 月令为比劫时弃月令不用（建禄月劫羊刃入口）
- [x] **格局判定**（`rules/ge_ju.py`）：8 正格映射 + 3 比劫格局
    - 正官格 / 七杀格（偏官格）/ 正财格 / 偏财格
    - 正印格 / 偏印格（枭神格）/ 食神格 / 伤官格
    - 建禄格 / 月劫格 / 羊刃格
- [x] **诊断输出**（`diagnosis.py`）：`Diagnosis` 数据结构
    - `summary()` 一行摘要
    - `explain()` 完整教学模式输出（每条结论都可追溯到《子平真诠》原文）
    - `to_dict()` JSON 友好序列化
- [x] **顶层引擎**（`engine.py`）：`diagnose(chart)` 串联所有规则

### 9. 比劫当令的另寻用神算法 —— Layer 2 v0.2.1 新增

- [x] **优先级搜索算法**（`rules/yong_shen.py::_find_alternative_yong_shen`）：
    - 按优先级 `正官 → 七杀 → 财星 → 印星 → 食伤 → 无可用` 搜索月令之外的用神
    - 每个优先级内：天干透出优先（year/month/hour），藏干次之（year/day/hour 支）
    - 来源：《子平真诠·论建禄月劫》《论羊刃》
- [x] **6 条新规则**：
    - ZP-YONG-006 取官星为用（最高优先级）
    - ZP-YONG-007 无官用杀（羊刃格最喜）
    - ZP-YONG-008 官杀俱无取财
    - ZP-YONG-009 财官俱无取印
    - ZP-YONG-010 印亦无取食伤
    - ZP-YONG-011 兜底：所有候选皆无，标记真无可用
- [x] **结果增强**：`YongShenResult` 新增 `alternative_source` 字段（如"透于hour干"/"藏于day支中气"）
- [x] **格局判定同步更新**：建禄/月劫/羊刃格局在用神已定时 `unresolved=False`，citation 注明"月令之外取 X 为用神"
- [x] **explain() 教学模式**：比劫当令的推理链从 ZP-YONG-000 → ZP-YONG-005 → ZP-YONG-006~010，每步可追溯

### 10. 相神 / 忌神识别 —— Layer 2 v0.2.2 新增

- [x] **相神忌神查表**（`rules/xiang_shen.py::XIANG_JI_TABLE`）：八大正格各自的相神/忌神映射
    - 正官格：相神=财/印，忌神=伤官/七杀
    - 七杀格：相神=食神/印，忌神=财
    - 正财/偏财格：相神=食伤，忌神=比劫
    - 正印/偏印格：相神=官杀，忌神=财
    - 食神格：相神=财，忌神=偏印（枭神夺食）
    - 伤官格：相神=印/财，忌神=正官（伤官见官）
- [x] **2 条新规则**：
    - ZP-XIANG-001 相神紧要（来源：《子平真诠·论相神紧要》）
    - ZP-JI-001 忌神破用（来源：《子平真诠·论用神成败》）
- [x] **识别算法**（`rules/xiang_shen.py::identify_xiang_ji`）：
    - 扫描所有位置（天干 + 藏干），匹配相神/忌神十神集合
    - 排除日干和用神本身
    - 输出 `StemOccurrence` 列表（含 position / location / stem / ten_god）
- [x] **特殊提示**（notes）：
    - 枭神夺食（食神格 + 偏印现）
    - 伤官见官（伤官格 + 正官现）
    - 官杀混杂（正官格 + 七杀现）

### 11. 格局成败评估 —— Layer 2 v0.2.2 新增

- [x] **三态判定**（`rules/ge_ju_cheng_bai.py::assess_cheng_bai`）：
    - **成格**：用神已立 + 无忌神破坏（用神有力，相神护卫到位或虽无相神亦无忌神）
    - **救应**：忌神现 + 相神可制忌神（反败为成，相神兼作救神）
    - **败格**：忌神现 + 无相神可救（忌神破用神而无救应）
    - **未定**：用神未定（如比劫当令另寻失败，或十神不在八大正格之列）
- [x] **3 条新规则**：
    - ZP-CHENG-001 成格规则（来源：《子平真诠·论用神成败》）
    - ZP-BAI-001 败格规则（来源：《子平真诠·论用神成败》）
    - ZP-JIUYING-001 救应规则（来源：《子平真诠·论用神成败》）
- [x] **数据结构**：`ChengBaiResult` 含 `verdict` / `source_rule_id` / `rescue_gods` / `citations`
- [x] **诊断输出扩展**：`Diagnosis` 新增 `xiang_shen` 和 `cheng_bai` 字段，`to_dict()` 和 `explain()` 同步更新

### 12. 刑冲合化检测 —— Layer 2 v0.2.3 新增

- [x] **天干五合**（`interactions.py::GAN_HE_TABLE`）：5 组合化关系
    - 甲己合化土、乙庚合化金、丙辛合化水、丁壬合化木、戊癸合化火
    - 检测四柱任意两天干之间的合关系
- [x] **地支三合**（`interactions.py::SAN_HE_TABLE`）：4 组三合局
    - 申子辰合水、亥卯未合木、寅午戌合火、巳酉丑合金
    - 支持全三合（3 支全见）和半三合（2 支见，标注缺哪一支）
- [x] **地支三会**（`interactions.py::SAN_HUI_TABLE`）：4 组三会方
    - 寅卯辰会木、巳午未会火、申酉戌会金、亥子丑会水
    - 支持全三会和半三会
- [x] **地支六冲**（`interactions.py::LIU_CHONG_TABLE`）：6 组对冲
    - 子午冲、丑未冲、寅申冲、卯酉冲、辰戌冲、巳亥冲
- [x] **地支相刑**（`interactions.py`）：三种刑
    - 三刑：寅巳申 / 丑戌未（支持全见和缺一支两种情况）
    - 互刑：子卯（无礼之刑）
    - 自刑：辰午酉亥（同支重复出现时触发）
- [x] **地支相害**（`interactions.py::HAI_TABLE`）：6 组相害
    - 子未害、丑午害、寅巳害、卯辰害、申亥害、酉戌害
- [x] **6 条新规则**：
    - ZP-HE-GAN 天干五合（来源：《子平真诠·论天干五合》）
    - ZP-SAN-HE 地支三合（来源：《子平真诠·论地支三合》）
    - ZP-SAN-HUI 地支三会（来源：《子平真诠·论地支三会》）
    - ZP-CHONG 地支六冲（来源：《子平真诠·论地支六冲》）
    - ZP-XING 地支相刑（来源：《子平真诠·论地支相刑》）
    - ZP-HAI 地支相害（来源：《子平真诠·论地支相害》）
- [x] **数据结构**：`Interaction`（单条互动）+ `InteractionResult`（聚合结果），含 `summary()` 和 `has_any()`
- [x] **诊断输出扩展**：`Diagnosis` 新增 `interactions` 字段，`to_dict()` 和 `explain()` 含"刑冲合化"专区

### 13. LLM 仲裁层 —— Layer 3 v0.3.0 新增

- [x] **设计原则**：
    - **不在本库内调用 LLM**：只产出 prompt 和解析 response，保持确定性可测试
    - **每个 case 都有证据**：LLM 不是"看八字瞎猜"，而是面对具体的结构化冲突
    - **强制置信度 + "无法判定"**：防止幻觉，置信度低于阈值（默认 0.6）等同于"无法判定"
    - **Response schema 严格校验**：`parse_arbitration_response()` 拒绝格式错误
- [x] **5 种冲突类型检测**（`arbitration.py::detect_arbitration_cases`）：
    - **RESCUE**：v0.2.2 判为"救应"，但相神的五行不克忌神的五行（如 印木 不能制 财金）
    - **HE_CHONG**：某地支同时在三合和六冲中（"贪合忘冲"是否成立？）
    - **HE_HUA**：天干五合结构上成立，但化神是否有月令支持（"真化"vs"合绊"）
    - **XING_CHONG**：3 组以上刑冲共存（"动荡命"程度评估）
    - **GE_JU_ZHEN_JIA**：用神十神已定但力量边界（"真格"vs"假格"）
- [x] **数据结构**：
    - `ArbitrationCase`：单条冲突（含 category / title / description / evidence / relevant_rules / options）
    - `ArbitrationPrompt`：给 LLM 的 prompt（含 system_prompt / user_prompt / expected_schema）
    - `ArbitrationResponse`：LLM 回应（含 decision / reasoning / confidence / cited_rules），`is_unresolved()` 方法
    - `ArbitrationResult`：聚合结果，`unresolved_cases()` 方法
- [x] **Prompt 构建**（`build_arbitration_prompt`）：
    - system_prompt 明确要求 LLM 输出 JSON、给置信度、引用规则
    - user_prompt 包含案例描述、结构化证据、相关规则原文、可选项
    - expected_schema 是严格的 JSON Schema（enum 锁定 options）
- [x] **Response 解析**（`parse_arbitration_response`）：
    - 自动剥离 markdown 代码块（```json ... ```）
    - 校验必填字段、decision 必须在 options 内（或"无法判定"）
    - 校验 confidence ∈ [0.0, 1.0]
    - 无效输入抛 `ArbitrationParseError`
- [x] **顶层入口**：`prepare_arbitration(d)` 一键产出所有 case + prompt；`attach_response()` 填充 response

### 14. CLI 命令行工具 —— v0.4.0 新增

`bazibase diagnose` 子命令，支持从命令行一键排盘 + 诊断 + 仲裁 prompt 生成。

**五种输出模式**：

- [x] **默认（summary）**：一行摘要
    ```bash
    $ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male
    癸巳年 甲子月 丁酉日 甲辰时 | 日主丁(身弱) | 逆运 6岁起运 | 用神癸(七杀) | 七杀格 | 救应
    ```
- [x] **`--explain`（教学模式）**：完整推理链，含规则原文 / 现状 / 结论
- [x] **`--json`（结构化输出）**：`{chart: {...}, diagnosis: {...}}` 完整 JSON
- [x] **`--chart-only`**：仅 Layer 1 排盘（不跑 Layer 2）
- [x] **`--arbitrate`（LLM 仲裁模式）**：输出 JSON 数组，每个元素含 `case_id / system_prompt / user_prompt / expected_schema`，可直接管道给外部 LLM

**可选参数**：

- `--tz <float>`：时区偏移（默认 8.0 北京时间）
- `--no-solar`：不做真太阳时修正
- `--luck <int>`：大运数量（默认 8）
- `--explain` 与 `--json` 互斥（一个是纯文本，一个是结构化）

**错误处理**：日期/时间格式错误、gender 非法均返回 exit code 2 + stderr 提示。

## 已验证的回归锚点

### Layer 1 锚点

| 出生信息 | 期望 | 状态 |
|----------|----------|------|
| 1893-12-26 08:00 北京时间, 112.9°E | 癸巳 / 甲子 / 丁酉 / 甲辰 | ✅ |
| 立春 2024 边界（16:25 vs 16:28） | 癸卯→甲辰 | ✅ |
| 惊蛰 2024 边界（10:20 vs 10:25） | 寅月→卯月 | ✅ |
| 子时跨日（23:30 vs 00:30） | 时支均为子，日柱前进一日 | ✅ |
| 北京 vs 乌鲁木齐同时辰 | 12:00 北京→午时, 乌鲁木齐→巳时 | ✅ |
| 60甲子日柱连续性 | 相邻日柱在60甲子中只差一步 | ✅ |

### Layer 2 锚点（v0.2.0）

| 出生信息 | 期望诊断 | 用神路径 | 状态 |
|----------|----------|----------|------|
| 1893-12-26 08:00, 112.9°E | 用神癸(七杀), 七杀格 | 本气透 (ZP-YONG-001) | ✅ |
| 2024-05-15 12:00 | 用神庚(伤官), 伤官格 | 中气透 (ZP-YONG-002) | ✅ |
| 2023-04-06 12:00 | 用神癸(正印), 正印格 | 余气透 (ZP-YONG-003) | ✅ |
| 2024-03-15 12:00 | 用神乙(正官), 正官格 | 暗用 (ZP-YONG-004) | ✅ |

### Layer 2 v0.2.1 锚点（比劫当令另寻用神）

| 出生信息 | 四柱 | 格局 | 用神 | 路径 | 状态 |
|----------|------|------|------|------|------|
| 2024-02-10 12:00 | 甲辰/丙寅/甲辰/庚午 | 建禄格 | 庚(七杀) | 透于hour干 (ZP-YONG-007) | ✅ |
| 2024-03-11 12:00 | 甲辰/丁卯/甲戌/庚午 | 羊刃格 | 辛(正官) | 藏于day支中气 (ZP-YONG-006) | ✅ |
| 2024-02-11 12:00 | 甲辰/丙寅/乙巳/壬午 | 月劫格 | 庚(正官) | 藏于day支中气 (ZP-YONG-006) | ✅ |

### Layer 2 v0.2.2 锚点（相神忌神 + 格局成败）

| 出生信息 | 用神 | 相神数 | 忌神数 | 败神/救神 | 成败 | 状态 |
|----------|------|--------|--------|-----------|------|------|
| 1893-12-26 08:00, 112.9°E | 癸(七杀) | 3 (甲正印×2, 乙偏印) | 2 (庚/辛财) | 印为救神 | 救应 (ZP-JIUYING-001) | ✅ |
| 2000-06-15 12:00, 116.4°E | 丁(伤官) | 7 | 0 | 无忌神 | 成格 (ZP-CHENG-001) | ✅ |

### Layer 2 v0.2.3 锚点（刑冲合化）

| 出生信息 | 四柱地支 | 检测到的互动 | 状态 |
|----------|----------|-------------|------|
| 1960-08-20 16:00, 116.4°E | 子申辰申 | 三合水局（申子辰全） | ✅ |
| 1893-12-26 08:00, 112.9°E | 巳子酉辰 | 半三合×2（子+辰缺申, 巳+酉缺丑） | ✅ |
| 2000-06-15 12:00, 116.4°E | 辰午辰午 | 自刑×2（辰+辰, 午+午） | ✅ |
| 1990-10-15 14:00, 116.4°E | 午戌丑未 | 三刑（丑戌未）+ 六冲（丑未）+ 相害（丑午） | ✅ |
| 1970-03-15 10:00, 116.4°E | 戌卯午巳 | 天干合×2（甲+己） | ✅ |
| 2024-03-11 12:00, 116.4°E | 辰卯戌午 | 六冲（辰戌）+ 相害（卯辰） | ✅ |

### Layer 3 v0.3.0 锚点（LLM 仲裁）

| 出生信息 | 检测到的冲突类型 | 冲突数 | 状态 |
|----------|-----------------|--------|------|
| 1893-12-26 08:00, 112.9°E | RESCUE（甲木 vs 庚金/辛金） | 2 | ✅ |
| 2000-06-15 12:00, 116.4°E | 无（成格，无忌神） | 0 | ✅ |
| 1970-03-15 10:00, 116.4°E | RESCUE + HE_HUA（甲己合） | 6 | ✅ |
| 1942-01-08 06:00, 116.4°E | HE_CHONG（酉卯冲 vs 三合） | 1+ | ✅ |
| 1981-12-18 13:00, 116.4°E | XING_CHONG（2冲+1刑） | 1+ | ✅ |

### v0.4.0 锚点（CLI）

| 命令 | 期望输出 | 状态 |
|------|----------|------|
| `diagnose 1893-12-26 08:00 --lon 112.9 --gender male` | summary 单行 | ✅ |
| `diagnose ... --explain` | 教学模式（含 ZP- 规则原文） | ✅ |
| `diagnose ... --json` | `{chart, diagnosis}` JSON | ✅ |
| `diagnose ... --chart-only` | Layer 1 排盘（无诊断） | ✅ |
| `diagnose 1893-12-26 08:00 ... --arbitrate` | JSON 数组（含 RESCUE case） | ✅ |
| `diagnose 2000-06-15 12:00 ... --arbitrate` | `[]`（干净八字无冲突） | ✅ |
| `diagnose not-a-date 08:00 ...` | exit code 2 + stderr 错误 | ✅ |

## 已知限制（v0.4.0 不解决，文档化即可）

### Layer 1 限制

1. **真太阳时跨日错位**：出生经度极端偏西（如新疆 87°E）时，TST 可能比北京时间晚 2 小时以上，导致 TST 落在前一日。此时日柱（用北京时间）和时支（用 TST）会出现"日柱属于今日 / 时支属于昨日"的错位。
   - **影响范围**：仅影响出生时刻在 UTC+8 凌晨 0:00–2:00 且经度 < 90°E 的极少数 case。
   - **临时处理**：用户可通过 `apply_solar_time_correction=False` 关闭 TST 修正。

2. **晚子时派**：当前只实现"日界在 00:00"派。若用户要"23:00 起算次日"派，需要后续扩展。

3. **均时差近似**：用 Spencer 公式，精度 ±0.5 分钟。对八字来说足够（时支是 2 小时区间），但天文历法层面不是最高精度。

4. **神煞**：v1 不实现（天乙、桃花、驿马等）。这些在子平派里属于"添加剂"，预测力弱，先不做。

### Layer 2 限制（v0.3.0）

5. **比劫另寻的边界**：v0.2.1 实现了通用优先级（官→杀→财→印→食伤），但没有为羊刃格做特殊加权（羊刃理应最喜七杀制刃，但当前算法在正官存在时仍优先取正官）。

6. **救应判定简化**：v0.2.2 的 `_find_rescue_gods()` 采用简化模型——只要相神存在就视为潜在救神。v0.3.0 的仲裁层已能**检测**此类冲突（RESCUE case），但**不在本库内自动修正**——修正需调用方拿到 prompt 问 LLM 后，根据 response 自行调整。

7. **相神忌神未做强弱评估**：v0.2.2 只识别相神/忌神的存在与否，不评估其强弱。v0.2.3 虽已检测合冲刑害，但还未将互动结果（如"三合水局使水变强"）应用到十神强弱计算中。

8. **合化成立条件未判定**：v0.2.3 检测到天干五合/地支三合后，只输出"结构上存在合"。v0.3.0 的仲裁层已能**检测**化与不化的疑问（HE_HUA case），但最终判断仍需 LLM 介入。

### Layer 3 限制（v0.3.0）

9. **仲裁层不调用 LLM**：bazibase 保持纯确定性库定位，只产出 prompt 和解析 response。实际 LLM 调用、重试、超时等由调用方负责。

10. **GE_JU_ZHEN_JIA 检测器未实装**：5 种冲突类型中，RESCUE/HE_CHONG/HE_HUA/XING_CHONG 已实装检测器；GE_JU_ZHEN_JIA（格局真假）需要更精细的用神强弱评估，暂留为空壳，待后续版本补全。

11. **仲裁结果不回写 Diagnosis**：`ArbitrationResult.responses` 是独立结构，不会自动修改原始 `Diagnosis` 的 `cheng_bai.verdict` 等字段。调用方需自行根据仲裁结果调整展示。

## 下一步路线

### 长期（Layer 3 + 反馈闭环）

1. **多流派对比**：同一八字，输出"格局派 / 调候派 / 滴天髓派"分别怎么看
2. **反馈闭环**：每个解读入库，半年/一年后用户标记应验/未应验，自动生成"命中率报告"
3. **教学模式**：agent 不直接给结论，而是反问用户"你认为月令用神是谁？"——把它变成命理学习的陪练工具
4. **断大事分级**：方向级（富贵贫贱）/ 中等（事业偏文偏武）/ 细节（某年发财破财）。默认只输出前两级。

## 文件清单（v0.4.0）

```
bazibase/
├── pyproject.toml
├── README.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── PROGRESS.md
├── bazibase/
│   ├── __init__.py             (115 行) 公开 API（含 Layer 3 + CLI）
│   ├── constants.py            (224 行) 所有静态查表
│   ├── solar_time.py           (126 行) 真太阳时校正
│   ├── pillars.py              (255 行) 四柱排盘
│   ├── luck.py                 (173 行) 大运起算
│   ├── ten_gods.py             (114 行) 十神标注
│   ├── strength.py             (156 行) 日主旺衰
│   ├── chart.py                (246 行) 顶层入口（Layer 1）
│   ├── diagnosis.py            (404 行) Diagnosis 数据结构（v0.2.3 扩展刑冲合化）
│   ├── engine.py               (80 行)  diagnose() 顶层入口（v0.2.3 扩展）
│   ├── arbitration.py          (686 行) LLM 仲裁层（v0.3.0 新增）
│   ├── cli.py                  (182 行) CLI 命令行工具（v0.4.0 新增）
│   └── rules/
│       ├── __init__.py         (86 行)  规则统一导出
│       ├── schema.py           (89 行)  Rule / RuleCitation / 注册表
│       ├── yong_shen.py        (508 行) 用神取法 + 11 条规则
│       ├── ge_ju.py            (255 行) 格局判定 + 4 条规则
│       ├── xiang_shen.py       (316 行) 相神/忌神识别 + 2 条规则
│       ├── ge_ju_cheng_bai.py  (286 行) 格局成败评估 + 3 条规则
│       └── interactions.py     (701 行) 刑冲合化检测 + 6 条规则
└── tests/
    ├── conftest.py
    ├── test_constants.py       (165 行)
    ├── test_solar_time.py      (97 行)
    ├── test_pillars.py         (97 行)
    ├── test_luck.py            (135 行)
    ├── test_ten_gods.py        (87 行)
    ├── test_strength.py        (64 行)
    ├── test_chart.py           (136 行)
    ├── test_known_charts.py    (212 行) ← Layer 1 回归锚点
    ├── test_yong_shen.py       (210 行) ← v0.2.1 另寻用神测试
    ├── test_ge_ju.py           (138 行)
    ├── test_xiang_shen.py      (126 行) ← v0.2.2 相神忌神测试
    ├── test_ge_ju_cheng_bai.py (222 行) ← v0.2.2 格局成败测试
    ├── test_interactions.py    (267 行) ← v0.2.3 刑冲合化测试
    ├── test_arbitration.py     (392 行) ← v0.3.0 仲裁层测试
    ├── test_cli.py             (211 行) ← v0.4.0 CLI 测试（新增）
    └── test_engine.py          (140 行)

代码总量：约 5900 行（含测试）
测试数量：263 个（全部通过）
已注册规则：27 条
  - 《子平真诠·论用神》系列 12 条（ZP-YONG-000~011）
  - 格局判定 4 条（ZP-GE-MAP / JIANLU / YUEJIE / YANGREN）
  - 相神忌神 2 条（ZP-XIANG-001 / ZP-JI-001）
  - 格局成败 3 条（ZP-CHENG / BAI / JIUYING-001）
  - 刑冲合化 6 条（ZP-HE-GAN / SAN-HE / SAN-HUI / CHONG / XING / HAI）
LLM 仲裁冲突类型：5 种（RESCUE / HE_CHONG / HE_HUA / XING_CHONG / GE_JU_ZHEN_JIA）
CLI 子命令：1 个（diagnose），5 种输出模式
```

## 使用示例

```python
from datetime import datetime
from bazibase import cast_chart, diagnose

# 标准格局（用神取自月令）
c = cast_chart(
    birth_time=datetime(1893, 12, 26, 8, 0),
    longitude=112.9,
    gender="male",
)
d = diagnose(c)
print(d.summary())
# 癸巳年 甲子月 丁酉日 甲辰时 | 日主丁(身弱) | 逆运 6岁起运 | 用神癸(七杀) | 七杀格 | 救应

# 建禄格（月令为比劫，v0.2.1 另寻用神）
c = cast_chart(datetime(2024, 2, 10, 12, 0), 116.4, "male")
d = diagnose(c)
print(d.summary())
# 甲辰年 丙寅月 甲辰日 庚午时 | 日主甲(身强) | 顺运 7岁起运 | 用神庚(七杀) | 建禄格 | 救应

# 三合局（v0.2.3 刑冲合化）
c = cast_chart(datetime(1960, 8, 20, 16, 0), 116.4, "male")
d = diagnose(c)
print(d.interactions.summary())
# 三合: 子+辰+申→水

# 教学模式 — 每条结论可追溯到原文，含相神忌神、成败和刑冲合化分析
print(d.explain())
# 输出完整推理链：
#   ZP-YONG-000 → ZP-YONG-005 → ZP-YONG-007（用神取法）
#   ZP-XIANG-001 / ZP-JI-001（相神忌神）
#   ZP-CHENG-001 / ZP-BAI-001 / ZP-JIUYING-001（格局成败）
#   ZP-HE-GAN / ZP-SAN-HE / ZP-SAN-HUI / ZP-CHONG / ZP-XING / ZP-HAI（刑冲合化）

# Layer 3 — LLM 仲裁（v0.3.0）
from bazibase import prepare_arbitration, parse_arbitration_response

d = diagnose(cast_chart(datetime(1893, 12, 26, 8, 0), 112.9, "male"))
result = prepare_arbitration(d)
print(f"检测到 {len(result.cases)} 个待仲裁冲突")
for prompt in result.prompts:
    print(f"\n案例: {prompt.case.title}")
    # 把 prompt.user_prompt 发给你的 LLM，拿回 JSON 后解析：
    # raw_json = llm_call(prompt.system_prompt, prompt.user_prompt)
    # response = parse_arbitration_response(prompt.case, raw_json)
    # result = attach_response(result, prompt.case.case_id, response)
```

### CLI 命令行（v0.4.0）

```bash
# 默认：一行摘要
$ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male
癸巳年 甲子月 丁酉日 甲辰时 | 日主丁(身弱) | 逆运 6岁起运 | 用神癸(七杀) | 七杀格 | 救应

# 教学模式：完整推理链 + 规则原文
$ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --explain

# JSON 结构化输出（chart + diagnosis）
$ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --json

# 仅 Layer 1 排盘
$ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --chart-only

# LLM 仲裁 prompts（JSON 数组，管道给外部 LLM）
$ bazibase diagnose 1893-12-26 08:00 --lon 112.9 --gender male --arbitrate | \
    llm-cli --batch
```
