"""混合检索记忆存储：向量 + BM25关键词"""
from typing import List, Dict, Optional
from datetime import datetime
from rank_bm25 import BM25Okapi
import jieba
from .vector_store import VectorStoreManager
import config


class HybridMemoryStore:
    """混合检索记忆存储"""

    def __init__(self, persist_directory: str = None):
        if persist_directory is None:
            persist_directory = config.MEMORY_DB_DIR

        # 向量存储
        self.vector_manager = VectorStoreManager(
            persist_directory=persist_directory,
            collection_name="long_term_memory"
        )

        # BM25所需的内存列表
        self.documents: List[str] = []
        self.metadatas: List[Dict] = []
        self._load_from_disk()

    def _tokenize(self, text: str) -> List[str]:
        """中文分词"""
        return list(jieba.cut(text))

    def _load_from_disk(self):
        """从磁盘加载已有记忆到内存"""
        results = self.vector_manager.get_all()
        if results and results.get("documents"):
            self.documents = list(results["documents"])
            self.metadatas = list(results.get("metadatas", [{}] * len(self.documents)))

    def add_memory(self, user_id: str, content: str,
                   memory_type: str = "general",
                   metadata: Optional[Dict] = None) -> str:
        """
        添加一条长期记忆

        Args:
            user_id: 用户标识
            content: 记忆内容
            memory_type: 类型(fact/preference/event/general)
            metadata: 额外元数据

        Returns:
            记忆ID
        """
        if metadata is None:
            metadata = {}

        full_metadata = {
            "user_id": user_id,
            "memory_type": memory_type,
            "timestamp": datetime.now().isoformat(),
            "source": "conversation",  # 标记来源为对话
            **metadata
        }

        doc_id = f"{user_id}_{datetime.now().timestamp()}"

        # 存入向量库
        self.vector_manager.add_texts(
            texts=[content],
            metadatas=[full_metadata],
            ids=[doc_id]
        )

        # 同步内存
        self.documents.append(content)
        self.metadatas.append(full_metadata)

        return doc_id

    def hybrid_search(self, query: str, user_id: str,
                      k: int = None, alpha: float = None) -> List[Dict]:
        """
        混合检索

        Args:
            query: 查询文本
            user_id: 用户标识
            k: 返回数量
            alpha: 融合权重
        """
        if k is None:
            k = config.HYBRID_SEARCH_K
        if alpha is None:
            alpha = config.HYBRID_SEARCH_ALPHA

        # 获取该用户的记忆索引
        user_indices = [
            i for i, meta in enumerate(self.metadatas)
            if meta and meta.get("user_id") == user_id
        ]

        if not user_indices:
            return []

        # 1. 向量语义检索
        vector_results = self.vector_manager.similarity_search(
            query, k=k * 2, filter={"user_id": user_id}
        )

        # 2. BM25关键词检索
        user_texts = [self.documents[i] for i in user_indices]
        tokenized_docs = [self._tokenize(doc) for doc in user_texts]
        tokenized_query = self._tokenize(query)

        bm25 = BM25Okapi(tokenized_docs)
        bm25_scores = bm25.get_scores(tokenized_query)

        bm25_ranked = sorted(
            [(user_indices[i], bm25_scores[i]) for i in range(len(user_texts))],
            key=lambda x: x[1], reverse=True
        )[:k * 2]

        # 3. RRF融合
        fused_scores = {}

        for rank, (doc, _) in enumerate(vector_results):
            doc_id = doc.page_content[:100]
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + alpha * (1.0 / (rank + 60))

        for rank, (idx, _) in enumerate(bm25_ranked):
            doc_id = self.documents[idx][:100]
            fused_scores[doc_id] = fused_scores.get(doc_id, 0) + (1 - alpha) * (1.0 / (rank + 60))

        sorted_results = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:k]

        # 4. 构造返回
        results = []
        for doc_id, score in sorted_results:
            for doc, _ in vector_results:
                if doc.page_content[:100] == doc_id:
                    results.append({
                        "content": doc.page_content,
                        "metadata": doc.metadata,
                        "score": round(score, 4)
                    })
                    break

        return results

    def get_user_memories(self, user_id: str) -> List[Dict]:
        """获取用户所有记忆"""
        results = self.vector_manager.get_all(filter={"user_id": user_id})
        memories = []
        if results and results.get("documents"):
            for text, meta in zip(results["documents"], results.get("metadatas", [])):
                memories.append({
                    "content": text,
                    "metadata": meta or {}
                })
        return memories

    def delete_user_memories(self, user_id: str):
        """删除用户所有记忆"""
        self.vector_manager.delete_by_filter({"user_id": user_id})
        keep = [i for i, m in enumerate(self.metadatas) if m.get("user_id") != user_id]
        self.documents = [self.documents[i] for i in keep]
        self.metadatas = [self.metadatas[i] for i in keep]