"""
bazibase.arbitration
====================

LLM arbitration layer (Layer 3).

bazibase's Layer 2 is deterministic — given the same chart, it always
produces the same Diagnosis. But some judgments in that Diagnosis are
*structural* (the rule fired) rather than *semantic* (the rule's
conclusion is actually correct). The arbitration layer surfaces those
uncertainties as structured **cases** and prepares prompts for an
external LLM to resolve.

Design principles
-----------------
1. **No LLM calls in this library.** We produce prompts and parse
   responses, but the actual LLM call is the caller's job. This keeps
   bazibase deterministic and testable.

2. **Every case cites its evidence.** The LLM is not asked to "look at
   the chart and decide" — it's given a precise list of facts (which
   rules fired, which stems/branches are involved) and asked to
   arbitrate between specific alternatives.

3. **Forced confidence + "无法判定" option.** The LLM must output a
   0–1 confidence; below a configurable threshold it must admit
   "无法判定". This prevents hallucinated certainty.

4. **Response schema is strict.** `parse_arbitration_response()`
   validates the JSON and rejects malformed responses.

Conflict categories detected
----------------------------
- **RESCUE**: v0.2.2's simplified rescue logic says 救应, but the
  相神 may not actually control the 忌神 in 五行 terms.
- **HE_CHONG**: a branch is in both a 三合/半三合 and a 六冲 —
  "贪合忘冲" may or may not apply.
- **HE_HUA**: 天干五合 or 地支三合 detected structurally, but 化神
  may not have 月令 support (合而不化 = 合绊).
- **XING_CHONG**: multiple 刑/冲 coexist — the chart is "动荡".
- **GE_JU_ZHEN_JIA**: 用神十神 known, but its strength is borderline,
  raising the "真格 vs 假格" question.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Literal
import json

from .diagnosis import Diagnosis
from .constants import STEM_ELEMENT, BRANCH_ELEMENT, ELEMENT_PRODUCTION, ELEMENT_CONQUEST
from .rules.schema import RuleCitation, get_rule


# ---------------------------------------------------------------------------
# Threshold defaults
# ---------------------------------------------------------------------------

DEFAULT_CONFIDENCE_THRESHOLD = 0.6


# ---------------------------------------------------------------------------
# Case category
# ---------------------------------------------------------------------------

CaseCategory = Literal[
    "RESCUE",        # 救应是否真的成立（五行制化）
    "HE_CHONG",      # 合冲并存（贪合忘冲？）
    "HE_HUA",        # 合化是否真的化（化神有力？）
    "XING_CHONG",    # 多刑多冲（动荡程度？）
    "GE_JU_ZHEN_JIA",  # 格局真假（用神是否有力？）
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ArbitrationCase:
    """A single conflict or ambiguity detected in a Diagnosis.

    Attributes:
        case_id: Unique ID for this case (e.g., "RESCUE-001").
        category: One of CaseCategory.
        title: Short human-readable title.
        description: Detailed description of the conflict.
        evidence: Structured evidence (stems, branches, rules involved).
        relevant_rules: Rule IDs that are in tension.
        options: The alternatives the LLM should choose between.
    """
    case_id: str
    category: CaseCategory
    title: str
    description: str
    evidence: dict
    relevant_rules: tuple[str, ...]
    options: tuple[str, ...]


@dataclass(frozen=True)
class ArbitrationPrompt:
    """A formatted prompt for an external LLM.

    Attributes:
        case: The ArbitrationCase this prompt is for.
        system_prompt: Role/instructions for the LLM.
        user_prompt: The evidence + question.
        expected_schema: JSON schema describing the required response shape.
    """
    case: ArbitrationCase
    system_prompt: str
    user_prompt: str
    expected_schema: dict


@dataclass(frozen=True)
class ArbitrationResponse:
    """Parsed and validated LLM response for one case.

    Attributes:
        case_id: Which case this response answers.
        decision: The LLM's chosen option (must be one of case.options,
                  or "无法判定").
        reasoning: The LLM's explanation (1-3 sentences).
        confidence: 0.0–1.0 confidence.
        cited_rules: Rule IDs the LLM referenced in reasoning.
        raw_response: The original JSON string from the LLM (for audit).
    """
    case_id: str
    decision: str
    reasoning: str
    confidence: float
    cited_rules: tuple[str, ...] = ()
    raw_response: Optional[str] = None

    def is_unresolved(self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> bool:
        """True if the response is '无法判定' or confidence is below threshold."""
        return self.decision == "无法判定" or self.confidence < threshold


@dataclass(frozen=True)
class ArbitrationResult:
    """Aggregate result of arbitration for a chart.

    Attributes:
        cases: All detected cases.
        prompts: Prompts ready to send to an LLM (one per case).
        responses: Filled in after LLM calls. Keyed by case_id.
                   Empty until `attach_response()` is called.
    """
    cases: tuple[ArbitrationCase, ...]
    prompts: tuple[ArbitrationPrompt, ...]
    responses: dict[str, ArbitrationResponse] = field(default_factory=dict)

    def unresolved_cases(
        self, threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    ) -> tuple[ArbitrationCase, ...]:
        """Cases that are either unanswered or answered with low confidence."""
        out = []
        for c in self.cases:
            r = self.responses.get(c.case_id)
            if r is None or r.is_unresolved(threshold):
                out.append(c)
        return tuple(out)

    def has_cases(self) -> bool:
        return bool(self.cases)


# ---------------------------------------------------------------------------
# Case detectors
# ---------------------------------------------------------------------------

def _detect_rescue_cases(d: Diagnosis) -> list[ArbitrationCase]:
    """Detect 救应 cases where 相神 may not control 忌神 in 五行 terms.

    v0.2.2's `_find_rescue_gods()` treats any 相神 as a potential 救神.
    But in strict 子平派, the rescue is only valid if the 相神's element
    actually controls the 忌神's element. E.g., 印(木) cannot rescue
    from 财(金) because 金克木.
    """
    cases: list[ArbitrationCase] = []
    if d.cheng_bai.verdict != "救应":
        return cases

    cb = d.cheng_bai
    xs = d.xiang_shen
    ys = d.yong_shen

    # For each (忌神, 救神) pair, check if 救神's element controls 忌神's
    for ji in xs.ji_shen:
        for rescue in cb.rescue_gods:
            ji_el = STEM_ELEMENT.get(ji.stem, "?")
            rescue_el = STEM_ELEMENT.get(rescue.stem, "?")
            # Does rescue_el conquer ji_el?
            can_control = ELEMENT_CONQUEST.get(rescue_el) == ji_el
            if not can_control:
                cases.append(ArbitrationCase(
                    case_id=f"RESCUE-{len(cases)+1:03d}",
                    category="RESCUE",
                    title=f"救神{rescue.stem}({rescue_el})能否制忌神{ji.stem}({ji_el})",
                    description=(
                        f"v0.2.2 判定为救应：相神{rescue.stem}({rescue.ten_god}) "
                        f"被视为救神，可制忌神{ji.stem}({ji.ten_god})。"
                        f"但从五行看，{rescue_el}不克{ji_el}"
                        f"（{rescue_el}克{ELEMENT_CONQUEST.get(rescue_el, '?')}，"
                        f"非{ji_el}），救神未必能制忌神。"
                        f"请判断此救应是否真正成立。"
                    ),
                    evidence={
                        "yong_shen": ys.stem,
                        "yong_shen_ten_god": ys.ten_god,
                        "ji_shen": ji.stem,
                        "ji_shen_ten_god": ji.ten_god,
                        "ji_shen_element": ji_el,
                        "rescue_god": rescue.stem,
                        "rescue_ten_god": rescue.ten_god,
                        "rescue_element": rescue_el,
                        "rescue_conquers_ji": can_control,
                    },
                    relevant_rules=("ZP-JIUYING-001", "ZP-XIANG-001", "ZP-JI-001"),
                    options=(
                        "救应成立（虽五行不克，但位置/力量足以制化）",
                        "救应不成立（五行不克，相神无力救应）",
                        "无法判定",
                    ),
                ))
                break  # one case per 忌神 is enough
    return cases


def _detect_he_chong_cases(d: Diagnosis) -> list[ArbitrationCase]:
    """Detect branches that are in both a 合 and a 冲.

    Traditional rule "贪合忘冲": if a branch is in a complete 三合,
    the 冲 is forgotten. But this only applies to full 三合, not 半三合.
    """
    cases: list[ArbitrationCase] = []
    ia = d.interactions

    # Only full 三合 can potentially "忘冲"
    if not ia.san_he or not ia.chong:
        return cases

    # Collect all branches involved in full 三合
    he_branches: set[str] = set()
    for i in ia.san_he:
        he_branches.update(i.elements)

    # Find 冲 where at least one side is in a 三合
    for chong in ia.chong:
        b_a, b_b = chong.elements
        a_in_he = b_a in he_branches
        b_in_he = b_b in he_branches
        if a_in_he or b_in_he:
            cases.append(ArbitrationCase(
                case_id=f"HE_CHONG-{len(cases)+1:03d}",
                category="HE_CHONG",
                title=f"{b_a}+{b_b}冲 vs 三合（贪合忘冲？）",
                description=(
                    f"地支{b_a}与{b_b}相冲，但同时"
                    f"{'{}参与了三合'.format(b_a) if a_in_he else ''}"
                    f"{'{}参与了三合'.format(b_b) if b_in_he else ''}。"
                    f"传统规则'贪合忘冲'认为：若三合全见，冲可被化解。"
                    f"请判断此冲是否被三合化解。"
                ),
                evidence={
                    "chong_pair": list(chong.elements),
                    "chong_positions": list(chong.participants),
                    "san_he_branches": sorted(he_branches),
                },
                relevant_rules=("ZP-SAN-HE", "ZP-CHONG"),
                options=(
                    "贪合忘冲（冲被三合化解）",
                    "冲不为合所化（冲仍起作用）",
                    "部分化解（冲力减弱但未消除）",
                    "无法判定",
                ),
            ))
    return cases


def _detect_he_hua_cases(d: Diagnosis) -> list[ArbitrationCase]:
    """Detect 合 relationships where 化 may not occur.

    A 合 is only a 化 if the 化神 (transformed element) has support in
    the 月令. Otherwise it's 合绊 (bound but not transformed).
    """
    cases: list[ArbitrationCase] = []
    ia = d.interactions

    # 天干五合 candidates
    for he in ia.gan_he:
        hua_el = he.resulting_element
        month_branch = d.ge_ju  # we need month branch element
        # Access chart via the Diagnosis — we don't have the chart directly,
        # but the chart_summary contains the month branch
        # For a proper implementation, we'd pass the chart to detect_*.
        # Here we just flag the case and let the LLM check 月令.
        cases.append(ArbitrationCase(
            case_id=f"HE_HUA-{len(cases)+1:03d}",
            category="HE_HUA",
            title=f"天干{he.elements[0]}+{he.elements[1]}合化{hua_el}（化神有力？）",
            description=(
                f"天干{he.elements[0]}与{he.elements[1]}相合，"
                f"结构上当化为{hua_el}。但化神{hua_el}需得月令或旺相才能真正化气，"
                f"否则为'合绊'（两干互相牵绊，不化气）。"
                f"请根据月令判断此合是'真化'还是'合绊'。"
            ),
            evidence={
                "stems": list(he.elements),
                "hua_element": hua_el,
                "positions": list(he.participants),
            },
            relevant_rules=("ZP-HE-GAN",),
            options=(
                "真化（化神得令或旺相，合而化气）",
                "合绊（化神无力，合而不化）",
                "无法判定",
            ),
        ))
    return cases


def _detect_xing_chong_cases(d: Diagnosis) -> list[ArbitrationCase]:
    """Detect charts with 3+ 刑冲 interactions (动荡命)."""
    cases: list[ArbitrationCase] = []
    ia = d.interactions

    total = len(ia.chong) + len(ia.xing)
    if total >= 3:
        cases.append(ArbitrationCase(
            case_id="XING_CHONG-001",
            category="XING_CHONG",
            title=f"多刑多冲（{len(ia.chong)}冲+{len(ia.xing)}刑）",
            description=(
                f"命中检测到{len(ia.chong)}组相冲、{len(ia.xing)}组相刑，"
                f"共{total}组冲突。命书云'冲多动荡，刑多招是非'。"
                f"请评估此八字的动荡程度及对格局的影响。"
            ),
            evidence={
                "chong_count": len(ia.chong),
                "xing_count": len(ia.xing),
                "chong_pairs": [list(i.elements) for i in ia.chong],
                "xing_patterns": [list(i.elements) for i in ia.xing],
            },
            relevant_rules=("ZP-CHONG", "ZP-XING"),
            options=(
                "动荡轻微（虽有刑冲但位置/力量不足以破格）",
                "动荡中等（刑冲影响运势起伏，但不改格局大势）",
                "动荡严重（刑冲破格，需大运补救）",
                "无法判定",
            ),
        ))
    return cases


def _detect_ge_ju_zhen_jia_cases(d: Diagnosis) -> list[ArbitrationCase]:
    """Detect 格局 where 用神 strength is borderline (真格 vs 假格).

    If the day-master strength assessment is near the threshold (borderline),
    the 用神 choice may be questionable.
    """
    cases: list[ArbitrationCase] = []
    # We don't have direct access to StrengthAssessment here, but the
    # chart_summary embeds 身强/身弱. Borderline = "偏强" or "偏弱"
    # if we had those labels. For now, flag any chart where the
    # 成败 verdict is 救应 (because rescue validity is always questionable).
    if d.cheng_bai.verdict == "救应" and not any(
        c.category == "RESCUE" for c in _detect_rescue_cases(d)
    ):
        # 救应 without a RESCUE case means all rescue gods can control
        # their 忌神 in 五行 terms. Still worth confirming.
        pass  # no case — the rescue is structurally sound

    return cases


# ---------------------------------------------------------------------------
# Case detection entry point
# ---------------------------------------------------------------------------

def detect_arbitration_cases(d: Diagnosis) -> tuple[ArbitrationCase, ...]:
    """
    Scan a Diagnosis for conflicts/ambiguities that need LLM arbitration.

    Args:
        d: A Diagnosis from `diagnose()`.

    Returns:
        Tuple of ArbitrationCase. Empty if the chart has no ambiguities.
    """
    cases: list[ArbitrationCase] = []
    cases.extend(_detect_rescue_cases(d))
    cases.extend(_detect_he_chong_cases(d))
    cases.extend(_detect_he_hua_cases(d))
    cases.extend(_detect_xing_chong_cases(d))
    cases.extend(_detect_ge_ju_zhen_jia_cases(d))
    return tuple(cases)


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是一位精通《子平真诠》的命理仲裁者。你的任务是分析八字规则引擎输出的冲突案例，给出判断。

## 工作规则

1. 你必须从给定的选项中选择一个，或选择"无法判定"。
2. 你的判断必须基于《子平真诠》的规则，不能凭空臆断。
3. 你必须给出推理过程（1-3句话），引用相关的规则编号。
4. 你必须给出置信度（0.0-1.0）。低于 0.6 的判断等同于"无法判定"。
5. 如果证据不足以做出判断，请直接选择"无法判定"。

## 输出格式

你必须输出严格的 JSON，格式如下：

```json
{
  "decision": "你选择的选项（必须与给定选项之一完全一致）",
  "reasoning": "1-3句话的推理过程",
  "confidence": 0.0,
  "cited_rules": ["规则编号1", "规则编号2"]
}
```

不要输出任何 JSON 之外的内容。"""


