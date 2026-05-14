"""
Anthropic (Claude) LLM客户端
实现Claude API的调用
"""

from typing import Any, Dict, List, Optional

from anthropic import AsyncAnthropic
from anthropic import AnthropicError, RateLimitError, APITimeoutError

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


class AnthropicLLM(BaseLLM):
    """
    Anthropic (Claude) LLM客户端

    支持模型：
    - claude-3-5-sonnet-20241022
    - claude-3-opus-20240229
    - claude-3-sonnet-20240229
    - claude-3-haiku-20240307

    注意：
    - Anthropic目前不提供官方嵌入API
    - 工具调用格式与OpenAI略有不同
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.anthropic.com",
        timeout: int = 60,
        max_retries: int = 2,
        **kwargs,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)
        self.timeout = timeout
        self.max_retries = max_retries

        # 初始化异步客户端
        self.client = AsyncAnthropic(
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
        """
        发送聊天请求到Anthropic

        Args:
            messages: 消息列表
            tools: 工具定义列表
            temperature: 温度参数
            max_tokens: 最大token数（Claude必填）
            **kwargs: 其他参数

        Returns:
            ChatResponse: 聊天响应
        """
        try:
            # Claude需要max_tokens，设置合理默认值
            if max_tokens is None:
                max_tokens = 4096

            # 转换消息格式
            system_message, api_messages = self._convert_messages(messages)

            # 构建请求参数
            request_params: Dict[str, Any] = {
                "model": self.model,
                "messages": api_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }

            if system_message:
                request_params["system"] = system_message

            # 添加工具定义
            if tools:
                request_params["tools"] = self._convert_tools(tools)

            # 调用API
            response = await self.client.messages.create(**request_params)

            # 解析响应
            return self._parse_chat_response(response)

        except AnthropicError as e:
            if "authentication" in str(e).lower():
                raise LLMAuthenticationError(
                    "Claude API认证失败，请检查API密钥",
                    provider="Anthropic",
                    details={"error": str(e)},
                )
            elif "rate" in str(e).lower():
                raise LLMRateLimitError(
                    "Claude API速率限制",
                    provider="Anthropic",
                    details={"error": str(e)},
                )
            elif "timeout" in str(e).lower():
                raise LLMTimeoutError(
                    "Claude API请求超时",
                    provider="Anthropic",
                    details={"error": str(e)},
                )
            elif "invalid" in str(e).lower():
                raise LLMInvalidRequestError(
                    f"Claude API无效请求: {e}",
                    provider="Anthropic",
                    details={"error": str(e)},
                )
            else:
                raise LLMError(
                    f"Claude API错误: {e}",
                    provider="Anthropic",
                    details={"error": str(e)},
                )

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """
        Anthropic不提供嵌入API

        需要使用其他提供商（如OpenAI或本地模型）
        """
        raise NotImplementedError(
            "Anthropic目前不提供嵌入API。请使用OpenAI或本地嵌入模型。"
        )

    def _convert_messages(
        self, messages: List[Message]
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        """
        将内部消息格式转换为Anthropic API格式

        Anthropic格式要求：
        - system消息单独提取
        - user/assistant交替
        - tool结果作为user消息的block_content
        """
        system_message = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_message = msg.content
            elif msg.role == "user":
                api_messages.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant":
                content = [{"type": "text", "text": msg.content}]
                # 添加工具调用
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        content.append({
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.function.name,
                            "input": eval(tc.function.arguments),  # JSON字符串转dict
                        })
                api_messages.append({"role": "assistant", "content": content})
            elif msg.role == "tool":
                # 工具结果作为user消息的一部分
                api_messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": msg.tool_call_id,
                        "content": msg.content,
                    }]
                })

        return system_message, api_messages

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """将内部工具格式转换为Anthropic API格式"""
        return [
            {
                "name": tool.function.name,
                "description": tool.function.description,
                "input_schema": tool.function.parameters,
            }
            for tool in tools
        ]

    def _parse_chat_response(self, response: Any) -> ChatResponse:
        """解析Anthropic API响应"""
        content = response.content
        text_content = ""
        tool_calls = []

        for block in content:
            if block.type == "text":
                text_content += block.text
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        type="function",
                        function=FunctionDefinition(
                            name=block.name,
                            arguments=str(block.input),  # dict转JSON字符串
                            parameters={},
                        ),
                    )
                )

        return ChatResponse(
            content=text_content,
            role="assistant",
            tool_calls=tool_calls if tool_calls else None,
            finish_reason=response.stop_reason,
            usage=TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
            ),
            model=response.model,
            raw_response={"id": response.id},
        )

    def supports_tools(self) -> bool:
        return True

    def supports_embedding(self) -> bool:
        return False
