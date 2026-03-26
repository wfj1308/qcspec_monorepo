"""
QCSpec FastAPI backend
services/api/main.py
"""

from contextlib import asynccontextmanager
from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load env files for local development.
# Priority: repo root .env, then service-local .env.
ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
API_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(ROOT_ENV, override=False)
load_dotenv(API_ENV, override=False)

from routers import auth, autoreg, erpnext, inspections, photos, projects, proof, reports, settings, team


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("QCSpec API starting")
    print(f"Supabase: {os.getenv('SUPABASE_URL', 'not configured')[:40]}")
    yield
    print("QCSpec API stopped")


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

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(
    projects.router,
    prefix="/v1/projects",
    tags=["projects"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    projects.public_router,
    prefix="/v1/projects",
    tags=["projects-public"],
)
app.include_router(
    inspections.router,
    prefix="/v1/inspections",
    tags=["inspections"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    photos.router,
    prefix="/v1/photos",
    tags=["photos"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    reports.router,
    prefix="/v1/reports",
    tags=["reports"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    proof.router,
    prefix="/v1/proof",
    tags=["proof"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    team.router,
    prefix="/v1/team",
    tags=["team"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    settings.router,
    prefix="/v1/settings",
    tags=["settings"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    erpnext.router,
    prefix="/v1/erpnext",
    tags=["erpnext"],
    dependencies=[Depends(auth.require_auth)],
)
app.include_router(
    autoreg.router,
    tags=["autoreg"],
    dependencies=[Depends(auth.require_auth)],
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
