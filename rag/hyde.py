from langchain_openai import ChatOpenAI
from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

HYDE_PROMPT = """请根据以下用户问题，写一段详细的回答，就好像你是一个专家一样。
不需要完全正确，但要包含可能相关的关键词和概念，以便用于检索相关文档。

用户问题：{query}

请直接写出一段回答文本（不需要加"根据..."等前缀）："""


class HyDEGenerator:
    """HyDE: 用 LLM 生成假设性文档，替代原始查询做向量检索，提升召回率"""

    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.chat_model,
                base_url=settings.chat_base_url,
                api_key=settings.chat_api_key,
                extra_body={"thinking": {"type": "disabled"}},
                temperature=0.3, max_tokens=512,
            )
        return self._llm

    def generate(self, query: str) -> str:
        if not settings.rag_hyde_enabled:
            return query
        try:
            response = self.llm.invoke(HYDE_PROMPT.format(query=query))
            content = response.content.strip()
            if content:
                logger.info("HyDE 生成 (%d chars)", len(content))
                return content
            return query
        except Exception as e:
            logger.warning("HyDE 失败: %s", e)
            return query

    async def agenerate(self, query: str) -> str:
        if not settings.rag_hyde_enabled:
            return query
        try:
            response = await self.llm.ainvoke(HYDE_PROMPT.format(query=query))
            content = response.content.strip()
            if content:
                logger.info("HyDE async 生成 (%d chars)", len(content))
                return content
            return query
        except Exception as e:
            logger.warning("HyDE async 失败: %s", e)
            return query