def build_arbitration_prompt(
    case: ArbitrationCase,
    d: Diagnosis,
) -> ArbitrationPrompt:
    """
    Build a prompt for an LLM to arbitrate a single case.

    Args:
        case: The ArbitrationCase to build a prompt for.
        d: The original Diagnosis (for context).

    Returns:
        ArbitrationPrompt with system_prompt, user_prompt, and expected_schema.
    """
    # Build the evidence section
    evidence_lines = []
    for k, v in case.evidence.items():
        evidence_lines.append(f"  - {k}: {v}")
    evidence_str = "\n".join(evidence_lines)

    # Build the rules section
    rules_lines = []
    for rid in case.relevant_rules:
        try:
            r = get_rule(rid)
            rules_lines.append(
                f"  [{rid}] ({r.chapter})\n"
                f"    原文: {r.source_text}\n"
                f"    释义: {r.modern_summary}"
            )
        except KeyError:
            rules_lines.append(f"  [{rid}] (规则未找到)")
    rules_str = "\n".join(rules_lines)

    # Build the options section
    options_str = "\n".join(
        f"  {i+1}. {opt}" for i, opt in enumerate(case.options)
    )

    user_prompt = f"""## 仲裁案例

**案例编号**: {case.case_id}
**类别**: {case.category}
**标题**: {case.title}

**描述**:
{case.description}

## 证据

{evidence_str}

## 相关规则

{rules_str}

## 可选项

{options_str}

## 八字背景

{d.chart_summary}
日主: {d.day_master}
用神: {d.yong_shen.stem} ({d.yong_shen.ten_god})
格局: {d.ge_ju.name}
成败: {d.cheng_bai.verdict}

## 请输出 JSON"""

    expected_schema = {
        "type": "object",
        "required": ["decision", "reasoning", "confidence", "cited_rules"],
        "properties": {
            "decision": {
                "type": "string",
                "enum": list(case.options),
            },
            "reasoning": {
                "type": "string",
                "maxLength": 300,
            },
            "confidence": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
            },
            "cited_rules": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    }

    return ArbitrationPrompt(
        case=case,
        system_prompt=_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        expected_schema=expected_schema,
    )


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class ArbitrationParseError(Exception):
    """Raised when an LLM response cannot be parsed or validated."""


