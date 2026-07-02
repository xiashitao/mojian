---
name: 墨鉴 Mojian
description: Chat-first Ba Zi consultation — restrained, professional, trustworthy.
colors:
  # ── Dark mode (default) ──
  ink-950: "#08060a"
  ink-900: "#0c0a07"
  ink-850: "#131008"
  ink-800: "#1a150d"
  ink-700: "#221b10"
  ink-600: "#2d2516"
  ink-500: "#3a3020"
  bone-100: "#f1e8d5"
  bone-200: "#e2d6bf"
  bone-300: "#c1b497"
  bone-400: "#90846a"
  bone-500: "#918576"
  cinnabar: "#c64d3f"
  vermilion: "#d85f4d"
  bronze: "#8b7151"
  jade: "#6b8e6f"
  gold: "#ccb07a"
  # ── Light mode ──
  light-ink-950: "#fbf7ef"
  light-ink-900: "#f9f3e8"
  light-ink-850: "#f5eee0"
  light-ink-800: "#efe5d2"
  light-ink-700: "#e7dcc6"
  light-bone-100: "#2c2622"
  light-bone-200: "#3d3632"
  light-bone-300: "#5a524a"
  light-bone-400: "#7a7168"
  light-bone-500: "#746a5c"
  light-cinnabar: "#8b5e4a"
  light-vermilion: "#9a6b56"
  light-bronze: "#7a6548"
  light-gold: "#96794c"
typography:
  brand:
    fontFamily: "'Noto Serif SC', 'Songti SC', serif"
    fontWeight: 600
    letterSpacing: "0.12em"
  body:
    fontFamily: "'Inter', system-ui, -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  mono:
    fontFamily: "'JetBrains Mono', 'SF Mono', 'Menlo', monospace"
    fontSize: "10px"
    fontWeight: 400
    letterSpacing: "0.04em"
  display:
    fontFamily: "'Noto Serif SC', 'Songti SC', serif"
    fontSize: "52px"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "0.10em"
rounded:
  # 以代码为准的真实圆角阶梯（软圆角系统，非「几乎为直角」）
  hairline: "2px"   # 细条 / 滚动条 / 极小指示（strength-track、legend-bar、popover option）
  xs: "3px"         # 标签 chip / tag（god-chip、case-status、response-rule-chip）
  sm: "4px"         # 小按钮 / 次级控件（.btn、theme-toggle、workbench input）
  md: "6px"         # 常规按钮 / 导航项 / 小卡（oracle-chip、nav、case-card、liunian-cell）
  lg: "8px"         # 卡片 / 面板 / 输入条（.card、rail-card、input-bar、tone-popover）
  xl: "10px"        # 表单输入 / 主按钮 / 命盘数据块（auth-input、auth-submit、bazi-col、dayun）
  "2xl": "12px"     # 落地页输入 / 演示气泡（landing__composer、demo__bubble）
  "3xl": "14px"     # 大卡片 / hero 卡（welcome__card、chart-card__capture、demo）
  modal: "16px"     # 模态框（auth-modal）
  bubble: "22px"    # 消息气泡 / composer 输入舱（message body、composer__box；气泡带一角切角）
  full: "999px"     # 药丸按钮 / 圆点 / 头像（另有 50% 用于正圆）
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "22px"
  xl: "48px"
components:
  button-primary-dark:
    backgroundColor: "{colors.cinnabar}"
    textColor: "{colors.bone-100}"
    rounded: "{rounded.xl}"
    padding: "11px 24px"
  button-primary-dark-hover:
    backgroundColor: "{colors.vermilion}"
    textColor: "{colors.bone-100}"
  button-primary-light:
    backgroundColor: "{colors.light-bone-200}"
    textColor: "{colors.light-ink-950}"
    rounded: "{rounded.xl}"
    padding: "11px 24px"
  button-primary-light-hover:
    backgroundColor: "{colors.light-bone-100}"
    textColor: "{colors.light-ink-950}"
  input-default:
    backgroundColor: "{colors.ink-900}"
    textColor: "{colors.bone-200}"
    rounded: "{rounded.xl}"
    padding: "11px 14px"
  card-rail:
    backgroundColor: "{colors.ink-850}"
    rounded: "{rounded.lg}"
    padding: "14px 16px"
