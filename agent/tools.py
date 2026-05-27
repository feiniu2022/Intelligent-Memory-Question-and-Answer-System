"""智能体工具定义"""
from langchain_core.tools import tool
from memory.hybrid_memory import HybridMemoryStore
from rag.document_loader import DocumentLoader


def create_agent_tools(memory_store: HybridMemoryStore, knowledge_base: DocumentLoader):
    """创建所有工具"""

    @tool
    def search_memory(query: str, user_id: str) -> str:
        """
        搜索用户的长期记忆。当你需要了解用户的个人信息、偏好、历史记录时调用。

        Args:
            query: 搜索查询，例如"用户喜欢什么"、"用户的工作信息"
            user_id: 用户唯一标识
        """
        results = memory_store.hybrid_search(query, user_id, k=3)
        if not results:
            return "未找到相关历史记忆。"

        lines = []
        for i, r in enumerate(results, 1):
            mtype = r['metadata'].get('memory_type', '')
            lines.append(f"{i}. [{mtype}] {r['content']}")
        return "找到以下相关记忆：\n" + "\n".join(lines)

    @tool
    def save_memory(content: str, user_id: str, memory_type: str = "general") -> str:
        """
        保存一条重要的长期记忆。当用户在对话中透露了需要记住的信息时调用。

        Args:
            content: 要记住的内容，用一句话简洁概括
            user_id: 用户唯一标识
            memory_type: 记忆类型：fact(事实)、preference(偏好)、event(事件)、general(通用)
        """
        memory_store.add_memory(user_id, content, memory_type)
        return f"已记住: {content}"

    @tool
    def list_memories(user_id: str) -> str:
        """
        列出用户的所有长期记忆。

        Args:
            user_id: 用户唯一标识
        """
        memories = memory_store.get_user_memories(user_id)
        if not memories:
            return "暂无任何长期记忆。"

        lines = []
        for i, m in enumerate(memories, 1):
            t = m['metadata'].get('memory_type', 'general')
            ts = m['metadata'].get('timestamp', '')[:10]
            lines.append(f"{i}. [{t}] {m['content']} ({ts})")
        return "所有长期记忆：\n" + "\n".join(lines)

    @tool
    def search_knowledge(query: str, user_id: str = "default_user") -> str:
        """
        搜索已加载的知识库文档。当记忆库中找不到相关信息时调用此工具。
        知识库中可能包含产品信息、人物信息、事件等任何类型的资料。

        Args:
            query: 搜索查询，使用用户问题中的关键词
            user_id: 用户标识，用于限定搜索范围
        """
        results = knowledge_base.search(query, k=3, user_id=user_id)
        if not results:
            return "未在知识库中找到相关内容。"

        lines = []
        for i, r in enumerate(results, 1):
            filename = r['metadata'].get('filename', 'unknown')
            content_preview = r['content'][:200].replace('\n', ' ')
            lines.append(f"{i}. [来自: {filename}] {content_preview}...")
        return "找到以下知识库内容：\n" + "\n".join(lines)

    @tool
    def list_knowledge_files(user_id: str = "default_user") -> str:
        """列出已加载的所有知识库文件"""
        files = knowledge_base.list_files(user_id=user_id)
        if not files:
            return "暂无已加载的资料文件。"
        lines = []
        for f in files:
            lines.append(f"- {f['filename']} ({f['source']}, {f['total_chunks']} chunks)")
        return "已加载的资料文件：\n" + "\n".join(lines)

    return [search_memory, save_memory, list_memories, search_knowledge, list_knowledge_files]