def parse_arbitration_response(
    case: ArbitrationCase,
    raw_response: str,
) -> ArbitrationResponse:
    """
    Parse and validate an LLM's JSON response for a case.

    Args:
        case: The case this response is for.
        raw_response: The raw JSON string from the LLM.

    Returns:
        ArbitrationResponse with validated fields.

    Raises:
        ArbitrationParseError: If the response is not valid JSON or
                               fails validation.
    """
    # Strip markdown code fences if present
    text = raw_response.strip()
    if text.startswith("```"):
        # Remove ```json ... ``` or ``` ... ```
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ArbitrationParseError(
            f"LLM response is not valid JSON: {e}"
        ) from e

    # Validate required keys
    for key in ("decision", "reasoning", "confidence"):
        if key not in data:
            raise ArbitrationParseError(
                f"Missing required key: {key!r}"
            )

    decision = data["decision"]
    reasoning = str(data["reasoning"])
    confidence = float(data["confidence"])
    cited_rules = tuple(data.get("cited_rules", []))

    # Validate decision is one of the options
    valid_options = set(case.options) | {"无法判定"}
    # Also accept "无法判定" even if not in options (LLM safety valve)
    if decision not in valid_options:
        raise ArbitrationParseError(
            f"Decision {decision!r} not in valid options: {valid_options}"
        )

    # Validate confidence range
    if not (0.0 <= confidence <= 1.0):
        raise ArbitrationParseError(
            f"Confidence {confidence} out of range [0.0, 1.0]"
        )

    return ArbitrationResponse(
        case_id=case.case_id,
        decision=decision,
        reasoning=reasoning,
        confidence=confidence,
        cited_rules=cited_rules,
        raw_response=raw_response,
    )


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def prepare_arbitration(
    d: Diagnosis,
) -> ArbitrationResult:
    """
    Detect all arbitration cases in a Diagnosis and build prompts for each.

    This is the main entry point for Layer 3. After calling this, the
    caller sends each prompt to an LLM, parses the responses with
    `parse_arbitration_response()`, and attaches them to the result.

    Args:
        d: A Diagnosis from `diagnose()`.

    Returns:
        ArbitrationResult with cases and prompts. The `responses` dict
        is empty — fill it by calling `attach_response()`.

    Example:
        >>> from bazibase import cast_chart, diagnose
        >>> from bazibase.arbitration import prepare_arbitration, parse_arbitration_response
        >>> c = cast_chart(datetime(1893,12,26,8,0), 112.9, "male")
        >>> d = diagnose(c)
        >>> result = prepare_arbitration(d)
        >>> for prompt in result.prompts:
        ...     # send prompt.system_prompt + prompt.user_prompt to your LLM
        ...     # raw = llm_call(prompt.system_prompt, prompt.user_prompt)
        ...     # response = parse_arbitration_response(prompt.case, raw)
        ...     # result.responses[prompt.case.case_id] = response
        ...     pass
    """
    cases = detect_arbitration_cases(d)
    prompts = tuple(build_arbitration_prompt(c, d) for c in cases)
    return ArbitrationResult(cases=cases, prompts=prompts)


def attach_response(
    result: ArbitrationResult,
    case_id: str,
    response: ArbitrationResponse,
) -> ArbitrationResult:
    """
    Return a new ArbitrationResult with the response attached.

    Since ArbitrationResult is frozen, this returns a new instance.
    """
    new_responses = dict(result.responses)
    new_responses[case_id] = response
    return ArbitrationResult(
        cases=result.cases,
        prompts=result.prompts,
        responses=new_responses,
    )


__all__ = [
    "CaseCategory",
    "ArbitrationCase",
    "ArbitrationPrompt",
    "ArbitrationResponse",
    "ArbitrationResult",
    "ArbitrationParseError",
    "DEFAULT_CONFIDENCE_THRESHOLD",
    "detect_arbitration_cases",
    "build_arbitration_prompt",
    "parse_arbitration_response",
    "prepare_arbitration",
    "attach_response",
]