---

# Design System: 墨鉴 Mojian

## 1. Overview

**Creative North Star: "素卷 · The Unadorned Scroll"**

墨鉴的视觉系统追求去装饰、去玄学包装的专业感。像一卷素纸上的墨迹——信息通过结构和层次自然显现，而非靠红金装饰、神秘符号或夸张排版来制造仪式感。专业感来自判断边界的克制、术语的精确、以及每一处留白的有意为之。

深色模式以近黑暖底（ink-850 `#131008`）为主场景，保留一抹克制的朱砂红作为唯一强调色。浅色模式则完全退去红色，转为暖棕色系——cinnabar 降为赭色 `#8b5e4a`，按钮使用 bone 深色而非红色底，形成「素」的基调。两套主题共享同一套 ink/bone 语义层级，仅映射值不同。

产品明确拒绝的方向：重红金装饰的「天机」「玄机」类网站风格、排盘工作台作为默认界面、营销式夸张 hero、全知大师包装。DESIGN.md 的每条规则都服务于这条线。

**Key Characteristics:**
- 聊天优先，排盘隐藏在后台
- 深色有墨韵，浅色去红存素
- 单一强调色策略（Restrained）
- 留白即信息，克制即专业

## 2. Colors: The Ink & Bone Palette

调色板以墨（ink）与骨（bone）两条中性轴为骨架，搭配一个语义强调色家族。深色模式下朱砂（cinnabar）作为唯一彩色；浅色模式下朱砂退为赭棕，让界面回到「素纸」基调。

### Primary

- **朱砂 Cinnabar** (`#c64d3f` dark / `#8b5e4a` light): 深色模式下的唯一强调色。用于发送按钮、消息装饰线、活跃状态。浅色模式下降饱和为赭棕，仅作微妙点缀，不在按钮或大面积元素上出现。
- **朱红 Vermilion** (`#d85f4d` dark / `#9a6b56` light): Cinnabar 的 hover/active 态。

### Secondary

- **青铜 Bronze** (`#8b7151` dark / `#7a6548` light): 用户消息边线、生辰信息卡边框。低调的暖标记色。
- **金 Gold** (`#ccb07a` dark / `#96794c` light): 极少使用。仅出现在来源权威标注等特殊场景。

### Neutral

- **Ink 系列** (6 阶，深→浅): 背景层级。深色 `#08060a` → `#3a3020`；浅色 `#fbf7ef` → `#c8bd9d`。
- **Bone 系列** (5 阶，亮→暗): 文本与前景。深色 `#f1e8d5` → `#918576`；浅色 `#2c2622` → `#746a5c`。

### Named Rules

**The素 Rule.** 浅色模式下禁止使用饱和红色（cinnabar dark `#c64d3f`）作为按钮背景、边框强调或大面积色块。所有强调色退为赭棕色系。「红」只属于深色模式的墨韵场景。

**The 4.5 Rule.** 所有 placeholder 文本、提示文字和 muted 标签必须达到 WCAG AA 4.5:1 对比度。bone-500 在两套主题下已校准至该标准。

## 3. Typography

**Display Font:** Noto Serif SC (with Songti SC fallback)
**Body Font:** Inter (with system-ui, PingFang SC, Microsoft YaHei fallback)
**Label/Mono Font:** JetBrains Mono (with SF Mono, Menlo fallback)

**Character:** 宋体衬线用于品牌标识和 Landing 标题，传达「书卷」气质但不过度装饰。正文用 Inter 无衬线，确保长文阅读舒适。Monospace 仅用于 9–11px 的辅助标签（时间戳、分析 ID、hint 文字），提供技术可信感。

### Hierarchy

