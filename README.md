# bazibase

Deterministic Ba Zi chart casting layer. This is Layer 1 of the mingli agent project — pure algorithmic computation, zero LLM, 100% reproducible.

## Documentation

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 架构总览、三层模型、关键设计决策（真太阳时作用范围、子时边界、旺衰评分权重等）
- **[docs/PROGRESS.md](docs/PROGRESS.md)** — 当前进度、已知限制、下一步路线（Layer 2 规则引擎规划）

## Scope

This package implements the chart casting foundation only:

- Public/datetime to four pillars (年月日时)
- True solar time correction (真太阳时)
- Hidden stems (地支藏干)
- Ten gods labeling (十神)
- Luck pillars (大运)
- Day master strength assessment (日主强弱)

It does NOT do interpretation, prediction, or 用神 selection. Those belong to Layer 2 (rule engine).

## Design principle

Every output must be:

1. **Deterministic** — same input always gives same output
2. **Verifiable** — every rule has a traceable source in 子平真诠 or 破窑赋/渊海子平
3. **Testable** — public historical charts serve as regression tests

## Usage

```python
from datetime import datetime
from bazibase import cast_chart

chart = cast_chart(
    birth_time=datetime(1990, 5, 15, 8, 30),
    longitude=116.4,        # 北京经度
    gender="male",
)
print(chart.to_dict())
```
