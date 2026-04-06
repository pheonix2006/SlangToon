import os
from pathlib import Path

from dotenv import load_dotenv

# 在任何 LangSmith/LangGraph 导入之前加载 .env 到 os.environ
# 确保 LANGSMITH_TRACING / LANGSMITH_API_KEY / LANGSMITH_PROJECT 生效
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=False)

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
