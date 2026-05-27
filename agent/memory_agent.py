"""智能体主逻辑 - 基于 LangGraph StateGraph 构建"""
import sqlite3

from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt.tool_node import tools_condition
from langgraph.store.memory import InMemoryStore
from tenacity import retry, stop_after_attempt, wait_exponential

from agent.prompt import SYSTEM_PROMPT
from agent.state import AgentState
from guardrails.input_guard import input_guardrail, route_after_input_guardrail
from guardrails.output_guard import output_guardrail
from memory.hybrid_memory import HybridMemoryStore
from rag.document_loader import DocumentLoader
from .tools import create_agent_tools
from config import settings
from utils.logger import setup_logger

logger = setup_logger(__name__)

MAX_MESSAGES = settings.max_messages
SUMMARY_THRESHOLD = settings.summary_threshold

_CHECKPOINT_PATH = str(settings.base_dir / "data" / "checkpoints.db")


class MemoryAgent:
    """具有长期记忆和知识库的智能体（StateGraph + 护栏 + 重试 + 消息裁剪 + 流式输出）"""

    def __init__(self):
        self.memory_store = HybridMemoryStore()
        self.knowledge_base = DocumentLoader()

        self.llm = ChatOpenAI(
            model=settings.chat_model,
            base_url=settings.chat_base_url,
            api_key=settings.chat_api_key,
            extra_body={"thinking": {"type": "disabled"}},
            temperature=0,
            max_tokens=2048,
        )

        self.tools = create_agent_tools(self.memory_store, self.knowledge_base)
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tool_node = ToolNode(self.tools)

        conn = sqlite3.connect(_CHECKPOINT_PATH, check_same_thread=False)
        self.checkpointer = SqliteSaver(conn)
        self.store = InMemoryStore()

        self.graph = self._build_graph()

        self.load_knowledge_files()

    def _trim_messages(self, messages):
        if len(messages) <= MAX_MESSAGES:
            return messages
        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        others = [m for m in messages if not isinstance(m, SystemMessage)]
        return system_msgs + others[-(MAX_MESSAGES - len(system_msgs)):]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_llm(self, messages):
        return self.llm_with_tools.invoke(messages)

    def _agent_node(self, state: AgentState):
        messages = list(state["messages"])

        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

        messages = self._trim_messages(messages)

        try:
            response = self._call_llm(messages)
        except Exception as e:
            logger.error("LLM 调用失败（已重试3次）: %s", e)
            return {
                "messages": [
                    AIMessage(content=f"抱歉，模型服务暂时不可用，请稍后重试。错误: {e}")
                ]
            }

        return {"messages": [response]}

    def _inject_user_id_node(self, state: AgentState):
        messages = state["messages"]
        if not messages:
            return state

        last_msg = messages[-1]
        user_id = state.get("user_id", "default_user")

        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                if "user_id" not in tc.get("args", {}):
                    tc["args"] = {**tc.get("args", {}), "user_id": user_id}

        return state

    def _summarize_node(self, state: AgentState):
        """对话摘要：当消息数超过 SUMMARY_THRESHOLD 时，将旧消息压缩为一条摘要"""
        messages = state["messages"]
        if len(messages) <= SUMMARY_THRESHOLD:
            return state

        system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
        non_system = [m for m in messages if not isinstance(m, SystemMessage)]

        if len(non_system) <= SUMMARY_THRESHOLD - len(system_msgs):
            return state

        old_msgs = non_system[:len(non_system) - MAX_MESSAGES + len(system_msgs)]
        recent_msgs = non_system[len(non_system) - MAX_MESSAGES + len(system_msgs):]

        old_text = "\n".join(
            f"{'用户' if isinstance(m, HumanMessage) else '助手'}: {m.content[:200]}"
            for m in old_msgs if hasattr(m, 'content') and m.content
        )

        try:
            summary_response = self.llm.invoke([
                SystemMessage(content="请用2-3句话概括以下对话的关键信息，保留重要的事实、偏好和决策："),
                HumanMessage(content=old_text),
            ])
            summary_msg = SystemMessage(content=f"[对话摘要] {summary_response.content}")
            return {"messages": system_msgs + [summary_msg] + recent_msgs}
        except Exception as e:
            logger.warning("摘要生成失败: %s, 保留最近消息", e)
            return state

    def _build_graph(self):
        builder = StateGraph(AgentState)

        builder.add_node("input_guardrail", input_guardrail)
        builder.add_node("agent", self._agent_node)
        builder.add_node("inject_user_id", self._inject_user_id_node)
        builder.add_node("summarize", self._summarize_node)
        builder.add_node("tools", self.tool_node)
        builder.add_node("output_guardrail", output_guardrail)

        builder.add_edge(START, "input_guardrail")
        builder.add_conditional_edges(
            "input_guardrail",
            route_after_input_guardrail,
            {"rejected": END, "agent": "agent"},
        )
        builder.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "inject_user_id", "__end__": "output_guardrail"},
        )
        builder.add_edge("inject_user_id", "tools")
        builder.add_edge("tools", "summarize")
        builder.add_edge("summarize", "agent")
        builder.add_edge("output_guardrail", END)

        graph = builder.compile(checkpointer=self.checkpointer, store=self.store)
        logger.info("Agent 图编译完成（含护栏+消息裁剪+摘要）")
        return graph

    def chat(self, user_id: str, message: str, thread_id: str = "default") -> str:
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        }
        response = self.graph.invoke(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
            },
            config=config,
        )
        return response["messages"][-1].content

    def chat_stream(self, user_id: str, message: str, thread_id: str = "default"):
        """同步流式输出，用于 SSE 和 CLI"""
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id,
            }
        }
        seen_content = ""
        for event in self.graph.stream(
            {
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
            },
            config=config,
            stream_mode="values",
        ):
            if "messages" in event and event["messages"]:
                last_msg = event["messages"][-1]
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    new_content = last_msg.content
                    if new_content.startswith(seen_content):
                        delta = new_content[len(seen_content):]
                        if delta:
                            yield delta
                    else:
                        yield new_content
                    seen_content = new_content

    def load_knowledge_files(self):
        return self.knowledge_base.load_all_files(user_id="default")