- **Display** (Noto Serif SC, 500, 52px, line-height 1.08, tracking 0.10em): Landing 页标题「墨鉴」。仅此一处。
- **Headline** (Inter, 500, 20px, line-height 1.2, tracking 0.08em): Rail 卡片主值（如当前所问的主题名）。
- **Title** (Inter/Noto Serif SC, 600, 22px, tracking 0.12em): Header 品牌名「墨鉴」。
- **Body** (Inter, 400, 14–14.5px, line-height 1.65–1.85): 消息正文、说明文字。消息体 max-width 680px (≈65ch)。
- **Label** (JetBrains Mono, 400–500, 9–11px, tracking 0.04–0.18em, uppercase): 卡片标签、时间戳、分析 ID、hint 文字。

### Named Rules

**The 一字一体 Rule.** 同一个界面元素只用一种字体，不在一个元素内混排（不在按钮里混入衬线，不在 label 里混入 body 字体）。

衬线（Noto Serif SC，`--font-brand`）的适用范围以代码为准，包括三类：① 品牌标识与 Display 级标题（landing「墨鉴」）；② **各级标题**——卡片标题、模态框标题、欢迎标题等（`.chart-card__title`、`.detail-modal__title`、`.auth-modal__title`、`.welcome__title`）；③ **天干地支等命理字符**，借衬线传递书卷字形（`.bazi-col__branch`、`.dayun__gz`、`.liunian__gz` 等）。正文、标签、hint、按钮文字、输入框一律用 Inter（`--font-cn`）。

## 4. Elevation

墨鉴使用 **色调分层** 而非阴影来表达深度。背景层级通过 ink 系列的明度阶梯区分：ink-900（侧面板）→ ink-850（主内容区）→ ink-800/700（卡片、悬浮态）。

唯一的阴影出现在 Landing 页的输入框（`box-shadow: 0 18px 54px rgba(0,0,0,0.32)`），这是全站仅有的 shadow，用于在「空」的 Landing 页中锚定视觉焦点。

浅色模式同理：`ink-950`（最亮）→ `ink-850`（主区域）→ `ink-700`（hover 态），深度通过明度递减而非投影。

### Named Rules

**The 无影 Rule.** Session 页面（三栏工作区）禁止使用 box-shadow。深度仅靠 ink 色阶和 1px rule-line 边线表达。移动端抽屉的阴影是唯一例外（`box-shadow: 4px 0 24px rgba(0,0,0,0.4)`），属于遮挡层而非装饰。

## 5. Components

### Buttons

- **Shape:** 软圆角系统。主操作 / 表单按钮 10px（`rounded.xl`，如发送、验证码提交），常规按钮 / 导航项 6px（`rounded.md`），次级 / 小按钮 4px（`rounded.sm`，如 `.btn`、主题切换）。药丸按钮用 999px。整体偏圆润克制，不是「几乎为直角」。
- **Primary (dark):** cinnabar `#c64d3f` 底，bone-100 文字。Hover 升为 vermilion `#d85f4d`，translateY(-1px)。
- **Primary (light):** bone-200 `#3d3632` 底，ink-950 `#fbf7ef` 文字。Hover 加深至 bone-100 `#2c2622`。无红色。
- **Disabled:** 透明底，rule-line-bright 边框，bone-500 文字。两套主题一致。
- **Focus:** 2px outline，rgba(237, 228, 204, 0.72)，offset 3px。

### Message Bubbles

- **用户消息:** 左侧 2px bronze 边线（深色）/ 1px bone-400 边线（浅色），bone-100 文字。
- **助手消息:** 左侧 2px cinnabar 边线 + 渐变背景洗（深色）/ 1px bone-400 边线 + 微暖背景（浅色）。末尾「墨」印章标记。
- **错误消息:** bone-500 边线，斜体，降低对比度。

### Chips (Follow-up / Rail)

