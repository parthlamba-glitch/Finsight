"""
FinSight Backend Application Entrypoint.

Accessibility-First, Voice-First Financial Copilot.
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Ensure repository root and backend directory are in sys.path for monorepo imports
_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

# Load project-root .env before any router or AI module is imported
from dotenv import load_dotenv

if (_REPO_ROOT / ".env").is_file():
    load_dotenv(_REPO_ROOT / ".env")
elif (_BACKEND_DIR / ".env").is_file():
    load_dotenv(_BACKEND_DIR / ".env")
else:
    load_dotenv()

from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.db import get_db, init_db
from backend.routers import auth, dashboard, transactions, goals, bank, statements, ai, payments, voice


class PrefixStrippingMiddleware:
    """
    ASGI middleware that transparently strips the '/svc/api' prefix if preserved by
    upstream rewrites/proxies, routing directly to the standard FastAPI routes (/auth, /overview, etc.).
    """

    def __init__(self, app: ASGIApp, prefix: str = "/svc/api"):
        self.app = app
        self.prefix = prefix
        self.prefix_bytes = prefix.encode("ascii")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path.startswith(self.prefix):
                scope = dict(scope)
                scope["path"] = path[len(self.prefix):] or "/"
                raw_path = scope.get("raw_path")
                if raw_path and raw_path.startswith(self.prefix_bytes):
                    scope["raw_path"] = raw_path[len(self.prefix_bytes):] or b"/"
        await self.app(scope, receive, send)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager to initialize SQLite schema on startup."""
    init_db()
    yield


app = FastAPI(
    title="FinSight API",
    description="Accessibility-First Financial Copilot API backend.",
    version="0.1.0",
    lifespan=lifespan,
)

# Prefix stripping middleware for upstream /svc/api routing
app.add_middleware(PrefixStrippingMiddleware, prefix="/svc/api")

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(goals.router)
app.include_router(bank.router)
app.include_router(statements.router)
app.include_router(ai.router)
app.include_router(payments.router)
app.include_router(voice.router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Health"])
@app.get("/api/v1/health", status_code=status.HTTP_200_OK, tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint verifying application status and database connectivity.
    """
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "service": "finsight-backend",
        "version": "0.1.0",
        "database": db_status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)

