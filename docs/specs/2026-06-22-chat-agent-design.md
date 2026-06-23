# bazibase Chat Agent Design

Date: 2026-06-22

## Goal

Build a chat-first Ba Zi consultation agent on top of `bazibase`.

The first version should feel like a lightweight consultation assistant for ordinary users, not a chart calculator. `bazibase` remains the deterministic foundation for chart casting, diagnosis, rule citations, and arbitration. The agent layer handles conversation, missing information, user-facing phrasing, and operational traceability.

## Product Positioning

The MVP is:

- Topic-driven and question-driven.
- Consultation-first for ordinary users.
- Lightly professional in wording, without exposing full rule chains in the main answer.
- Traceable for operations and internal review.
- Primarily grounded in the original text and rule system of 《子平真诠》, with 《滴天髓》 used as a secondary interpretive reference.

The MVP supports these topics:

- Career / work / entrepreneurship.
- Relationship / marriage.
- Wealth / money-making style.
- Personality / strengths and weaknesses.

The MVP does not support:

- Health or disease analysis.
- Detailed annual luck / yearly prediction.
- Multi-school comparison.
- Fully autonomous long-horizon planning.
- Absolute predictions such as guaranteed wealth, divorce, failure, or success.

## Source Authority

The analysis follows a strict source hierarchy:

1. 《子平真诠》 is the primary authority for chart structure, useful god selection, pattern diagnosis, pattern success/failure, and rule citations.
2. 《滴天髓》 can be used as a secondary reference for interpretive language, temperament, image-based explanation, and broad tendency cross-checking.
3. 《滴天髓》 must not override a deterministic `bazibase` diagnosis based on 《子平真诠》.
4. If the two sources suggest different interpretive emphasis, the user-facing answer should stay conservative and the operations trace should record the source tension.

Ordinary user replies can mention the source stance lightly:

```text
这个判断主要按《子平真诠》的格局和用神逻辑来看，同时参考《滴天髓》对气势和性情的理解。
```

Operations trace should record source usage explicitly:

```json
{
  "primary_source": "子平真诠",
  "secondary_sources": ["滴天髓"],
  "source_tensions": []
}
```

## User Experience

Users interact through chat. They can start with a direct question:

```text
我适合创业吗？
```

If birth information is missing, the agent asks naturally for the minimum required fields:

```text
我可以帮你看事业方向。为了分析，需要先确认四个信息：出生年月日、出生时间、出生地、性别。你可以直接一句话告诉我。
```

When enough information is available, the agent silently calls the `bazibase` tools and answers only the user's topic. It does not dump a full chart report.

Each assistant reply includes a user-visible analysis ID, including replies that only ask for missing information:

```text
分析 ID：BAZI-K7P4Q9
```

The user can give this ID to operations. Operations can search it to retrieve the exact answer, surrounding conversation, extracted birth data, chart, diagnosis, arbitration, prompts, raw LLM outputs, and trace steps.

## Frontend and Backend Surfaces

### User Chat

The user-facing chat shows:

- Conversation messages.
- Assistant reply.
- Suggested follow-up questions.
- Analysis ID for each assistant reply.

It should not show:

- Full `chart.to_dict()`.
- Full `diagnosis.to_dict()`.
- Rule citations by default.
- LLM raw prompts.
- Arbitration internals.

### Operations Backend

The operations backend supports searching by `analysis_id`.

The detail view should show:

- The user question for that analysis.
- The assistant reply.
- Previous and following messages in the same conversation.
- Extracted birth information.
- `chart` JSON.
- `diagnosis` JSON.
- Arbitration cases and responses.
- LLM prompts and raw responses.
- Model, latency, status, and errors.

## Identity and Trace Model

Use separate IDs for different concerns:

- `conversation_id`: one chat thread. Saved by the frontend and sent with every chat request.
- `message_id`: one user, assistant, or system message. Internal.
- `run_id`: one agent execution triggered by a user message. Internal.
- `analysis_id`: one public ID for an assistant reply and its agent run. User-visible and searchable by operations.

Do not expose `conversation_id`, `message_id`, or `run_id` as support identifiers. Use `analysis_id` for support and operations.

