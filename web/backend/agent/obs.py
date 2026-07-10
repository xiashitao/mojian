"""外部调用的可观测 span——把「一轮对话里到底调了谁」统一记下来。

每一次「离开本进程去问别人」的调用都记一个 Span:问大模型(kind=llm)、
调工具(kind=tool)、调 MCP server(kind=mcp)、走 HTTP(kind=http)……
一轮 run 里的所有 span 汇入该轮 trace,于是「这轮调了几次模型、每次多久、
花了多少 token、工具调了没、失败在哪」一目了然。

为什么 sink 用显式传参、不用 contextvar:
流式回复在 ASGI 线程池里跨 yield 执行,每次 __next__ 可能换线程/换上下文,
contextvar 里设的值不保证跨 yield 存活——最贵的那次生成 span 会丢。
显式把一个 list 传进调用链则稳定可靠,而且正是将来接 MCP/工具的统一姿势:
每个客户端函数多收一个 `trace_sink` 参数、把 span append 进去即可,
调用链其余部分不用动。emit() 对 sink=None 是无操作,所以不在 run 内
(比如单测直接调网关)时零负担、绝不报错。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# 调用链里显式传递的收集器;元素是 Span。None = 不在被追踪的 run 内。
TraceSink = list


@dataclass
class Span:
    """一次外部调用的记录。attributes 放各 kind 各自的细节(模型/token/工具入参…)。"""

    kind: str  # llm | tool | mcp | http | engine
    name: str  # 如 llm.stream / mcp.<server>.<tool> / tool.bazibase
    ok: bool = True
    latency_ms: int = 0
    attempts: int = 1
    error: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def step_type(self) -> str:
        """写进 run_traces 的 step_type,与既有管线步骤(extract_input 等)并列。"""
        return f"{self.kind}_call"

    def trace_input(self) -> dict[str, Any]:
        return {"name": self.name, "kind": self.kind}

    def trace_output(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ok": self.ok,
            "latency_ms": self.latency_ms,
            "attempts": self.attempts,
        }
        if self.error:
            out["error"] = self.error
        # 丢掉 None 值,trace 里干净些。
        out.update({k: v for k, v in self.attributes.items() if v is not None})
        return out

    def summary(self) -> str:
        head = f"{self.name} {'ok' if self.ok else 'FAIL'} {self.latency_ms}ms"
        tok = self.attributes.get("total_tokens")
        if tok:
            head += f" · {tok}tok"
        if self.attempts > 1:
            head += f" · {self.attempts}次尝试"
        if self.error:
            head += f" · {self.error[:80]}"
        return head


def emit(sink: TraceSink | None, span: Span) -> None:
    """best-effort 记录:不在 run 内(sink=None)则丢弃,append 出错也吞掉——
    可观测性绝不能反过来把主链路搞崩。"""
    if sink is None:
        return
    try:
        sink.append(span)
    except Exception:  # noqa: BLE001 - 记录失败不该影响业务
        pass


def preview(text: str | None, limit: int = 240) -> str:
    """长文本截断预览:留头 + 标注省略了多少字,既能看内容又不撑爆库。"""
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[:limit]}…(+{len(text) - limit})"
