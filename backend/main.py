import sys
import os

# Ensure backend directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.routes import router
from config import settings

app = FastAPI(
    title="AI Software Engineer",
    description="Multi-agent AI system that builds software collaboratively",
    version="1.0.0",
    docs_url="/docs",
)

# NOTE: A wildcard origin ("*") is incompatible with allow_credentials=True and
# is silently ignored by browsers. We therefore enumerate explicit origins and
# also permit any origin via regex for local development flexibility.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_origin_regex=r"http://localhost:\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Enforce X-API-Key header when BACKEND_API_KEY is configured.

    WebSocket upgrade requests are skipped - the task_id already acts as an
    implicit token since you can only open a WS channel for a task you created.
    """
    if settings.BACKEND_API_KEY:
        is_websocket = request.headers.get("upgrade", "").lower() == "websocket"
        if not is_websocket:
            key = request.headers.get("x-api-key", "")
            if key != settings.BACKEND_API_KEY:
                return JSONResponse(
                    status_code=403,
                    content={"error": "Missing or invalid API key. Set the X-API-Key header."},
                )
    return await call_next(request)


app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "AI Software Engineer",
        "version": "1.0.0",
        "status": "running",
        "agents": ["planner", "coder", "reviewer", "tester"],
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "api_key_configured": bool(settings.OPENAI_API_KEY),
        "model": settings.OPENAI_MODEL,
    }