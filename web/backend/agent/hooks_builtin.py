"""内置 hook:成本统计(CostMeter)+ 结构化日志(StructuredLog)。

两者都是观察类消费者,挂在 on_span / on_step / run_end 事件上。
main.py 的 lifespan 里 setup_default_hooks() 一次性注册;
测试/eval 直接调 planner 时不注册——hook 空转,零行为差异。
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..config import WEB_DIR
from . import hooks, repository
from .hooks import HookContext, HookSpec

# 定价表:元(CNY)/百万 token,(输入, 输出)。按「记录时定价」使用——cost 在
# span 落库那刻算好存死,日后调价只改这张表,历史数据不动。
# 注意:输入按缓存未命中价计(我们不追踪 cache hit 细分),所以是保守上界。
# 模型不在表里 → cost 记 None(不知道就说不知道,别拿 0 冒充)。
PRICING: dict[str, tuple[float, float]] = {
    "deepseek-chat": (2.0, 8.0),
    "deepseek-reasoner": (4.0, 16.0),
}


def compute_cost(model: str | None, prompt_tokens: int | None,
                 completion_tokens: int | None) -> float | None:
    """一次 LLM 调用的成本(元);模型无定价或 token 数缺失时返回 None。"""
    if not model or model not in PRICING:
        return None
    if prompt_tokens is None or completion_tokens is None:
        return None
    price_in, price_out = PRICING[model]
    return (prompt_tokens * price_in + completion_tokens * price_out) / 1_000_000


class CostMeter:
    """成本统计:on_span 给每次 LLM 调用补写 cost(随 trace 落库),
    run_end 把整轮聚合写进 run_costs 表(报表从这张表出)。"""

    def on_span(self, ctx: HookContext) -> None:
        span = ctx.payload["span"]
        if span.kind != "llm":
            return
        attrs = span.attributes
        cost = compute_cost(attrs.get("model"), attrs.get("prompt_tokens"),
                            attrs.get("completion_tokens"))
        if cost is not None:
            attrs["cost"] = round(cost, 6)

    def on_run_end(self, ctx: HookContext) -> None:
        summary = ctx.payload["summary"]
        if summary.llm_calls == 0:
            return  # 纯模板轮(smalltalk 降级等)没有 LLM 开销,不占表
        repository.add_run_cost(
            summary.run_id,
            summary.conversation_id,
            llm_calls=summary.llm_calls,
            prompt_tokens=summary.prompt_tokens,
            completion_tokens=summary.completion_tokens,
            total_tokens=summary.total_tokens,
            cost=summary.cost,
            models=summary.models,
        )


class StructuredLog:
    """结构化日志:每个事件一行 JSON 追加到 jsonl 文件,排查 = grep/jq 按
    run_id 或 error 过滤。不做轮转(单机量小;真涨到碍事再说)。"""

    def __init__(self, path: Path | None = None):
        self.path = path or (WEB_DIR / "logs" / "agent.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, record: dict[str, Any]) -> None:
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def on_step(self, ctx: HookContext) -> None:
        self._write({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": "step",
            "run_id": ctx.run_id,
            "step_type": ctx.payload.get("step_type"),
            "step_index": ctx.payload.get("step_index"),
            "summary": ctx.payload.get("summary"),
        })

    def on_run_end(self, ctx: HookContext) -> None:
        summary = ctx.payload["summary"]
        self._write({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": "run_end",
            "run_id": summary.run_id,
            "conversation_id": summary.conversation_id,
            "status": summary.status,
            "error": summary.error,
            "latency_ms": summary.latency_ms,
            "llm_calls": summary.llm_calls,
            "total_tokens": summary.total_tokens,
            "cost": summary.cost,
        })


def setup_default_hooks() -> None:
    """注册默认 hook(main.py lifespan 调用,进程生命周期内一次)。"""
    meter = CostMeter()
    slog = StructuredLog()
    hooks.register(HookSpec(event="on_span", fn=meter.on_span, name="cost_meter.span"))
    hooks.register(HookSpec(event="run_end", fn=meter.on_run_end, name="cost_meter.run"))
    hooks.register(HookSpec(event="on_step", fn=slog.on_step, name="structured_log.step"))
    hooks.register(HookSpec(event="run_end", fn=slog.on_run_end, name="structured_log.run"))
