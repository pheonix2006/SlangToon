import logging

from app.config import Settings
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError
from app.prompts.compose_prompt import COMPOSE_PROMPT
from app.services.image_gen_client import ImageGenClient, ImageGenTimeoutError, ImageGenApiError
from app.storage.file_storage import FileStorage
from app.services.history_service import HistoryService
from app.schemas.common import ErrorCode
from app.flow_log import get_current_trace

logger = logging.getLogger(__name__)


class GenerateError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def _compose_prompt(
    image_base64: str, image_format: str,
    style_name: str, style_brief: str, settings: Settings,
) -> str:
    """调 LLM 为选中的主题生成详细英文构图 prompt。"""
    llm = LLMClient(settings)
    try:
        logger.info("Compose LLM 请求开始 (model=%s, style=%s)", settings.openai_model, style_name)
        content = await llm.chat_with_vision(
            COMPOSE_PROMPT, image_base64, image_format,
            f"主题: {style_name}\n简述: {style_brief}\n请为这个主题撰写详细的英文构图提示词。",
            temperature=0.7,
        )
    except (LLMTimeoutError, LLMApiError) as e:
        logger.error("Compose LLM 调用失败: %s", e)
        raise GenerateError(ErrorCode.COMPOSE_LLM_FAILED, f"构图设计失败: {e}") from e

    try:
        data = LLMClient.extract_json_from_content(content)
    except Exception as e:
        logger.error("Compose LLM 响应解析失败: %s", e)
        raise GenerateError(ErrorCode.COMPOSE_LLM_INVALID, f"构图设计响应异常: {e}") from e

    if "prompt" not in data or not data["prompt"]:
        raise GenerateError(ErrorCode.COMPOSE_LLM_INVALID, "构图设计缺少 prompt 字段")
    return data["prompt"]


async def generate_artwork(
    image_base64: str, image_format: str,
    style_name: str, style_brief: str,
    settings: Settings, storage: FileStorage, history: HistoryService,
) -> dict:
    """生成海报：先 LLM 构思详细 prompt，再调 Qwen 生图。"""
    trace = get_current_trace()

    # 1. 保存原始照片
    async with trace.step("save_photo"):
        photo_info = storage.save_photo(image_base64, image_format)
        if hasattr(trace, 'trace') and trace.trace.steps:
            trace.trace.steps[-1].detail = {"path": photo_info.get("file_path", ""), "file_size": len(image_base64)}

    # 2. Compose — LLM 生成详细英文构图 prompt
    async with trace.step("compose_prompt", detail={"model": settings.openai_model, "style_name": style_name, "temperature": 0.7}):
        prompt = await _compose_prompt(image_base64, image_format, style_name, style_brief, settings)
        if hasattr(trace, 'trace') and trace.trace.steps:
            trace.trace.steps[-1].detail["prompt_length"] = len(prompt)

    # 3. Image generation — Qwen 生图
    gen_client = ImageGenClient(settings)
    async with trace.step("image_generate", detail={"model": settings.qwen_image_model, "style_name": style_name}):
        try:
            logger.info("图片生成请求开始 (model=%s, style=%s)", settings.qwen_image_model, style_name)
            poster_b64 = await gen_client.generate(prompt, image_base64, image_format)
            logger.info("图片生成完成")
            if hasattr(trace, 'trace') and trace.trace.steps:
                trace.trace.steps[-1].detail["response_size"] = len(poster_b64)
        except (ImageGenTimeoutError, ImageGenApiError) as e:
            logger.error("图片生成失败: %s", e)
            raise GenerateError(50003, f"图片生成失败: {e}") from e
        except Exception as e:
            logger.error("生成结果处理失败: %s", e)
            raise GenerateError(50004, f"生成结果处理失败: {e}") from e

    # 4. Save poster & record history
    async with trace.step("save_poster"):
        poster_info = storage.save_poster(poster_b64, photo_info["uuid"], photo_info["date"])
        history_id = history.add({
            "style_name": style_name,
            "prompt": prompt,
            "poster_url": poster_info["poster_url"],
            "thumbnail_url": poster_info["thumbnail_url"],
            "photo_url": photo_info["url"],
        })
        logger.info("海报已保存 (history_id=%s)", history_id)
        if hasattr(trace, 'trace') and trace.trace.steps:
            trace.trace.steps[-1].detail = {"history_id": history_id}

    return {
        "poster_url": poster_info["poster_url"],
        "thumbnail_url": poster_info["thumbnail_url"],
        "history_id": history_id,
    }
