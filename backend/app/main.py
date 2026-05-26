"""
Uvicorn: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

WebSocket:
  ws://HOST:8000/ws/device?patient_id=P001   (ESP32)
  ws://HOST:8000/ws/twin                      (Digital Twin)
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers import control, dashboard_api, sessions
from app.api.websocket import pose_routes, rehab_routes
from app.application.services.pose_stream_service import get_pose_hub, get_pose_worker
from app.core.config import get_settings
from app.infrastructure.db.session import close_db, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    hub = get_pose_hub()
    hub.bind_loop(asyncio.get_running_loop())
    get_pose_worker().start()
    yield
    get_pose_worker().stop()
    await close_db()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Cyber layer — ROM, Digital Twin bridge, training history",
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

app.include_router(rehab_routes.router)
app.include_router(pose_routes.router)
app.include_router(sessions.router)
app.include_router(control.router)
app.include_router(dashboard_api.router)

_DASHBOARD_DIR = Path(__file__).resolve().parent / "static" / "dashboard"
if _DASHBOARD_DIR.is_dir():
    app.mount(
        "/dashboard",
        StaticFiles(directory=str(_DASHBOARD_DIR), html=True),
        name="dashboard",
    )


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard/")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
