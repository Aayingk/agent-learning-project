"""
嵌入模型模块
提供文本向量化功能
"""

from typing import List, Optional
from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """嵌入模型抽象基类"""

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        生成文本嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """
    OpenAI嵌入模型

    支持模型：
    - text-embedding-3-small (1536维)
    - text-embedding-3-large (3072维)
    - text-embedding-ada-002 (1536维)
    """

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: Optional[str] = None,
    ):
        from backend.llm import LLMFactory

        self.llm = LLMFactory.create("openai", model=model)
        self.model = model

    async def embed(self, texts: List[str]) -> List[List[float]]:
        response = await self.llm.embed(texts)
        return response.embeddings

    def get_dimension(self) -> int:
        if "3-large" in self.model:
            return 3072
        return 1536


class SentenceTransformerEmbedder(BaseEmbedder):
    """
    Sentence Transformer嵌入模型

    本地运行的开源嵌入模型
    支持多种模型如 all-MiniLM-L6-v2, paraphrase-multilingual-MiniLM-L12-v2
    """

    def __init__(
        self,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(
                self.model_name,
                device=self.device,
            )

    async def embed(self, texts: List[str]) -> List[List[float]]:
        self._load_model()
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def get_dimension(self) -> int:
        self._load_model()
        return self._model.get_sentence_embedding_dimension()


class EmbedderFactory:
    """
    嵌入模型工厂

    根据配置创建合适的嵌入器
    """

    @staticmethod
    def create(
        provider: str = "openai",
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseEmbedder:
        """
        创建嵌入器

        Args:
            provider: 提供商 (openai, sentence_transformer)
            model: 模型名称
            **kwargs: 其他参数

        Returns:
            嵌入器实例
        """
        if provider == "openai":
            return OpenAIEmbedder(model=model or "text-embedding-3-small")
        elif provider in ["sentence_transformer", "local"]:
            return SentenceTransformerEmbedder(
                model_name=model or "paraphrase-multilingual-MiniLM-L12-v2",
                **kwargs,
            )
        else:
            raise ValueError(f"不支持的嵌入提供商: {provider}")
