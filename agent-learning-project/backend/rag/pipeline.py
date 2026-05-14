"""
RAG管道模块
完整的RAG处理流程
"""

from typing import Any, Dict, List, Optional
from pathlib import Path


class RAGPipeline:
    """
    RAG处理管道

    完整的检索增强生成流程：
    1. 文档加载和分割
    2. 向量化存储
    3. 检索
    4. 增强生成
    """

    def __init__(
        self,
        embedder_provider: str = "openai",
        persist_dir: str = "./data/rag",
        collection_name: str = "rag_documents",
    ):
        """
        初始化RAG管道

        Args:
            embedder_provider: 嵌入模型提供商
            persist_dir: 持久化目录
            collection_name: 集合名称
        """
        from backend.rag.embeddings import EmbedderFactory
        from backend.rag.vectorstore import VectorStore
        from backend.rag.retriever import RAGRetriever

        # 创建嵌入器
        self.embedder = EmbedderFactory.create(embedder_provider)

        # 创建向量存储
        self.vector_store = VectorStore(
            persist_dir=persist_dir,
            collection_name=collection_name,
            embedding_dimension=self.embedder.get_dimension(),
        )

        # 创建检索器
        self.retriever = RAGRetriever(
            vector_store=self.vector_store,
            embedder=self.embedder,
        )

    async def add_document(
        self,
        path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        添加文档

        Args:
            path: 文档路径
            metadata: 元数据

        Returns:
            添加结果
        """
        return await self.retriever.add_document(path, metadata=metadata)

    async def add_directory(
        self,
        directory: str,
        pattern: str = "*.pdf",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        批量添加目录中的文档

        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            metadata: 通用元数据

        Returns:
            添加结果统计
        """
        dir_path = Path(directory)
        files = list(dir_path.glob(pattern))

        results = {
            "total_files": len(files),
            "successful": 0,
            "failed": 0,
            "errors": [],
        }

        for file_path in files:
            try:
                file_meta = {**metadata} if metadata else {}
                file_meta["filename"] = file_path.name

                await self.add_document(str(file_path), metadata=file_meta)
                results["successful"] += 1

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "file": str(file_path),
                    "error": str(e),
                })

        return results

    async def query(
        self,
        question: str,
        llm,
        top_k: int = 5,
        context_only: bool = False,
    ) -> Dict[str, Any]:
        """
        RAG查询

        Args:
            question: 问题
            llm: LLM客户端
            top_k: 检索文档数量
            context_only: 是否只返回检索结果

        Returns:
            答案和来源
        """
        # 检索相关文档
        results = await self.retriever.retrieve(question, top_k=top_k)

        if not results:
            return {
                "answer": "未找到相关文档。",
                "sources": [],
            }

        # 构建上下文
        context = self._format_context(results)

        if context_only:
            return {
                "context": context,
                "sources": [r["metadata"] for r in results],
            }

        # 构建提示词
        prompt = self._build_prompt(question, context)

        # 生成答案
        from backend.llm.models import Message
        response = await llm.chat([
            Message(role="system", content=self._get_system_prompt()),
            Message(role="user", content=prompt),
        ])

        return {
            "answer": response.content,
            "sources": [
                {
                    "content": r["content"][:200] + "...",
                    "metadata": r["metadata"],
                    "score": r["score"],
                }
                for r in results
            ],
            "usage": response.usage.model_dump(),
        }

    def _format_context(self, results: List[Dict[str, Any]]) -> str:
        """格式化检索结果为上下文"""
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", result["metadata"].get("filename", "未知"))
            score = result["score"]
            content = result["content"]
            context_parts.append(
                f"[参考文档{i}] 来源: {source} (相关度: {score:.2f})\n{content}"
            )
        return "\n\n".join(context_parts)

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        return """你是一个智能问答助手。请基于提供的参考文档回答用户问题。

要求：
1. 答案必须基于参考文档，不要编造信息
2. 如果参考文档中没有相关信息，明确告知用户
3. 引用具体的文档来源
4. 答案要准确、简洁、有条理"""

    def _build_prompt(self, question: str, context: str) -> str:
        """构建查询提示词"""
        return f"""参考文档：

{context}

用户问题：{question}

请基于上述参考文档回答用户问题。"""

    def get_stats(self) -> Dict[str, Any]:
        """获取RAG系统统计信息"""
        return {
            "vector_store": self.vector_store.get_stats(),
            "embedder": {
                "type": self.embedder.__class__.__name__,
                "dimension": self.embedder.get_dimension(),
            },
        }

    def clear(self) -> None:
        """清空所有文档"""
        self.vector_store.clear()
