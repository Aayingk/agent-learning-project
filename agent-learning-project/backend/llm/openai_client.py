"""
OpenAI LLM客户端
实现OpenAI API的调用
"""

import asyncio
from typing import Any, Dict, List, Optional

import openai
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

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


class OpenAILLM(BaseLLM):
    """
    OpenAI LLM客户端

    支持模型：
    - gpt-4o, gpt-4-turbo, gpt-4
    - gpt-3.5-turbo
    - o1-preview, o1-mini

    支持：
    - 聊天对话（带工具调用）
    - 文本嵌入
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        embedding_model: str = "text-embedding-3-small",
        timeout: int = 60,
        max_retries: int = 2,
        **kwargs,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)
        self.embedding_model = embedding_model
        self.timeout = timeout
        self.max_retries = max_retries

        # 初始化异步客户端
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )

    @retry(
        retry=retry_if_exception_type(openai.RateLimitError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
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
        发送聊天请求到OpenAI

        Args:
            messages: 消息列表
            tools: 工具定义列表
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            ChatResponse: 聊天响应
        """
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

        except openai.AuthenticationError as e:
            raise LLMAuthenticationError(
                "OpenAI API认证失败，请检查API密钥",
                provider="OpenAI",
                details={"error": str(e)},
            )
        except openai.RateLimitError as e:
            raise LLMRateLimitError(
                "OpenAI API速率限制",
                provider="OpenAI",
                details={"error": str(e)},
            )
        except openai.APITimeoutError as e:
            raise LLMTimeoutError(
                "OpenAI API请求超时",
                provider="OpenAI",
                details={"error": str(e)},
            )
        except openai.InvalidRequestError as e:
            raise LLMInvalidRequestError(
                f"OpenAI API无效请求: {e}",
                provider="OpenAI",
                details={"error": str(e)},
            )
        except openai.APIError as e:
            raise LLMError(
                f"OpenAI API错误: {e}",
                provider="OpenAI",
                details={"error": str(e)},
            )

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """
        生成文本嵌入向量

        Args:
            texts: 文本列表
            **kwargs: 其他参数

        Returns:
            EmbeddingResponse: 嵌入响应
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]

            return EmbeddingResponse(
                embeddings=embeddings,
                model=self.embedding_model,
                usage=TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=0,
                    total_tokens=response.usage.total_tokens,
                ),
            )

        except Exception as e:
            raise LLMError(
                f"OpenAI嵌入API错误: {e}",
                provider="OpenAI",
                details={"error": str(e)},
            )

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将内部消息格式转换为OpenAI API格式"""
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
        """将内部工具格式转换为OpenAI API格式"""
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
        """解析OpenAI API响应"""
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
                        parameters={},  # 不在响应中
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
            raw_response={
                "id": response.id,
                "created": response.created,
            },
        )

    def supports_tools(self) -> bool:
        return True

    def supports_embedding(self) -> bool:
        return True
