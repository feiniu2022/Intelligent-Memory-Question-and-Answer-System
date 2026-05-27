import re

from langchain_core.messages import AIMessage

from utils.logger import setup_logger

logger = setup_logger(__name__)

PII_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("id_card", re.compile(r"\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b"), "[ID_CARD]"),
    ("phone", re.compile(r"(?:(?:\+86)?[-\s]?)?1[3-9]\d{9}\b"), "[PHONE]"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    ("bank_card", re.compile(r"\b\d{16,19}\b"), "[BANK_CARD]"),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    masked_types: list[str] = []
    for pii_type, pattern, replacement in PII_PATTERNS:
        if pattern.search(text):
            text = pattern.sub(replacement, text)
            masked_types.append(pii_type)
    return text, masked_types


def output_guardrail(state: dict) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage):
        return state

    if not last_msg.content or getattr(last_msg, "tool_calls", None):
        return state

    masked_content, masked_types = mask_pii(last_msg.content)

    if masked_types:
        logger.info("输出护栏: 脱敏了 %s 类信息: %s", len(masked_types), ", ".join(masked_types))
        return {
            "messages": [
                AIMessage(content=masked_content, id=last_msg.id)
            ]
        }

    return state