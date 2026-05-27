"""向量存储管理器"""
from typing import List, Dict, Optional
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import config


class VectorStoreManager:
    """向量存储管理器 - 封装Chroma操作"""

    def __init__(self, persist_directory: str, collection_name: str):
        """
        Args:
            persist_directory: 持久化目录
            collection_name: 集合名称
        """
        self.embeddings = OllamaEmbeddings(
            model=config.EMBEDDING_MODEL,
            base_url=config.OLLAMA_BASE_URL
        )
        self.collection_name = collection_name
        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )

    def add_texts(self, texts: List[str], metadatas: List[Dict], ids: List[str]):
        """批量添加文本"""
        self.vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)

    def similarity_search(self, query: str, k: int = 5, filter: Optional[Dict] = None):
        """语义相似度搜索（带分数）"""
        return self.vectorstore.similarity_search_with_score(
            query, k=k, filter=filter
        )

    def get_all(self, filter: Optional[Dict] = None):
        """获取所有数据"""
        return self.vectorstore.get(where=filter)

    def delete_by_filter(self, filter: Dict):
        """按条件删除"""
        results = self.vectorstore.get(where=filter)
        if results.get("ids"):
            self.vectorstore.delete(ids=results["ids"])

    def as_retriever(self, k: int = 5, filter: Optional[Dict] = None):
        """转换为检索器"""
        search_kwargs = {"k": k}
        if filter:
            search_kwargs["filter"] = filter
        return self.vectorstore.as_retriever(search_kwargs=search_kwargs)