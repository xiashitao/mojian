# Session: 设计 Kairos agent 代码

## Task Info
- Type: design
- Language: 中文
- Started: 2026-07-06
- Scope: web/backend/agent/ (~4300 行,extractor → router → planner → tools → responder + memory/profile/context/tracing)

## Plan
| # | Step | Status | User Level |
|---|------|--------|------------|
| 1 | 设计「话题即数据」registry:条目结构(prompt侧重段+数据选择规则) | done(Claude 代实现,agent/topics.py) | 中(前端背景,首次做后端架构设计) |
| 2 | eval 加「带偏攻击」用例集(话题连跳/越界/施压改口/粒度逼问),跑基线定防御必要性 | done(11/13 通过;A/B/D 全过,C 施压类漏 2:flip-deny 极性翻转、flip-sympathy 误判 smalltalk) | - |
| 3 | 合盘 feature 设计(独立设计,不进插件/registry;等 1、2 落地后启动) | not-started | - |
| 4 | (插入)前端 markdown 渲染:react-markdown 渲染助手消息 | done(Claude 代实现) | - |

## 已达成的设计共识
- 不做通用插件架构:能力清单测试显示 80% 场景是「prompt段+数据选择」,registry 级即可;合盘是唯一三层全动的能力,单独设计
- 追问/带偏防御:无失败样本不设计,先用 eval 攻击用例量化
- 带偏行为定义:A(话题间跳转)=合法,要无缝切且不串话题;B(越界)=router 已有 out_of_scope,待 eval 验证

## Mistakes Log
| # | Step | Mistake | Root Misconception | Resolution |
|---|------|---------|-------------------|------------|

## Insights
- 现有架构原则:确定性事实归引擎,权衡判断归 LLM(router 门控确定性,extractor/responder 用 LLM)
- 已知背景:eval 基线 4.38,量出三类系统 bug(喜忌极性背叛/干支泄漏/年龄混淆);"回答浅显"有深度分析升级规格

## Session Log
- 2026-07-06 用户要求切换模式:由 Claude 直接实现 registry 并测试(结对辅导结束,设计共识见上)
- 2026-07-06 会话开始,完成代码结构初步勘察,进入诊断阶段
- 2026-07-06 目标确认:回答深度升级 + 代码结构重构 + 新能力扩展(未选"修系统性bug")
- 2026-07-06 待回答:①新能力具体清单 ②上次改动最痛的模块(真实案例)
- 2026-07-06 痛点确认:system prompt 不能动态切换/组装。现状:responder.py:684 _system_rules() 硬编码 9 个 _SEC_* 常量拼接,唯一运行时变量是 tone → prompt 是代码不是数据
- 2026-07-06 切换维度:按话题/场景 + 做实验跑eval + 按用户切换;用户还问是否需要管理平台
- 2026-07-06 用户提出:想做一套插件架构,让能力以插件形式添加 → 待检验(先列能力清单+每个能力的挂载点)
- 2026-07-06 能力清单:①话题侧重(学历→考试节点流年,其他类推) ②合盘/八字合婚(肯定要做,性格相合/相处方式) ③追问模式(没想好,担心用户把agent带偏)
- 2026-07-06 挂载点分析进行中:①≈prompt段+数据选择器(data/registry级) ②=三层都动(独立feature级) ③=对话策略问题,非插件
