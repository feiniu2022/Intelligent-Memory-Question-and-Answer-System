"""
智能记忆问答Agent - 入口文件

使用方法：
  CLI 模式:  python main.py
  API 服务:  python server.py

CLI 命令：
  load       - 加载知识库文件（支持 TXT/MD/PDF/DOCX/PPTX）
  rag <问题>  - RAG 检索问答（HyDE增强）
  memories   - 查看所有长期记忆
  files      - 查看已加载的知识库文件
  quit       - 退出
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.memory_agent import MemoryAgent
from config import settings


def print_banner():
    print("=" * 60)
    print("  智能记忆问答Agent v3.0")
    print("  - 长期记忆（混合检索）")
    print("  - 多格式知识库（TXT/MD/PDF/DOCX/PPTX）")
    print("  - RAG检索增强（HyDE）")
    print("  - 输入/输出安全护栏")
    print("  - LangGraph StateGraph 架构")
    print("=" * 60)
    print("  命令：")
    print("    load       - 加载知识库文件")
    print("    rag <问题>  - RAG检索问答")
    print("    memories   - 查看所有长期记忆")
    print("    files      - 查看已加载资料文件")
    print("    quit       - 退出")
    print("=" * 60)


def main():
    os.makedirs(str(settings.resolved_txt_data_dir), exist_ok=True)
    print_banner()

    print("\n正在初始化Agent...")
    agent = MemoryAgent()
    print("Agent初始化完成\n")

    user_id = "default_user"
    session_id = "session_1"

    while True:
        try:
            user_input = input("你: ").strip()
            if not user_input:
                continue

            if user_input.lower() == "quit":
                print("再见！")
                break

            if user_input.lower() == "load":
                from rag.document_loader import DocumentLoader
                loader = DocumentLoader()
                count = loader.load_all_files(user_id=user_id)
                print(f"加载完成: {count} 个文本块")
                continue

            if user_input.lower().startswith("rag "):
                from rag.rag_service import RAGService
                rag = RAGService()
                query = user_input[4:].strip()
                if not query:
                    print("用法: rag <问题>")
                    continue
                result = rag.query(query, user_id=user_id)
                print(f"\n[HyDE查询] {result.get('hyde_query', 'N/A')[:100]}...")
                print(f"\n[回答] {result['answer']}")
                if result.get("sources"):
                    print("\n[来源]:")
                    for s in result["sources"]:
                        print(f"  - {s['filename']} (score: {s['score']})")
                continue

            if user_input.lower() == "memories":
                memories = agent.memory_store.get_user_memories(user_id)
                if not memories:
                    print("(暂无长期记忆)")
                else:
                    for i, m in enumerate(memories, 1):
                        t = m['metadata'].get('memory_type', 'general')
                        ts = m['metadata'].get('timestamp', '')[:19]
                        print(f"  {i}. [{t}] {m['content']}")
                        print(f"     {ts}")
                continue

            if user_input.lower() == "files":
                files = agent.knowledge_base.list_files(user_id=user_id)
                if not files:
                    print("(暂无已加载的资料文件)")
                else:
                    for f in files:
                        print(f"  - {f['filename']} ({f['source']}, {f['total_chunks']} chunks)")
                continue

            print("助手: ", end="", flush=True)
            full_reply = ""
            for chunk in agent.chat_stream(user_id, user_input, session_id):
                if chunk and chunk != full_reply:
                    if full_reply and chunk.startswith(full_reply):
                        print(chunk[len(full_reply):], end="", flush=True)
                    else:
                        print(chunk, end="", flush=True)
                    full_reply = chunk
            if not full_reply:
                reply = agent.chat(user_id, user_input, session_id)
                print(reply)
            else:
                print()

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"\n错误: {e}")


if __name__ == "__main__":
    main()