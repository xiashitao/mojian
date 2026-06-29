# CLAUDE.md — Kairos / 墨鉴 (Mojian)

Kairos 是一个**八字 AI 决策助手**：用户用日常语言问事业/感情/财运/性格/时机，确定性引擎排盘+诊断，LLM 只做**有边界的措辞**。命理是手段，决策是目的。

产品与视觉定位见 `PRODUCT.md` / `DESIGN.md`（本文件不重复，只补"怎么干"和"不可碰的原则"）。

## 架构（三层 + Web）

- **Layer 1 排盘**（`bazibase/`）：纯函数、确定性、**从不读时钟**（"now" 由调用方注入）。`solar_time` / `dst` / `pillars` / `luck` / `ten_gods` / `strength` / `timeline` / `changsheng`。
- **Layer 2 规则**（`bazibase/rules/` + `engine.py` / `diagnosis.py`）：`diagnose()` 串「用神→格局→相神/忌神→成败→刑冲合会→喜忌(fortune)」，全程带规则引用链，锚《子平真诠》格局派。
- **Layer 3 仲裁**（`bazibase/arbitration.py`）：规则冲突时才上 LLM，结构化进出。
- **Web 后端**（`web/backend/`）：FastAPI。`agent/`（planner 状态机 / router / extractor / tools / responder / context / memory / repository）；`services/`（llm 网关分 fast/deep；nayin / kong_wang / shensha …）；`routers/`。
- **前端**（`web/frontend/`）：React + TS + Vite，设计系统「墨鉴 / 素卷」。

## 不可碰的原则（改代码前先认这几条）

1. **确定交引擎、不确定交模型**：规则可定的事实 → 引擎；需权衡的判断 → LLM。引擎不读时钟。
2. **引擎纯子平真诠**：单一流派（格局派）。别混扶抑/调候/盲派。**神煞只在 web 层做展示，绝不进引擎判断、不喂 LLM**。
3. **引擎定吉凶『符号』、模型定『统观』**：每个干支的喜忌符号是确定事实、LLM 不许翻转（别把引擎判「忌/增凶」的说成好运）；LLM 只综合多符号的净顺逆 + 措辞。
4. **看大不看小**：时间粒度最多到「流年（哪一年）」，绝不到月/日/季度。
5. **Grounding**：年龄/年份/数字只引用引擎给的、不自行换算；年龄是『虚岁』；回答里**不报干支**（用年份 + 十神白话指代）。
6. **确定性**：同输入 → 同输出。

## 前端设计系统（双主题，两条硬规则）

- **无影 Rule**：会话区禁 `box-shadow`（用边框 + 底色分层）。焦点环用 `outline`（不算 box-shadow，可用）。
- **素 Rule**：浅色模式禁饱和红；用主题感知的 `--cinnabar`（浅色自动 → 赭）。五行色用 `--el-*` token（每主题一套）。
- **应用同时跑浅色 + 深色，两套都要测。** 坑：`mix-blend-mode: screen` 在浅色底上不可见。
- 一切走 token；与现有组件对齐，别造一次性样式。

## 怎么跑 / 怎么验

- **后端**：`cd web && PYTHONPATH=<repo根> .venv/bin/python -m uvicorn backend.main:app --port 8010 --reload`（前端 `/api` 代理到 8010）
- **前端**：`cd web/frontend && npm run dev`（Vite，5173）
- **测试**：repo 根 `pytest`（conftest 自动加 path）；前端 `cd web/frontend && npx tsc -b` 查类型
- **回答质量 eval**（改 prompt/引擎后必跑的回归网）：`PYTHONPATH=. python -m web.backend.eval.run [case_id]`，报告落 `web/backend/eval/reports/`
- Vite 直编 `.tsx`；**别提交 `tsc -b` 误生成的 `src/**/*.js`**（已 gitignore）。

## 与本仓协作的坑（省返工）

- **命盘卡在排盘那刻生成并存库**：给卡新增字段后，**只有之后新排的盘**才有 —— 测新功能要**开全新对话**，旧对话走 fallback。
- **视觉/UI 的活**：Claude 看不见屏幕 —— **尽早给截图**，预期要迭代几轮。
- **可能有并发窗口改同一文件**：编辑前先重读、只提交自己的文件、push 用快进。
- 在**分支**上干活、**逻辑分块提交**、提交前跑 `pytest` / `tsc`。
- 大改动**先出方案再写**、拆成**可验证的小阶段**；改 prompt/引擎后**跑 eval** 看分数别凭感觉。
