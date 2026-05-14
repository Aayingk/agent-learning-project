"""
DeepSeek LLM客户端
实现DeepSeek API的调用
"""

from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

from backend.llm.base import (
    BaseLLM,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMAuthenticationError,
    LLMInvalidRequestError,
)
from backend.llm.models import (
    ChatResponse,
    EmbeddingResponse,
    Message,
    TokenUsage,
    ToolCall,
    ToolDefinition,
    FunctionDefinition,
)


class DeepSeekLLM(BaseLLM):
    """
    DeepSeek LLM客户端

    支持模型：
    - deepseek-chat: 通用对话模型
    - deepseek-coder: 代码模型

    DeepSeek使用OpenAI兼容的API，文档: https://platform.deepseek.com/api-docs/
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        timeout: int = 60,
        max_retries: int = 2,
        **kwargs,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)
        self.timeout = timeout
        self.max_retries = max_retries

        # 使用OpenAI SDK连接DeepSeek
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """发送聊天请求到DeepSeek"""
        try:
            # 转换消息格式
            api_messages = self._convert_messages(messages)

            # 构建请求参数
            request_params: Dict[str, Any] = {
                "model": self.model,
                "messages": api_messages,
                "temperature": temperature,
            }

            if max_tokens:
                request_params["max_tokens"] = max_tokens

            # 添加工具定义
            if tools:
                request_params["tools"] = self._convert_tools(tools)

            # 调用API
            response = await self.client.chat.completions.create(**request_params)

            # 解析响应
            return self._parse_chat_response(response)

        except Exception as e:
            error_str = str(e)
            if "401" in error_str or "auth" in error_str.lower():
                raise LLMAuthenticationError(
                    "DeepSeek API认证失败，请检查API密钥",
                    provider="DeepSeek",
                    details={"error": error_str},
                )
            elif "429" in error_str or "rate" in error_str.lower():
                raise LLMRateLimitError(
                    "DeepSeek API速率限制",
                    provider="DeepSeek",
                    details={"error": error_str},
                )
            elif "timeout" in error_str.lower():
                raise LLMTimeoutError(
                    "DeepSeek API请求超时",
                    provider="DeepSeek",
                    details={"error": error_str},
                )
            else:
                raise LLMError(
                    f"DeepSeek API错误: {e}",
                    provider="DeepSeek",
                    details={"error": error_str},
                )

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """生成文本嵌入向量"""
        # DeepSeek目前不提供官方嵌入API
        # 可以使用第三方或本地模型
        raise NotImplementedError(
            "DeepSeek目前不提供嵌入API。请使用其他提供商或本地嵌入模型。"
        )

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将内部消息格式转换为OpenAI兼容格式"""
        api_messages = []
        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                api_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            if msg.tool_call_id:
                api_msg["tool_call_id"] = msg.tool_call_id
            api_messages.append(api_msg)
        return api_messages

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """将内部工具格式转换为OpenAI兼容格式"""
        return [
            {
                "type": tool.type,
                "function": {
                    "name": tool.function.name,
                    "description": tool.function.description,
                    "parameters": tool.function.parameters,
                },
            }
            for tool in tools
        ]

    def _parse_chat_response(self, response: Any) -> ChatResponse:
        """解析DeepSeek API响应（OpenAI兼容格式）"""
        choice = response.choices[0]
        message = choice.message

        # 解析工具调用
        tool_calls = None
        if message.tool_calls:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    type=tc.type,
                    function=FunctionDefinition(
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                        parameters={},
                    ),
                )
                for tc in message.tool_calls
            ]

        return ChatResponse(
            content=message.content or "",
            role="assistant",
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
            usage=TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
            ),
            model=response.model,
            raw_response={"id": response.id, "created": response.created},
        )

    def supports_tools(self) -> bool:
        return True

    def supports_embedding(self) -> bool:
        return False
