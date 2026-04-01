import uvicorn

from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        access_log=False,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "loggers": {
                "uvicorn": {"level": "WARNING", "propagate": True},
                "uvicorn.access": {"level": "WARNING", "propagate": False},
                "uvicorn.error": {"level": "WARNING", "propagate": True},
            },
        },
    )
