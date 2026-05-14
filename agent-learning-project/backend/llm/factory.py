"""
LLM工厂类
根据配置创建相应的LLM客户端实例
"""

from typing import Optional

from backend.llm.base import BaseLLM
from backend.llm.openai_client import OpenAILLM
from backend.llm.anthropic_client import AnthropicLLM
from backend.llm.ollama_client import OllamaLLM
from backend.llm.glm_client import GLMLLM
from backend.llm.deepseek_client import DeepSeekLLM
from config.settings import settings


class LLMFactory:
    """
    LLM工厂类

    根据提供商名称创建对应的LLM客户端实例。
    支持的提供商：openai, anthropic, ollama, glm, deepseek
    """

    _providers = {
        "openai": OpenAILLM,
        "anthropic": AnthropicLLM,
        "ollama": OllamaLLM,
        "glm": GLMLLM,
        "deepseek": DeepSeekLLM,
    }

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseLLM:
        """
        创建LLM客户端实例

        Args:
            provider: 提供商名称（openai/anthropic/ollama/glm/deepseek）
                     如果不指定，使用配置文件中的默认提供商
            model: 模型名称，如果不指定使用默认模型
            **kwargs: 其他传递给LLM客户端的参数

        Returns:
            BaseLLM: LLM客户端实例

        Raises:
            ValueError: 不支持的提供商
        """
        # 使用默认提供商
        if provider is None:
            provider = settings.default_llm_provider

        # 检查提供商是否支持
        if provider not in cls._providers:
            raise ValueError(
                f"不支持的LLM提供商: {provider}. "
                f"支持的提供商: {list(cls._providers.keys())}"
            )

        # 获取凭据
        credentials = settings.get_llm_credentials(provider)

        # 确定模型名称
        if model is None:
            model = credentials.get("model")

        # 合并参数，排除model避免重复传递
        merged_kwargs = {**credentials, **kwargs}
        merged_kwargs.pop("model", None)

        # 创建实例
        llm_class = cls._providers[provider]
        return llm_class(model=model, **merged_kwargs)

    @classmethod
    def register_provider(cls, name: str, llm_class: type):
        """
        注册新的LLM提供商

        Args:
            name: 提供商名称
            llm_class: LLM客户端类（必须继承BaseLLM）
        """
        if not issubclass(llm_class, BaseLLM):
            raise TypeError(f"{llm_class} 必须继承 BaseLLM")
        cls._providers[name] = llm_class

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有已注册的提供商"""
        return list(cls._providers.keys())
