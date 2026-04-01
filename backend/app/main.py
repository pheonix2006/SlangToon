from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.logging_config import setup_logging
from app.middleware import RequestIdMiddleware
from app.routers import script, comic, history, traces


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    Path(settings.comic_storage_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.history_file).parent.mkdir(parents=True, exist_ok=True)
    # Trace cleanup on startup
    if settings.trace_enabled:
        Path(settings.trace_dir).mkdir(parents=True, exist_ok=True)
        from app.flow_log.trace_store import TraceStore
        TraceStore(settings.trace_dir, settings.trace_retention_days).cleanup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    setup_logging(log_file="logs/backend.log", level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    data_dir = Path("data")
    if data_dir.exists():
        app.mount("/data", StaticFiles(directory="data"), name="data")
    app.include_router(script.router)
    app.include_router(comic.router)
    app.include_router(history.router)
    app.include_router(traces.router)
    return app


app = create_app()


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": "SlangToon"}
