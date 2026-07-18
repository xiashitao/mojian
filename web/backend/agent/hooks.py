"""通用 hook 系统:在管线的固定事件点上挂可插拔的拦截器/观察者。

对标 Claude Code 的 hook 模型:
- 事件(event)     管线生命周期的固定节点,见 EVENTS 能力表
- matcher          按事件的关键值(工具名/步骤类型/动作)正则过滤,不匹配不执行
- priority         同事件多个 hook 按 (priority, 注册序) 排序,小者先跑
- 返回值语义       continue(默认)/ block(短路,走拒绝分支)/ patch(改写 payload)
- critical         True: hook 抛异常 = 整个 dispatch 失败;False: 记日志跳过

能力表(EVENTS)是安全边界:每个事件声明了「能不能 block、能 patch 哪些键」,
不在白名单里的 patch 键一律丢弃并告警。这样把「不可碰原则」做进 API 形状——
prompt 稳定前缀没有对应事件、没有可 patch 的键,想违反缓存约束在类型上就做不到。
(将来需要话题侧重段之类的 prompt 注入时,再加一个只允许 append 易变尾部的
pre_prompt 事件,不开放整个 prompt。)

纪律:
- 注册只在启动时(main.py lifespan / 测试 setup);运行期不增删,eval 才可复现;
- 零 hook 注册时 dispatch 是纯空转,管线行为与未接入前一致;
- 观察类事件(on_step/on_span/run_end/post_response)返回 block/patch 会被
  忽略并告警——观测消费者写错了也伤不到主链路。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from .obs import Span

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 事件能力表:block 可否短路、patch 允许改哪些键(空集 = 观察类,只读)。
# 新增事件必须在这里登记,register() 会校验(拼错事件名注册时就炸,不留暗雷)。
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EventCaps:
    can_block: bool = False
    patchable_keys: frozenset[str] = frozenset()


EVENTS: dict[str, EventCaps] = {
    # 拦截类:可 block / 可 patch(白名单键)
    "user_message": EventCaps(can_block=True, patchable_keys=frozenset({"message"})),
    "post_route": EventCaps(can_block=True,
                            patchable_keys=frozenset({"action", "intent", "topic"})),
    "pre_tool": EventCaps(patchable_keys=frozenset({"args"})),
    "post_tool": EventCaps(patchable_keys=frozenset({"result"})),
    # 观察类:只读(post_response 时回复已流式发出,无法收回,故也是观察类)
    "post_response": EventCaps(),
    "on_step": EventCaps(),
    "on_span": EventCaps(),
    "run_end": EventCaps(),
}


@dataclass(frozen=True)
class HookContext:
    """hook 收到的只读视图。payload 是 dispatch 维护的当前值(前序 hook 的
    patch 已生效);想改它请返回 HookResult(action="patch"),别直接改——
    唯一例外是 on_span 的 Span 对象:补写 span.attributes 是该事件的正当
    用法(如 CostMeter 记成本,随 trace 一起落库)。"""

    event: str
    run_id: str
    payload: dict[str, Any]
    match_value: str | None = None


@dataclass(frozen=True)
class HookResult:
    action: Literal["continue", "block", "patch"] = "continue"
    patch: dict[str, Any] | None = None   # action=patch 时的局部覆盖
    reason: str | None = None             # block/patch 建议填,进 tracing/日志


@dataclass(frozen=True)
class HookSpec:
    event: str
    fn: Callable[[HookContext], HookResult | None]  # 返回 None 视同 continue
    name: str = ""              # 空则用函数限定名;进日志和 Outcome.applied
    matcher: str | None = None  # 对 match_value 做 re.search;None = 全匹配
    priority: int = 100         # 小者先跑;同值按注册序
    critical: bool = False      # True: 异常上抛(HookError);False: 记日志跳过


@dataclass(frozen=True)
class Outcome:
    """dispatch 的结果:调用方拿最终 payload 继续,或按 blocked 走拒绝分支。"""

    payload: dict[str, Any]
    blocked: bool = False
    reason: str | None = None
    blocked_by: str | None = None
    applied: tuple[str, ...] = field(default_factory=tuple)  # 实际执行过的 hook 名


class HookError(Exception):
    """critical hook 失败。调用方(管线)按普通异常处理——走 error 分支。"""


_HOOKS: list[HookSpec] = []


def register(spec: HookSpec) -> None:
    """启动时注册。事件名/matcher 立刻校验,坏配置当场炸而不是运行时哑火。"""
    if spec.event not in EVENTS:
        raise ValueError(f"unknown hook event: {spec.event!r} "
                         f"(known: {sorted(EVENTS)})")
    if spec.matcher is not None:
        re.compile(spec.matcher)  # 坏正则在注册时报错
    if not spec.name:
        spec = HookSpec(event=spec.event, fn=spec.fn,
                        name=getattr(spec.fn, "__qualname__", repr(spec.fn)),
                        matcher=spec.matcher, priority=spec.priority,
                        critical=spec.critical)
    _HOOKS.append(spec)


def reset() -> None:
    """清空注册表——仅供测试隔离用。"""
    _HOOKS.clear()


def registered(event: str | None = None) -> list[HookSpec]:
    """当前注册的 hook(可按事件过滤),排序同执行序:(priority, 注册序)。"""
    indexed = [(s.priority, i, s) for i, s in enumerate(_HOOKS)
               if event is None or s.event == event]
    return [s for _, _, s in sorted(indexed, key=lambda t: (t[0], t[1]))]


def dispatch(
    event: str,
    payload: dict[str, Any],
    *,
    run_id: str = "",
    match_value: str | None = None,
) -> Outcome:
    """按序执行一个事件上的所有 hook,返回最终 payload / block 结论。

    - payload 按值传递语义:内部用浅拷贝工作,调用方传入的 dict 不被改动;
    - patch 链式生效:后一个 hook 看到的是前一个 patch 后的 payload;
    - block 短路:命中即返回,后续 hook 不执行;
    - 观察类事件的 block/patch 被忽略并告警(见模块 docstring)。
    """
    caps = EVENTS.get(event)
    if caps is None:
        raise ValueError(f"unknown hook event: {event!r}")

    current = dict(payload)
    applied: list[str] = []

    for spec in registered(event):
        if spec.matcher is not None and not re.search(spec.matcher, match_value or ""):
            continue
        ctx = HookContext(event=event, run_id=run_id,
                          payload=current, match_value=match_value)
        try:
            result = spec.fn(ctx) or HookResult()
        except Exception as e:  # noqa: BLE001
            if spec.critical:
                raise HookError(f"critical hook {spec.name} failed on {event}: {e}") from e
            log.warning("hook %s failed on %s (skipped)", spec.name, event,
                        exc_info=True)
            continue
        applied.append(spec.name)

        if result.action == "block":
            if not caps.can_block:
                log.warning("hook %s tried to block observe-only event %s (ignored)",
                            spec.name, event)
                continue
            return Outcome(payload=current, blocked=True,
                           reason=result.reason, blocked_by=spec.name,
                           applied=tuple(applied))

        if result.action == "patch":
            patch = result.patch or {}
            allowed = {k: v for k, v in patch.items() if k in caps.patchable_keys}
            dropped = set(patch) - set(allowed)
            if dropped:
                log.warning("hook %s patch keys %s not allowed on %s (dropped)",
                            spec.name, sorted(dropped), event)
            if allowed:
                current = {**current, **allowed}

    return Outcome(payload=current, applied=tuple(applied))


# ---------------------------------------------------------------------------
# run 聚合视图(run_end 事件的 payload 内容)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RunSummary:
    """一轮 run 的聚合。models:按模型分桶 {model: {calls, prompt_tokens,
    completion_tokens, cost}};cost 单位元(CNY),None = 无定价。"""

    run_id: str
    conversation_id: str
    status: str
    error: str | None
    latency_ms: int
    llm_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float | None
    models: dict[str, dict[str, Any]] = field(default_factory=dict)


def summarize_run(
    *,
    run_id: str,
    conversation_id: str,
    status: str,
    error: str | None,
    latency_ms: int,
    spans: list[Span],
) -> RunSummary:
    """从一轮的 span 列表聚合 RunSummary(只统计 kind=llm)。

    cost 来自 span.attributes["cost"](CostMeter 在 on_span 里补写);没有
    CostMeter 或模型无定价时为 None,聚合时跳过而不是当 0——不知道就说不知道。
    """
    llm_calls = 0
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cost_sum = 0.0
    cost_known = False
    models: dict[str, dict[str, Any]] = {}

    for span in spans:
        if span.kind != "llm":
            continue
        llm_calls += 1
        attrs = span.attributes
        prompt_tokens += attrs.get("prompt_tokens") or 0
        completion_tokens += attrs.get("completion_tokens") or 0
        total_tokens += attrs.get("total_tokens") or 0

        model = attrs.get("model") or "unknown"
        bucket = models.setdefault(model, {
            "calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "cost": None,
        })
        bucket["calls"] += 1
        bucket["prompt_tokens"] += attrs.get("prompt_tokens") or 0
        bucket["completion_tokens"] += attrs.get("completion_tokens") or 0

        span_cost = attrs.get("cost")
        if span_cost is not None:
            cost_known = True
            cost_sum += span_cost
            bucket["cost"] = (bucket["cost"] or 0.0) + span_cost

    return RunSummary(
        run_id=run_id,
        conversation_id=conversation_id,
        status=status,
        error=error,
        latency_ms=latency_ms,
        llm_calls=llm_calls,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost=round(cost_sum, 6) if cost_known else None,
        models=models,
    )
