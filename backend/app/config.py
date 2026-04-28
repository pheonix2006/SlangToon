from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用配置
    app_name: str = "SlangToon"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8889

    # Vision LLM (OpenAI-compatible, using GLM-4.6V)
    openai_api_key: str = Field(alias="OPENAI_API_KEY", default="")
    openai_base_url: str = Field(alias="OPENAI_BASE_URL", default="https://open.bigmodel.cn/api/paas/v4")
    openai_model: str = Field(alias="OPENAI_MODEL", default="glm-4.6v")
    vision_llm_max_tokens: int = 16384
    vision_llm_timeout: int = 120
    vision_llm_max_retries: int = 2

    # Qwen Image 2.0
    qwen_image_apikey: str = ""
    qwen_image_base_url: str = "https://dashscope.aliyuncs.com/api/v1"
    qwen_image_model: str = "qwen-image-2.0"
    qwen_image_timeout: int = 120
    qwen_image_max_retries: int = 3

    # Image generation provider switch
    image_gen_provider: str = "dashscope"  # "dashscope" | "openrouter" | "replicate"

    # OpenRouter image generation
    openrouter_image_apikey: str = ""
    openrouter_image_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_image_model: str = "google/gemini-2.5-flash-image"
    openrouter_image_timeout: int = 120
    openrouter_image_max_retries: int = 3

    # Replicate image generation
    replicate_api_token: str = ""
    replicate_image_model: str = "openai/gpt-image-2"
    replicate_image_timeout: int = 300
    replicate_image_max_retries: int = 3
    replicate_image_extra_params: str = ""  # JSON string, e.g. '{"quality":"auto","moderation":"auto"}'

    # 存储
    comic_storage_dir: str = "data/comics"
    history_file: str = "data/history.json"
    slang_blacklist_file: str = "data/slang_blacklist.json"
    max_history_records: int = 1000

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # 日志
    log_level: str = "INFO"

    # Trace
    trace_enabled: bool = True
    trace_dir: str = "data/traces"
    trace_retention_days: int = 7

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


def get_settings() -> Settings:
    return Settings()
