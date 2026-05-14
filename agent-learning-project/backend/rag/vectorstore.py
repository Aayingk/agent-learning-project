"""
向量存储模块
基于ChromaDB的向量数据库
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime


class VectorStore:
    """
    向量存储管理器

    基于ChromaDB实现向量存储和检索
    """

    def __init__(
        self,
        persist_dir: str = "./data/vectorstore",
        collection_name: str = "documents",
        embedding_dimension: int = 1536,
    ):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化目录
            collection_name: 集合名称
            embedding_dimension: 嵌入向量维度
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_dimension = embedding_dimension

        # 确保目录存在
        os.makedirs(persist_dir, exist_ok=True)

        # 延迟初始化
        self._client = None
        self._collection = None

    def _init_client(self):
        """延迟初始化ChromaDB客户端"""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            self._client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )

            # 获取或创建集合
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "hnsw:space": "cosine",
                    "dimension": self.embedding_dimension,
                },
            )

        except Exception as e:
            raise RuntimeError(f"ChromaDB初始化失败: {e}")

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档

        Args:
            documents: 文档内容列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表
            ids: 文档ID列表（可选）

        Returns:
            文档ID列表
        """
        self._init_client()

        # 生成ID
        if ids is None:
            ids = [
                f"doc_{datetime.now().timestamp()}_{i}"
                for i in range(len(documents))
            ]

        # 准备元数据
        if metadatas is None:
            metadatas = [{} for _ in documents]

        for i, meta in enumerate(metadatas):
            meta.setdefault("created_at", datetime.now().isoformat())

        # 添加到集合
        self._collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        向量搜索

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            where: 元数据过滤条件
            where_document: 文档内容过滤条件

        Returns:
            搜索结果列表
        """
        self._init_client()

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            where_document=where_document,
        )

        # 解析结果
        documents = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                # 计算相似度分数
                distance = results["distances"][0][i] if results.get("distances") else 0
                score = 1 - distance  # 转换为相似度

                documents.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": score,
                })

        return documents

    def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取文档

        Args:
            ids: 文档ID列表
            where: 元数据过滤条件
            limit: 返回数量限制

        Returns:
            文档列表
        """
        self._init_client()

        results = self._collection.get(
            ids=ids,
            where=where,
            limit=limit,
        )

        documents = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                documents.append({
                    "id": doc_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })

        return documents

    def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        删除文档

        Args:
            ids: 文档ID列表
            where: 元数据过滤条件

        Returns:
            删除数量
        """
        self._init_client()

        if ids:
            self._collection.delete(ids=ids)
            return len(ids)
        elif where:
            # 先获取要删除的ID
            results = self._collection.get(where=where)
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                return len(results["ids"])
            return 0
        else:
            count = self._collection.count()
            self._client.delete_collection(name=self.collection_name)
            self._collection = None
            return count

    def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        更新文档

        Args:
            ids: 文档ID列表
            documents: 新文档内容
            embeddings: 新嵌入向量
            metadatas: 新元数据
        """
        self._init_client()

        kwargs = {}
        if documents is not None:
            kwargs["documents"] = documents
        if embeddings is not None:
            kwargs["embeddings"] = embeddings
        if metadatas is not None:
            kwargs["metadatas"] = metadatas

        self._collection.update(ids=ids, **kwargs)

    def count(self) -> int:
        """获取文档数量"""
        self._init_client()
        return self._collection.count()

    def clear(self) -> None:
        """清空所有文档"""
        self._init_client()
        self._client.delete_collection(name=self.collection_name)
        self._collection = None

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        self._init_client()

        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_dir": self.persist_dir,
            "embedding_dimension": self.embedding_dimension,
        }
