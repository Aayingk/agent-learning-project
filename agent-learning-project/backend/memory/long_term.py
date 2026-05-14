"""
长期记忆模块
基于向量存储的语义记忆
"""

import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime

from backend.llm.models import Message

if TYPE_CHECKING:
    from backend.memory.short_term import ShortTermMemory


class LongTermMemory:
    """
    长期记忆管理器

    使用向量存储实现语义检索的记忆系统。
    支持：
    - 存储对话片段
    - 语义检索相关记忆
    - 记忆过期和清理
    """

    def __init__(
        self,
        persist_dir: str = "./data/chroma",
        collection_name: str = "agent_memory",
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        初始化长期记忆

        Args:
            persist_dir: ChromaDB持久化目录
            collection_name: 集合名称
            embedding_model: 嵌入模型名称
        """
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        # 延迟初始化（第一次使用时才创建）
        self._client = None
        self._collection = None
        self._embedder = None

    def _init_chroma(self):
        """延迟初始化ChromaDB"""
        if self._client is not None:
            return

        try:
            import chromadb
            from chromadb.config import Settings

            # 确保目录存在
            os.makedirs(self.persist_dir, exist_ok=True)

            # 创建客户端
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
                metadata={"hnsw:space": "cosine"},
            )

        except Exception as e:
            raise RuntimeError(f"ChromaDB初始化失败: {e}")

    def _init_embedder(self):
        """延迟初始化嵌入模型"""
        if self._embedder is not None:
            return

        try:
            # 尝试使用OpenAI嵌入
            from backend.llm import LLMFactory

            llm = LLMFactory.create("openai")
            self._embedder = llm

        except Exception:
            # 回退到简单实现
            self._embedder = None

    async def add(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
    ) -> str:
        """
        添加记忆

        Args:
            content: 记忆内容
            metadata: 附加元数据
            session_id: 会话ID

        Returns:
            记忆ID
        """
        self._init_chroma()
        self._init_embedder()

        # 生成唯一ID
        memory_id = f"mem_{datetime.now().timestamp()}"

        # 准备元数据
        meta = metadata or {}
        meta["created_at"] = datetime.now().isoformat()
        if session_id:
            meta["session_id"] = session_id

        # 生成嵌入
        embedding = await self._get_embedding(content)

        # 添加到集合
        self._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta],
        )

        return memory_id

    async def add_conversation(
        self,
        messages: List[Message],
        session_id: str,
    ) -> List[str]:
        """
        添加对话记忆

        将对话中的重要片段存储为长期记忆

        Args:
            messages: 消息列表
            session_id: 会话ID

        Returns:
            记忆ID列表
        """
        memory_ids = []

        for msg in messages:
            # 只存储有意义的消息
            if msg.role in ["user", "assistant"] and len(msg.content) > 10:
                memory_id = await self.add(
                    content=msg.content,
                    metadata={
                        "role": msg.role,
                        "type": "conversation",
                    },
                    session_id=session_id,
                )
                memory_ids.append(memory_id)

        return memory_ids

    async def search(
        self,
        query: str,
        top_k: int = 5,
        session_id: Optional[str] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        语义搜索记忆

        Args:
            query: 查询文本
            top_k: 返回结果数量
            session_id: 限制在特定会话中搜索
            min_score: 最小相似度阈值

        Returns:
            结果列表，每项包含 content, score, metadata
        """
        self._init_chroma()
        self._init_embedder()

        # 生成查询嵌入
        query_embedding = await self._get_embedding(query)

        # 构建过滤条件
        where = None
        if session_id:
            where = {"session_id": session_id}

        # 搜索
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
        )

        # 解析结果
        memories = []
        if results["ids"] and results["ids"][0]:
            for i, memory_id in enumerate(results["ids"][0]):
                # 计算相似度分数（Chroma返回的是距离，需要转换）
                distance = results["distances"][0][i] if results.get("distances") else 0
                score = 1 - distance  # 转换为相似度

                if score < min_score:
                    continue

                memories.append({
                    "id": memory_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": score,
                })

        return memories

    async def get_all(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有记忆

        Args:
            session_id: 限制在特定会话

        Returns:
            所有记忆列表
        """
        self._init_chroma()

        where = None
        if session_id:
            where = {"session_id": session_id}

        results = self._collection.get(where=where)

        memories = []
        if results["ids"]:
            for i, memory_id in enumerate(results["ids"]):
                memories.append({
                    "id": memory_id,
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i],
                })

        return memories

    def clear(self, session_id: Optional[str] = None) -> int:
        """
        清除记忆

        Args:
            session_id: 清除特定会话的记忆，None表示清除全部

        Returns:
            清除的数量
        """
        self._init_chroma()

        if session_id:
            # 获取该会话的所有记忆ID
            results = self._collection.get(
                where={"session_id": session_id}
            )
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                return len(results["ids"])
            return 0
        else:
            # 清除所有
            count = self._collection.count()
            self._client.delete_collection(name=self.collection_name)
            self._collection = None
            return count

    async def _get_embedding(self, text: str) -> List[float]:
        """
        获取文本嵌入向量

        Args:
            text: 文本

        Returns:
            嵌入向量
        """
        if self._embedder is not None:
            # 使用LLM客户端的嵌入功能
            response = await self._embedder.embed([text])
            return response.embeddings[0]
        else:
            # 简单实现：使用字符编码（不推荐生产使用）
            # 生产环境应该使用真正的嵌入模型
            import hashlib
            import numpy as np

            # 使用hash生成伪向量（仅用于演示）
            hash_obj = hashlib.sha256(text.encode())
            hash_bytes = hash_obj.digest()

            # 扩展到固定维度
            vector = np.zeros(1536)  # OpenAI嵌入维度
            for i, b in enumerate(hash_bytes):
                vector[i * 4] = b / 255.0
                vector[i * 4 + 1] = (b >> 2) / 255.0
                vector[i * 4 + 2] = (b >> 4) / 255.0
                vector[i * 4 + 3] = (b >> 6) / 255.0

            return vector.tolist()

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        self._init_chroma()

        return {
            "collection_name": self.collection_name,
            "total_memories": self._collection.count(),
            "persist_dir": self.persist_dir,
        }


class MemoryManager:
    """
    记忆管理器

    统一管理短期和长期记忆
    """

    def __init__(
        self,
        short_term: Optional["ShortTermMemory"] = None,
        long_term: Optional[LongTermMemory] = None,
    ):
        """
        初始化记忆管理器

        Args:
            short_term: 短期记忆实例
            long_term: 长期记忆实例
        """
        if short_term is None:
            from backend.memory.short_term import ShortTermMemory
            self.short_term = ShortTermMemory()
        else:
            self.short_term = short_term

        self.long_term = long_term or LongTermMemory()

    async def add_message(
        self,
        session_id: str,
        message: Message,
        store_long_term: bool = False,
    ) -> None:
        """
        添加消息

        Args:
            session_id: 会话ID
            message: 消息
            store_long_term: 是否同时存储到长期记忆
        """
        self.short_term.add_message(session_id, message)

        if store_long_term:
            await self.long_term.add(
                content=message.content,
                metadata={"role": message.role},
                session_id=session_id,
            )

    def get_context(
        self,
        session_id: str,
        include_long_term: bool = False,
        long_term_query: Optional[str] = None,
        max_long_term: int = 3,
    ) -> List[Message]:
        """
        获取完整上下文

        Args:
            session_id: 会话ID
            include_long_term: 是否包含长期记忆
            long_term_query: 长期记忆查询文本
            max_long_term: 最多包含的长期记忆数量

        Returns:
            上下文消息列表
        """
        messages = self.short_term.get_messages(session_id)

        # 添加长期记忆
        if include_long_term and long_term_query:
            import asyncio
            memories = asyncio.run(self.long_term.search(
                query=long_term_query,
                top_k=max_long_term,
                session_id=session_id,
            ))

            # 将记忆转换为消息
            for mem in memories:
                messages.insert(
                    0,
                    Message(
                        role="system",
                        content=f"[相关记忆] {mem['content']}",
                        metadata={"source": "long_term_memory", "score": mem["score"]},
                    ),
                )

        return messages

    def clear_session(self, session_id: str) -> None:
        """清除会话的所有记忆"""
        self.short_term.clear_session(session_id)
        self.long_term.clear(session_id)
