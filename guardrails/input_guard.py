import re

from langchain_core.messages import AIMessage, HumanMessage

from utils.logger import setup_logger

logger = setup_logger(__name__)

MAX_INPUT_LENGTH = 2000

INJECTION_PATTERNS = [
    r"(?i)ignore\s+(previous|above|all)\s+(instructions|prompts|rules)",
    r"(?i)forget\s+(everything|all|previous)",
    r"(?i)you\s+are\s+now\s+",
    r"(?i)pretend\s+(you\s+are|to\s+be)",
    r"(?i)system\s*:\s*",
    r"(?i)(sudo|admin|root)\s+mode",
    r"(?i)jailbreak",
    r"(?i)dan\s+mode",
    r"(?i)override\s+(all\s+)?(safety|security|filter)",
    r"```(python|javascript|bash|shell)\s",
    r"(?i)exec\s*\(",
    r"(?i)subprocess\.",
    r"(?i)__import__",
    r"(?i)os\.system\s*\(",
]

UNSAFE_CONTENT_PATTERNS = [
    r"(?i)(how\s+to|ways\s+to|make|create|build|synthes)\s+(bomb|weapon|drug|poison|explosive)",
    r"(?i)(hack|exploit|attack)\s+(into|system|server|database|account)",
]


def detect_prompt_injection(text: str) -> tuple[bool, str]:
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True, f"匹配到潜在注入模式: {pattern}"
    return False, ""


def detect_unsafe_content(text: str) -> tuple[bool, str]:
    for pattern in UNSAFE_CONTENT_PATTERNS:
        if re.search(pattern, text):
            return True, f"匹配到不安全内容模式: {pattern}"
    return False, ""


def input_guardrail(state: dict) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        return state

    content = last_msg.content
    if not content or not isinstance(content, str):
        return state

    if len(content) > MAX_INPUT_LENGTH:
        logger.warning("输入护栏: 输入过长 (%d 字符, 上限 %d)", len(content), MAX_INPUT_LENGTH)
        return {
            "messages": [
                AIMessage(
                    content=f"输入过长（{len(content)}字），请控制在{MAX_INPUT_LENGTH}字以内。"
                )
            ]
        }

    is_injection, reason = detect_prompt_injection(content)
    if is_injection:
        logger.warning("输入护栏: 拦截注入攻击 - %s | 内容: %.80s...", reason, content)
        return {
            "messages": [
                AIMessage(content="检测到不安全的输入内容，请重新表述您的问题。")
            ]
        }

    is_unsafe, reason = detect_unsafe_content(content)
    if is_unsafe:
        logger.warning("输入护栏: 拦截不安全内容 - %s | 内容: %.80s...", reason, content)
        return {
            "messages": [
                AIMessage(content="输入内容涉及不安全信息，我无法回答此类问题。")
            ]
        }

    return state


def route_after_input_guardrail(state: dict) -> str:
    messages = state.get("messages", [])
    if not messages:
        return "agent"

    last_msg = messages[-1]
    has_tool_calls = isinstance(last_msg, AIMessage) and last_msg.tool_calls
    if isinstance(last_msg, AIMessage) and not has_tool_calls:
        return "rejected"

    return "agent"