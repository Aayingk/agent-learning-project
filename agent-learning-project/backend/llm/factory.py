"""
LLM factory.

Provider clients are imported lazily so an optional SDK that is not installed
(for example zhipuai for GLM) does not break imports for every other provider.
"""

from importlib import import_module
from typing import Optional

from backend.llm.base import BaseLLM
from config.settings import settings


class LLMFactory:
    """Create LLM clients from provider names."""

    _provider_paths = {
        "openai": "backend.llm.openai_client.OpenAILLM",
        "anthropic": "backend.llm.anthropic_client.AnthropicLLM",
        "ollama": "backend.llm.ollama_client.OllamaLLM",
        "glm": "backend.llm.glm_client.GLMLLM",
        "deepseek": "backend.llm.deepseek_client.DeepSeekLLM",
    }
    _providers: dict[str, type[BaseLLM]] = {}

    @classmethod
    def _load_provider(cls, provider: str) -> type[BaseLLM]:
        if provider in cls._providers:
            return cls._providers[provider]

        import_path = cls._provider_paths[provider]
        module_name, class_name = import_path.rsplit(".", 1)
        try:
            module = import_module(module_name)
            llm_class = getattr(module, class_name)
        except ImportError as exc:
            raise ImportError(
                f"Provider '{provider}' is not available because an optional dependency is missing: {exc}"
            ) from exc

        if not issubclass(llm_class, BaseLLM):
            raise TypeError(f"{llm_class} must inherit from BaseLLM")

        cls._providers[provider] = llm_class
        return llm_class

    @classmethod
    def create(
        cls,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> BaseLLM:
        """Create an LLM client instance."""
        if provider is None:
            provider = settings.default_llm_provider

        if provider not in cls._provider_paths and provider not in cls._providers:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: {cls.list_providers()}"
            )

        credentials = settings.get_llm_credentials(provider)
        if model is None:
            model = credentials.get("model")

        merged_kwargs = {**credentials, **kwargs}
        merged_kwargs.pop("model", None)

        llm_class = cls._load_provider(provider)
        return llm_class(model=model, **merged_kwargs)

    @classmethod
    def register_provider(cls, name: str, llm_class: type[BaseLLM]):
        """Register a custom LLM provider class."""
        if not issubclass(llm_class, BaseLLM):
            raise TypeError(f"{llm_class} must inherit from BaseLLM")
        cls._providers[name] = llm_class

    @classmethod
    def list_providers(cls) -> list[str]:
        """List registered and built-in provider names."""
        return sorted(set(cls._provider_paths) | set(cls._providers))