`analysis_id` must be random enough to avoid enumeration. It should not be an auto-incrementing ID. Examples:

```text
BAZI-K7P4Q9
BAZI-01JZ8M6B8XQ2
```

## Data Model

### conversations

Stores one chat thread.

```text
id
user_id
title
status
created_at
updated_at
last_message_at
metadata_json
```

`user_id` can be nullable for anonymous MVP usage.

### messages

Stores user-visible and system messages.

```text
id
conversation_id
role
content
analysis_id
created_at
metadata_json
```

`role` is one of:

```text
user
assistant
system
```

`analysis_id` is usually null for user messages and present for assistant messages.

### agent_runs

Stores one agent execution triggered by a user message.

```text
id
conversation_id
trigger_message_id
assistant_message_id
public_analysis_id
status
intent
topic
model
started_at
finished_at
latency_ms
error
metadata_json
```

`status` is one of:

```text
success
failed
partial
```

### run_traces

Stores step-by-step execution traces for audit.

```text
id
run_id
step_index
step_type
input_json
output_json
summary
created_at
```

`step_type` is one of:

```text
extract_input
merge_session_state
cast_chart
diagnose
prepare_arbitration
call_arbitration_llm
generate_reply
persist_state
error
```

## Chat API

### POST /api/chat

Request:

```json
{
  "conversation_id": "conv_xxx",
  "message": "我是1990年5月15日早上8点半北京出生，男，想看事业"
}
```

`conversation_id` is optional. If omitted, the backend creates a new conversation.

Response:

```json
{
  "conversation_id": "conv_xxx",
  "analysis_id": "BAZI-K7P4Q9",
  "reply": "你不是完全不适合创业，但更适合...",
  "state": {
    "topic": "career",
    "needs_more_info": false,
    "missing_fields": [],
    "suggested_followups": [
      "我适合什么行业？",
      "适合单干还是合伙？"
    ]
  }
}
```

### GET /api/admin/analyses/{analysis_id}

Returns the operational audit package for one analysis.

The response includes:

```text
analysis
conversation
messages
agent_run
run_traces
chart
diagnosis
arbitration
llm raw inputs and outputs
```

Access to this endpoint must be restricted to operations or internal users.

## Agent Decision Logic

Use a deterministic state machine for the MVP.

```text
receive user message
  -> create or load conversation
  -> save user message
  -> create agent_run + analysis_id
  -> identify intent and topic
  -> extract birth info
  -> merge with conversation state
  -> if required info is missing: ask a focused follow-up question
  -> if required info is complete:
       cast_chart
       diagnose
       prepare_arbitration
       call arbitration LLM only when cases exist and an LLM provider is configured
       generate user-facing reply
  -> save assistant message
  -> save run traces
  -> return reply + analysis_id
```

## Intent and Topic Schema

Supported intents:

```text
collect_birth_info
career
relationship
wealth
personality
clarify_previous
unknown
```

Supported topics:

```text
career
relationship
wealth
personality
```

Examples:

- "我适合创业吗？" -> `intent=career`, `topic=career`
- "那感情呢？" -> `intent=relationship`, `topic=relationship`, reuse current chart
- "为什么这么说？" -> `intent=clarify_previous`, reuse previous analysis context
- "我是1990年5月15日早上8点半北京出生，男" -> `intent=collect_birth_info`

## Birth Information Extraction

The agent extracts structured birth information from natural language.

Target schema:

```json
{
  "birth_date": "1990-05-15",
  "birth_time": "08:30",
  "birth_place": "北京",
  "longitude": 116.4,
  "gender": "male",
  "confidence": 0.92,
  "missing_fields": []
}
```

Required fields for chart casting:

```text
birth_date
birth_time
longitude or birth_place resolvable to longitude
gender
```

Use a small city-longitude table for common cities. If the city cannot be resolved, ask for a more specific city or longitude.

## User-Facing Reply Policy

The main reply should be consultation-style.

It may use a small amount of professional language, but should avoid raw rule dumps.

The main conclusion should be based on 《子平真诠》. 《滴天髓》 can enrich the explanation style, but should not become the decision engine.

Allowed:

