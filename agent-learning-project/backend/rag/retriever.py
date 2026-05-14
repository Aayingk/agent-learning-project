"""
RAG检索器模块
实现检索增强生成
"""

from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path


class DocumentLoader:
    """
    文档加载器

    支持多种文档格式
    """

    @staticmethod
    def load_text(path: str) -> str:
        """加载纯文本文件"""
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def load_pdf(path: str) -> str:
        """加载PDF文件"""
        try:
            import pypdf

            text = ""
            with open(path, "rb") as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except ImportError:
            raise ImportError("pypdf未安装，请运行: uv add pypdf")

    @staticmethod
    def load_markdown(path: str) -> str:
        """加载Markdown文件"""
        return DocumentLoader.load_text(path)

    @staticmethod
    def load_docx(path: str) -> str:
        """加载Word文档"""
        try:
            from docx import Document

            doc = Document(path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            raise ImportError("python-docx未安装，请运行: uv add python-docx")

    @staticmethod
    def load(path: str) -> str:
        """
        自动检测并加载文档

        Args:
            path: 文件路径

        Returns:
            文档内容
        """
        path_obj = Path(path)

        if not path_obj.exists():
            raise FileNotFoundError(f"文件不存在: {path}")

        suffix = path_obj.suffix.lower()

        loaders = {
            ".txt": DocumentLoader.load_text,
            ".md": DocumentLoader.load_markdown,
            ".pdf": DocumentLoader.load_pdf,
            ".docx": DocumentLoader.load_docx,
            ".doc": DocumentLoader.load_docx,
        }

        loader = loaders.get(suffix)
        if loader is None:
            raise ValueError(f"不支持的文件格式: {suffix}")

        return loader(path)


class DocumentSplitter:
    """
    文档分割器

    将长文档分割为适合嵌入的块
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n\n",
    ):
        """
        初始化分割器

        Args:
            chunk_size: 块大小（字符数）
            chunk_overlap: 块之间重叠大小
            separator: 分隔符
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separator = separator

    def split(self, text: str) -> List[str]:
        """
        分割文档

        Args:
            text: 文档内容

        Returns:
            文档块列表
        """
        # 按分隔符分割
        sections = text.split(self.separator)
        chunks = []
        current_chunk = ""
        current_size = 0

        for section in sections:
            section = section.strip()
            if not section:
                continue

            section_size = len(section)

            # 如果当前块加上新部分会超限
            if current_size + section_size > self.chunk_size and current_chunk:
                chunks.append(current_chunk)
                # 保留重叠部分
                overlap = current_chunk[-self.chunk_overlap:] if self.chunk_overlap > 0 else ""
                current_chunk = overlap
                current_size = len(overlap)

            # 添加分隔符和内容
            if current_chunk:
                current_chunk += self.separator + section
            else:
                current_chunk = section
            current_size = len(current_chunk)

        # 添加最后一个块
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def split_documents(self, texts: List[str]) -> List[Tuple[str, int]]:
        """
        批量分割文档

        Args:
            texts: 文档内容列表

        Returns:
            (文档块, 原文档索引)列表
        """
        all_chunks = []
        for doc_idx, text in enumerate(texts):
            chunks = self.split(text)
            for chunk in chunks:
                all_chunks.append((chunk, doc_idx))
        return all_chunks


class RAGRetriever:
    """
    RAG检索器

    实现检索增强生成的核心逻辑
    """

    def __init__(
        self,
        vector_store,
        embedder,
        top_k: int = 5,
        score_threshold: float = 0.7,
    ):
        """
        初始化检索器

        Args:
            vector_store: 向量存储实例
            embedder: 嵌入模型实例
            top_k: 检索结果数量
            score_threshold: 相似度阈值
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.top_k = top_k
        self.score_threshold = score_threshold

    async def add_document(
        self,
        path: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        添加文档到向量库

        Args:
            path: 文档路径
            metadata: 附加元数据
            chunk_size: 分块大小

        Returns:
            添加结果统计
        """
        # 加载文档
        content = DocumentLoader.load(path)

        # 分割文档
        splitter = DocumentSplitter(chunk_size=chunk_size)
        chunks = splitter.split(content)

        # 生成嵌入
        embeddings = await self.embedder.embed(chunks)

        # 准备元数据
        metadatas = []
        for i, chunk in enumerate(chunks):
            meta = {
                "source": path,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)

        # 添加到向量库
        ids = self.vector_store.add_documents(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return {
            "path": path,
            "chunks_added": len(chunks),
            "ids": ids,
        }

    async def add_texts(
        self,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> List[str]:
        """
        添加文本到向量库

        Args:
            texts: 文本列表
            metadatas: 元数据列表

        Returns:
            文档ID列表
        """
        # 生成嵌入
        embeddings = await self.embedder.embed(texts)

        # 添加到向量库
        return self.vector_store.add_documents(
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回数量
            score_threshold: 相似度阈值
            where: 元数据过滤

        Returns:
            检索结果列表
        """
        top_k = top_k or self.top_k
        score_threshold = score_threshold or self.score_threshold

        # 生成查询嵌入
        query_embeddings = await self.embedder.embed([query])
        query_embedding = query_embeddings[0]

        # 搜索
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where,
        )

        # 过滤低分结果
        filtered = [
            r for r in results
            if r["score"] >= score_threshold
        ]

        return filtered

    async def retrieve_and_format(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> str:
        """
        检索并格式化为上下文文本

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            格式化的上下文
        """
        results = await self.retrieve(query, top_k=top_k)

        if not results:
            return "未找到相关文档。"

        context_parts = []
        for i, result in enumerate(results, 1):
            source = result["metadata"].get("source", "未知来源")
            score = result["score"]
            content = result["content"]
            context_parts.append(
                f"[文档{i}] 来源: {source} (相关度: {score:.2f})\n{content}"
            )

        return "\n\n".join(context_parts)
