import logging

from app.config import Settings
from app.services.llm_client import LLMClient, LLMTimeoutError, LLMApiError
from app.prompts.analyze_prompt import ANALYZE_PROMPT
from app.schemas.analyze import StyleOption
from app.flow_log import FlowSession, get_current_trace

logger = logging.getLogger(__name__)


class AnalyzeError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def analyze_photo(image_base64: str, image_format: str, settings: Settings) -> list[StyleOption]:
    """分析照片，返回 5 个主题选项（仅名称+简述）。"""
    trace = get_current_trace()
    llm = LLMClient(settings)

    # Step 1: LLM 分析
    async with trace.step("llm_analyze", detail={"model": settings.openai_model, "image_size": len(image_base64), "temperature": 0.8}):
        try:
            logger.info("LLM 分析请求开始 (model=%s)", settings.openai_model)
            content = await llm.chat_with_vision(
                ANALYZE_PROMPT, image_base64, image_format,
                "请分析照片中的人物，生成 5 个创意主题选项",
                temperature=0.8,
            )
            logger.info("LLM 分析完成")
        except (LLMTimeoutError, LLMApiError) as e:
            logger.error("LLM 调用失败: %s", e)
            raise AnalyzeError(50001, f"Vision LLM 调用失败: {e}") from e

    # Step 2: 解析响应
    async with trace.step("parse_response"):
        try:
            data = LLMClient.extract_json_from_content(content)
        except Exception as e:
            logger.error("LLM 响应解析失败: %s", e)
            raise AnalyzeError(50002, f"Vision LLM 返回格式异常: {e}") from e

    if not isinstance(data, dict) or "options" not in data:
        raise AnalyzeError(50002, "JSON 缺少 options 字段")

    options = data["options"]
    if not isinstance(options, list) or len(options) == 0:
        raise AnalyzeError(50002, "options 应为非空数组")

    if len(options) < 5:
        raise AnalyzeError(50002, f"LLM 返回 {len(options)} 个选项，期望 5 个")

    style_options = []
    for i, opt in enumerate(options[:5]):
        if not isinstance(opt, dict):
            raise AnalyzeError(50002, f"options[{i}] 不是有效对象")
        for field in ("name", "brief"):
            if field not in opt or not opt[field]:
                raise AnalyzeError(50002, f"options[{i}] 缺少有效字段: {field}")
        style_options.append(StyleOption(name=opt["name"], brief=opt["brief"]))

    # 更新 llm_analyze step 的 detail（仅 FlowSession 模式）
    if isinstance(trace, FlowSession) and len(trace.trace.steps) > 0:
        trace.trace.steps[0].detail["options_count"] = len(style_options)
        trace.trace.steps[0].detail["topic_names"] = [o.name for o in style_options]

    return style_options