```text
你的命盘里事业压力感和竞争感比较明显，适合在有规则、有目标、有挑战的环境里发展。
从结构上看，这类组合更重视责任、约束和执行力。
```

Avoid by default:

```text
你是七杀格，用神癸水，相神甲木，忌神庚辛金。
```

The reply should usually contain four parts:

```text
direct answer
conditions or fit
risk reminder
suggested follow-up questions
```

## Topic Reply Frameworks

### Career

Cover:

- Suitable work environment.
- Suitable role and operating style.
- Entrepreneurship or job-change risks.
- Practical next step.

### Relationship

Cover:

- Relationship pattern.
- Suitable communication style.
- Likely friction points.
- Practical relationship advice.

### Wealth

Cover:

- Suitable money-making style.
- Risk preference.
- Cooperation and investment cautions.
- Cash-flow advice.

### Personality

Cover:

- Core strengths.
- Behavior under pressure.
- Recurring blockers.
- Growth advice.

## Arbitration Policy

The user-facing product should not expose "arbitration" as a technical concept.

The backend should call the arbitration LLM only when `prepare_arbitration()` returns cases and the runtime has a configured LLM provider. If no provider is configured, store the arbitration cases in trace and generate a conservative user-facing answer.

If arbitration has unresolved or low-confidence cases, the user-facing answer should become more conservative:

```text
这里有一个判断点不宜说得太满，所以我会把结论说得保守一些。
```

The operations trace still stores:

- Arbitration cases.
- Prompt bundles.
- LLM raw responses.
- Parsed decisions.
- Confidence.
- Unresolved status.
- Source basis and source tension when 《子平真诠》 and 《滴天髓》 point to different interpretive emphasis.

## Safety Policy

The MVP must not output:

- Health or disease diagnosis.
- Guaranteed wealth, divorce, failure, or success.
- Concrete investment instructions.
- Command-style advice for major life decisions.
- Fear-inducing language.

Use calibrated language:

```text
不建议一开始就压上全部资源。
```

Instead of:

```text
你一定不能创业。
```

## Integration With Existing Code

Keep the `bazibase` package deterministic and free of direct LLM calls.

Add the agent layer outside the core package, preferably under:

```text
web/backend/agent/
```

Suggested modules:

```text
session.py
models.py
ids.py
repository.py
extractor.py
tools.py
planner.py
responder.py
tracing.py
```

Responsibilities:

- `session.py`: load and update conversation state.
- `models.py`: Pydantic models for chat, extraction, state, and trace payloads.
- `ids.py`: generate public analysis IDs.
- `repository.py`: SQLite persistence for conversations, messages, runs, and traces.
- `extractor.py`: natural-language birth info and topic extraction.
- `tools.py`: wrappers around `cast_chart`, `diagnose`, and arbitration functions.
- `planner.py`: MVP state-machine decision logic.
- `responder.py`: user-facing reply generation.
- `tracing.py`: append trace steps in a consistent format.

## MVP Acceptance Criteria

The MVP is complete when:

- A user can start a new chat without using a form.
- The agent asks for missing birth information naturally.
- The agent answers career, relationship, wealth, and personality questions.
- Every assistant reply returns an `analysis_id`, including missing-information follow-ups.
- Operations can search by `analysis_id`.
- Operations can inspect messages and run traces for that analysis.
- User-facing replies do not expose raw rule chains by default.
- Trace includes chart, diagnosis, arbitration, and LLM raw inputs/outputs when available.
- The core `bazibase` package remains deterministic and does not call LLMs directly.

## Open Implementation Notes

- Start with SQLite because the existing web backend already uses it.
- Add auth before exposing admin endpoints beyond local development.
- Keep `analysis_id` short enough for users to copy, but random enough to avoid guessing.
- For the MVP, city-to-longitude resolution can start with a small curated China city table.
- Full rule citations should remain in backend trace and admin views, not in ordinary user chat.

## Follow-Up Design Topics

- Deeply define the命理 source and lineage strategy: how the agent should use 《子平真诠》 as the main analytical basis, where 《滴天髓》 may supplement interpretation, how to handle source tension, what passages/rules should be encoded, and how much of this should appear in user-facing replies versus operations trace.
