"""POST /api/chat/mock — 模拟流式输出，用于前端调试。"""
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

_MOCK_REPLY = (
    "根据你的命盘结构来看，日主偏强，用神倾向食伤泄秀。"
    "事业上比较适合在专业领域深耕，靠能力和作品建立信用，"
    "而不是靠人脉和资源驱动的方向。\n\n"
    "当前运势处于过渡期，适合稳固现有基础，"
    "不宜大规模扩张或冒险性投入。明年下半年开始，"
    "会进入一个相对顺畅的阶段，可以考虑做一些中期布局。\n\n"
    "你可以继续问：适合哪个行业方向？ / 明年有什么需要注意的？"
)


async def _mock_stream(conversation_id: str | None):
    conv_id = conversation_id or "mock-conv-001"
    analysis_id = "mock-analysis-001"

    # 按字符分批 yield，模拟真实流速
    chunk_size = 3
    for i in range(0, len(_MOCK_REPLY), chunk_size):
        chunk = _MOCK_REPLY[i:i + chunk_size]
        yield json.dumps({"type": "token", "text": chunk}, ensure_ascii=False) + "\n"
        await asyncio.sleep(0.05)

    yield json.dumps({
        "type": "done",
        "conversation_id": conv_id,
        "analysis_id": analysis_id,
        "state": {
            "topic": "career",
            "needs_more_info": False,
            "missing_fields": [],
            "suggested_followups": ["适合哪个行业方向？", "明年有什么需要注意的？"],
        },
    }, ensure_ascii=False) + "\n"


@router.post("/chat/mock")
async def mock_chat(body: dict = None):
    """流式输出 mock，用于前端验证 streaming UI，无需 API key。"""
    conv_id = (body or {}).get("conversation_id")
    return StreamingResponse(
        _mock_stream(conv_id),
        media_type="application/x-ndjson",
    )