- **Style:** 透明底，1px rule-line-bright 边框，bone-300 文字。圆角 3px（tag/chip，`rounded.xs`）～ 6px（follow-up chip 如 `.oracle-chip`，`rounded.md`）。
- **Hover (dark):** 边框变 cinnabar，文字变 cinnabar。
- **Hover (light):** 边框变 bone-300，文字变 bone-200，微背景色。
- **Disabled:** opacity 0.4。

### Cards / Rail Cards

- **Corner Style:** 卡片 / 面板 8px（`rounded.lg`，如 `.card`、`.rail-card`）；大卡片 / hero 卡 14px（`rounded.3xl`，如 `.welcome__card`）；命盘数据块 10px（`rounded.xl`，如 `.bazi-col`、`.dayun`）。
- **Background:** ink-850（与主内容区同色，靠边框区隔）。
- **Border:** 1px solid rule-line。
- **Birth info card:** 使用 bronze-wash 边框色（深色）/ rule-line-bright（浅色）。
- **Alert 区块:** cinnabar-soft 底 + 2px cinnabar 左线（深色）/ bone-400 底 + 1px bone-400 左线（浅色）。

### Inputs / Composer

- **Style:** ink-900 底，1px rule-line 边框。表单输入 10px 圆角（`rounded.xl`，如 `.auth-input`）；主聊天 composer 输入舱 22px（`rounded.bubble`，`.composer__box`）；落地页输入 12px（`rounded.2xl`）。
- **Focus:** 边框变 bone-400（深浅两色一致，如 `.composer__box:focus-within`、`.auth-input:focus`）。输入框聚焦不使用朱砂红——强调色留给发送/提交按钮本身。
- **Placeholder:** bone-500，已校准至 4.5:1 对比度。

### Archive Panel (Slip)

- **Default:** 透明底，底部 1px rule-line 分隔。
- **Hover (dark):** bronze-soft 背景。
- **Hover (light):** rgba(90, 82, 74, 0.05) 背景。
- **Active:** 左侧 2px cinnabar 边线（深色）/ bone-300 边线（浅色），cinnabar-soft / bone-soft 背景。

### Theme Toggle

- **Style:** 方形按钮，4px 圆角（`rounded.sm`，`.theme-toggle`），1px rule-line-bright 边框。
- **Icons:** 内联 SVG — 太阳（浅色）、月亮（深色）、半明半暗太阳（跟随系统）。
- **Behavior:** 单击循环：system → light → dark。

## 6. Do's and Don'ts

### Do:

- **Do** 在浅色模式下使用 bone 色系（棕灰）作为所有强调色，保持「素」的基调。
- **Do** 确保所有文本（包括 placeholder）达到 WCAG AA 4.5:1 对比度。bone-500 已为两套主题校准。
- **Do** 用 ink 色阶的明度差异表达层级，而非 box-shadow。
- **Do** 让 Serif 字体（Noto Serif SC）仅出现在品牌标识和 Landing 页 Display 标题。
- **Do** 保持深色和浅色主题在组件结构上的一致性——只改颜色映射值，不改布局或组件形态。

### Don't:

- **Don't** 在浅色模式下使用饱和红色（如 `#c64d3f`、`#b94d40`）作为按钮、边框或装饰色。这是"素卷"的核心禁令。
- **Don't** 使用「重红金装饰、强神秘暗示、大量玄学符号、夸张标题、命运恐吓」的视觉风格（引自 PRODUCT.md）。
- **Don't** 使用 `border-left` 或 `border-right` 大于 1px 的彩色侧条纹作为装饰（浅色模式已降为 1px；深色模式保留 2px 仅因其与墨迹意象吻合）。
- **Don't** 在 Session 工作区使用 box-shadow。
- **Don't** 把排盘工作台、规则 JSON、仲裁 schema、模型 prompt 作为普通用户的默认界面。
- **Don't** 使用紫蓝渐变、毛玻璃效果、弹跳/弹性动画等 AI 默认风格。
- **Don't** 使用 cream/sand/warm-neutral 作为浅色模式的「暖感」来源——暖感由 bone 色系的色调倾向承载，而非体感温度。
