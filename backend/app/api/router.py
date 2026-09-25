from fastapi import APIRouter

from app.api import accounts, clips, health, jobs, overview, projects, settings as settings_routes, sources, usage

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(overview.router)
api_router.include_router(accounts.router)
api_router.include_router(projects.router)
api_router.include_router(sources.router)
api_router.include_router(jobs.router)
api_router.include_router(clips.router)
api_router.include_router(clips.tags_router)
api_router.include_router(usage.router)
api_router.include_router(settings_routes.router)
