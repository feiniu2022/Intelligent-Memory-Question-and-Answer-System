from typing import AsyncIterator, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from config import settings
from rag.document_loader import DocumentLoader
from rag.hyde import HyDEGenerator
from utils.logger import setup_logger

logger = setup_logger(__name__)

RAG_PROMPT = """你是一个专业的知识库问答助手。请严格根据以下参考资料回答用户的问题。

## 规则
1. 只使用参考资料中的信息来回答
2. 如果参考资料中没有相关信息，请诚实告知
3. 回答时标注信息来源（文件名）
4. 回答要简洁、准确、有条理

## 参考资料
{context}
"""

NO_CONTEXT_PROMPT = """你是一个智能助手。用户提出的问题在知识库中没有找到相关资料。
请根据你的常识回答，但要在回答中说明"知识库中暂无相关资料，以下为通用回答"。"""


class RAGService:
    def __init__(self):
        self._llm = None
        self._hyde = HyDEGenerator()
        self._loader = DocumentLoader()

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(
                model=settings.chat_model, base_url=settings.chat_base_url,
                api_key=settings.chat_api_key,
                extra_body={"thinking": {"type": "disabled"}},
                temperature=0, max_tokens=2048,
            )
        return self._llm

    def query(self, question: str, user_id: str = "default", top_k: int = 5, use_hyde: bool = True) -> dict:
        retrieval_q = self._hyde.generate(question) if use_hyde else question
        docs = self._loader.search(retrieval_q, k=top_k, user_id=user_id)
        if not docs:
            answer = self._answer_no_ctx(question)
            return {"answer": answer, "sources": [], "query": question, "hyde_query": retrieval_q if use_hyde else None}
        ctx = self._fmt_ctx(docs)
        return {"answer": self._answer(question, ctx), "sources": self._src(docs), "query": question, "hyde_query": retrieval_q if use_hyde else None}

    async def aquery(self, question: str, user_id: str = "default", top_k: int = 5, use_hyde: bool = True) -> dict:
        retrieval_q = await self._hyde.agenerate(question) if use_hyde else question
        docs = self._loader.search(retrieval_q, k=top_k, user_id=user_id)
        if not docs:
            answer = await self._aanswer_no_ctx(question)
            return {"answer": answer, "sources": [], "query": question, "hyde_query": retrieval_q if use_hyde else None}
        ctx = self._fmt_ctx(docs)
        return {"answer": await self._aanswer(question, ctx), "sources": self._src(docs), "query": question, "hyde_query": retrieval_q if use_hyde else None}

    async def aquery_stream(self, question: str, user_id: str = "default", top_k: int = 5, use_hyde: bool = True) -> AsyncIterator[str]:
        retrieval_q = await self._hyde.agenerate(question) if use_hyde else question
        yield {"event": "status", "data": "searching"}
        docs = self._loader.search(retrieval_q, k=top_k, user_id=user_id)
        if not docs:
            yield {"event": "status", "data": "no_context"}
            async for ev in self._astream_no_ctx(question):
                yield ev
            return
        ctx = self._fmt_ctx(docs)
        yield {"event": "status", "data": "generating"}
        prompt = RAG_PROMPT.format(context=ctx)
        async for event in self.llm.astream_events([SystemMessage(content=prompt), HumanMessage(content=question)], version="v2"):
            if event.get("event") == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {"event": "token", "data": chunk.content}

    def _fmt_ctx(self, docs):
        parts = [f"[文档{i} - {d.get('metadata', {}).get('filename', '?')}]\n{d['content']}" for i, d in enumerate(docs, 1)]
        return "\n\n".join(parts)

    def _src(self, docs):
        seen = set()
        s = []
        for d in docs:
            fn = d.get("metadata", {}).get("filename", "?")
            if fn not in seen:
                seen.add(fn)
                s.append({"filename": fn, "score": d.get("score", 0)})
        return s

    def _answer(self, q, ctx):
        return self.llm.invoke([SystemMessage(content=RAG_PROMPT.format(context=ctx)), HumanMessage(content=q)]).content

    async def _aanswer(self, q, ctx):
        return (await self.llm.ainvoke([SystemMessage(content=RAG_PROMPT.format(context=ctx)), HumanMessage(content=q)])).content

    def _answer_no_ctx(self, q):
        return self.llm.invoke([SystemMessage(content=NO_CONTEXT_PROMPT), HumanMessage(content=q)]).content

    async def _aanswer_no_ctx(self, q):
        return (await self.llm.ainvoke([SystemMessage(content=NO_CONTEXT_PROMPT), HumanMessage(content=q)])).content

    async def _astream_no_ctx(self, q):
        async for event in self.llm.astream_events([SystemMessage(content=NO_CONTEXT_PROMPT), HumanMessage(content=q)], version="v2"):
            if event.get("event") == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield {"event": "token", "data": chunk.content}