"""TXT资料加载器 - 将txt文件加载为知识库"""
import os
import hashlib
from typing import List, Dict, Optional
from datetime import datetime
from langchain_core.documents import Document
from memory.vector_store import VectorStoreManager
from utils.logger import setup_logger
import config

logger = setup_logger(__name__)


class TXTKnowledgeBase:
    """TXT资料知识库"""

    def __init__(self, persist_directory: str = None, txt_dir: str = None):
        if persist_directory is None:
            persist_directory = config.KNOWLEDGE_DB_DIR
        if txt_dir is None:
            txt_dir = config.TXT_DATA_DIR

        self.txt_dir = txt_dir
        os.makedirs(txt_dir, exist_ok=True)

        self.vector_manager = VectorStoreManager(
            persist_directory=persist_directory,
            collection_name="txt_knowledge"
        )

    def _compute_file_hash(self, filepath: str) -> str:
        """计算文件MD5哈希"""
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def load_txt_file(self, filepath: str, chunk_size: int = 500,
                      chunk_overlap: int = 50) -> int:
        """
        加载单个txt文件到知识库

        Args:
            filepath: txt文件路径
            chunk_size: 分块大小
            chunk_overlap: 块重叠大小

        Returns:
            添加的文本块数量
        """
        filename = os.path.basename(filepath)
        file_hash = self._compute_file_hash(filepath)

        # 检查是否已加载
        existing = self.vector_manager.get_all(filter={"file_hash": file_hash})
        if existing and existing.get("ids"):
            logger.info("文件已加载，跳过: %s", filename)
            return 0

        # 读取文件
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 简单分块
        chunks = []
        for i in range(0, len(content), chunk_size - chunk_overlap):
            chunk = content[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)

        if not chunks:
            return 0

        # 批量存入向量库
        texts = []
        metadatas = []
        ids = []

        for i, chunk in enumerate(chunks):
            texts.append(chunk)
            metadatas.append({
                "filename": filename,
                "file_hash": file_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "source": "txt_file",
                "timestamp": datetime.now().isoformat()
            })
            ids.append(f"{file_hash}_{i}")

        self.vector_manager.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        logger.info("已加载文件 %s，共 %d 个文本块", filename, len(chunks))
        return len(chunks)

    def load_all_txt_files(self) -> int:
        """加载txt目录下所有文件"""
        total_chunks = 0
        txt_files = [f for f in os.listdir(self.txt_dir) if f.endswith(".txt")]

        if not txt_files:
            logger.warning("知识库目录为空: %s", self.txt_dir)
            return 0

        logger.info("正在加载知识库文件 (%d 个)...", len(txt_files))
        for filename in txt_files:
            filepath = os.path.join(self.txt_dir, filename)
            chunks = self.load_txt_file(filepath)
            total_chunks += chunks

        logger.info("知识库加载完成，共 %d 个文件，%d 个文本块", len(txt_files), total_chunks)
        return total_chunks

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """搜索知识库"""
        results = self.vector_manager.similarity_search(query, k=k)
        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": round(score, 4)
            }
            for doc, score in results
        ]

    def list_files(self) -> List[str]:
        """列出已加载的文件"""
        results = self.vector_manager.get_all()
        if not results or not results.get("metadatas"):
            return []
        return list(set(
            m.get("filename", "unknown")
            for m in results["metadatas"] if m
        ))