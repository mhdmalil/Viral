from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from app.core.config import MEDIA_DIR, ROOT_DIR, settings
from app.core.logging import setup_logging
from app.database.base import Base
from app.database.session import engine, ensure_schema
from app.api.health import router as health_router
from app.api.router import api_router
from app import models  # noqa: F401  — register tables

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


def _mount_desktop_ui(app: FastAPI) -> None:
    index = FRONTEND_DIST / "index.html"
    if not index.is_file():
        return
    assets = FRONTEND_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="ui-assets")

    @app.get("/")
    def desktop_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/{full_path:path}")
    def desktop_spa(full_path: str) -> FileResponse:
        target = (FRONTEND_DIST / full_path).resolve()
        try:
            target.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            return FileResponse(index)
        if target.is_file():
            return FileResponse(target)
        return FileResponse(index)


def create_app() -> FastAPI:
    setup_logging()
    settings.ensure_dirs()
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    from app.api.jobs import abandon_orphan_jobs

    abandon_orphan_jobs()

    app = FastAPI(title="ViralClipper", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(api_router, prefix="/api")
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    Path(settings.projects_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
    app.mount("/files", StaticFiles(directory=settings.projects_dir), name="project-files")
    _mount_desktop_ui(app)
    return app


app = create_app()
