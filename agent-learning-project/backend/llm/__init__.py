"""LLM backend module."""

from importlib import import_module

from backend.llm.base import BaseLLM, LLMError
from backend.llm.models import (
    Message,
    ChatResponse,
    EmbeddingResponse,
    ToolDefinition,
    ToolCall,
    FunctionDefinition,
    TokenUsage,
)
from backend.llm.factory import LLMFactory

_CLIENT_EXPORTS = {
    "OpenAILLM": "backend.llm.openai_client",
    "AnthropicLLM": "backend.llm.anthropic_client",
    "OllamaLLM": "backend.llm.ollama_client",
    "GLMLLM": "backend.llm.glm_client",
    "DeepSeekLLM": "backend.llm.deepseek_client",
}

__all__ = [
    "BaseLLM",
    "LLMError",
    "Message",
    "ChatResponse",
    "EmbeddingResponse",
    "ToolDefinition",
    "ToolCall",
    "FunctionDefinition",
    "TokenUsage",
    "LLMFactory",
    *sorted(_CLIENT_EXPORTS),
]


def __getattr__(name: str):
    if name not in _CLIENT_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(_CLIENT_EXPORTS[name])
    value = getattr(module, name)
    globals()[name] = value
    return value