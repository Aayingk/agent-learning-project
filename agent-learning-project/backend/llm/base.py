"""
LLM抽象基类
定义所有LLM提供商必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from backend.llm.models import (
    ChatResponse,
    EmbeddingResponse,
    Message,
    ToolDefinition,
)


class BaseLLM(ABC):
    """
    LLM抽象基类

    所有LLM提供商（OpenAI、Anthropic、Ollama等）都需要实现这个接口。
    这样可以在上层代码中统一调用，不需要关心具体是哪个LLM。
    """

    def __init__(
        self,
        model: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        """
        初始化LLM客户端

        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            **kwargs: 其他提供商特定参数
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.extra_params = kwargs

    @abstractmethod
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            tools: 可用的工具定义列表（用于function calling）
            temperature: 温度参数（0-1，越高越随机）
            max_tokens: 最大生成token数
            **kwargs: 其他参数

        Returns:
            ChatResponse: 包含回复内容、tool_calls、token使用等
        """
        pass

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """
        生成文本嵌入向量

        Args:
            texts: 要嵌入的文本列表
            **kwargs: 其他参数

        Returns:
            EmbeddingResponse: 包含嵌入向量和token使用
        """
        pass

    def supports_tools(self) -> bool:
        """此LLM是否支持工具调用"""
        return True

    def supports_embedding(self) -> bool:
        """此LLM是否支持嵌入"""
        return True

    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "provider": self.__class__.__name__,
            "model": self.model,
            "base_url": self.base_url,
            "supports_tools": self.supports_tools(),
            "supports_embedding": self.supports_embedding(),
        }


class LLMError(Exception):
    """LLM调用错误基类"""

    def __init__(self, message: str, provider: str, details: Optional[Dict] = None):
        self.message = message
        self.provider = provider
        self.details = details or {}
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMError):
    """速率限制错误"""


class LLMTimeoutError(LLMError):
    """超时错误"""


class LLMInvalidRequestError(LLMError):
    """无效请求错误"""


class LLMAuthenticationError(LLMError):
    """认证错误"""
