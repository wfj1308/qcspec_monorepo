"""FastAPI app factory and router bootstrap."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api.infrastructure.http.middleware import SovereignContextMiddleware
from services.api.routers import ROUTER_REGISTRY


def _load_env() -> None:
    root_env = Path(__file__).resolve().parents[4] / ".env"
    api_env = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(root_env, override=False)
    load_dotenv(api_env, override=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    print("QCSpec API starting")
    print(f"Supabase: {os.getenv('SUPABASE_URL', 'not configured')[:40]}")
    yield
    print("QCSpec API stopped")


def create_app() -> FastAPI:
    _load_env()
    app = FastAPI(
        title="QCSpec API",
        description="Engineering quality inspection platform backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SovereignContextMiddleware)

    for item in ROUTER_REGISTRY:
        app.include_router(
            item["router"],
            prefix=item.get("prefix", ""),
            tags=item.get("tags", []),
            dependencies=item.get("dependencies", []),
        )

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "QCSpec API",
            "version": "0.1.0",
            "v_uri": "v://cn/region/service/qcspec-api/",
        }

    @app.get("/")
    async def root():
        return {
            "name": "QCSpec Engineering Quality Platform",
            "docs": "/docs",
            "health": "/health",
            "v_uri": "v://cn/region/service/qcspec-api/",
        }

    return app
