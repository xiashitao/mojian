"""FastAPI app — bazibase web backend entry point."""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Add bazibase project root to sys.path so `import bazibase` works
# web/ is nested under the bazibase project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import chart, arbitrate, charts_store, chat, admin, conversations
from .routers import auth as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Kairos API",
    description="AI 决策助手 — Ba Zi 排盘 / 诊断 / LLM 仲裁",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Register routers under /api prefix
app.include_router(auth_router.router, prefix="/api")
app.include_router(chart.router, prefix="/api")
app.include_router(arbitrate.router, prefix="/api")
app.include_router(charts_store.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
