"""API v1 routers."""

from fastapi import APIRouter

from app.api.v1 import health, auth, jobs, artifacts, ir

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(ir.router, prefix="/ir", tags=["Symbolic IR"])

