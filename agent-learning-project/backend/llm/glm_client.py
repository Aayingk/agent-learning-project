"""
GLM (智谱AI) LLM客户端
实现智谱AI API的调用
"""

from typing import Any, Dict, List, Optional
from zhipuai import ZhipuAI

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


class GLMLLM(BaseLLM):
    """
    智谱AI LLM客户端

    支持模型：
    - glm-4-flash: 闪电模型，速度快
    - glm-4-plus: Plus模型，能力强
    - glm-4-air: 空气模型，性价比高
    - glm-4-long: 长文本模型
    - glm-3-turbo: Turbo模型

    文档: https://open.bigmodel.cn/dev/api
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        timeout: int = 60,
        max_retries: int = 2,
        **kwargs,
    ):
        super().__init__(model=model, api_key=api_key, base_url=base_url, **kwargs)
        self.timeout = timeout
        self.max_retries = max_retries

        # 初始化客户端
        self.client = ZhipuAI(
            api_key=api_key,
            timeout=timeout,
        )

    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> ChatResponse:
        """发送聊天请求到智谱AI"""
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

            # 调用API（智谱SDK是同步的，用asyncio.to_thread包装）
            import asyncio
            response = await asyncio.to_thread(self.client.chat.completions.create, **request_params)

            # 解析响应
            return self._parse_chat_response(response)

        except Exception as e:
            error_str = str(e)
            if "401" in error_str or "auth" in error_str.lower():
                raise LLMAuthenticationError(
                    "智谱AI API认证失败，请检查API密钥",
                    provider="GLM",
                    details={"error": error_str},
                )
            elif "429" in error_str or "rate" in error_str.lower():
                raise LLMRateLimitError(
                    "智谱AI API速率限制",
                    provider="GLM",
                    details={"error": error_str},
                )
            elif "timeout" in error_str.lower():
                raise LLMTimeoutError(
                    "智谱AI API请求超时",
                    provider="GLM",
                    details={"error": error_str},
                )
            else:
                raise LLMError(
                    f"智谱AI API错误: {e}",
                    provider="GLM",
                    details={"error": error_str},
                )

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """生成文本嵌入向量"""
        try:
            import asyncio
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model="embedding-3",  # 智谱的嵌入模型
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]

            return EmbeddingResponse(
                embeddings=embeddings,
                model="embedding-3",
                usage=TokenUsage(
                    prompt_tokens=response.usage.total_tokens,
                    completion_tokens=0,
                    total_tokens=response.usage.total_tokens,
                ),
            )

        except Exception as e:
            raise LLMError(
                f"智谱AI嵌入API错误: {e}",
                provider="GLM",
                details={"error": str(e)},
            )

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """将内部消息格式转换为智谱API格式"""
        api_messages = []
        for msg in messages:
            api_msg = {"role": msg.role, "content": msg.content}
            if msg.tool_calls:
                # 智谱API工具调用格式
                tool_calls = []
                for tc in msg.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    })
                api_msg["tool_calls"] = tool_calls
            api_messages.append(api_msg)
        return api_messages

    def _convert_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """将内部工具格式转换为智谱API格式"""
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
        """解析智谱API响应"""
        choice = response.choices[0]
        message = choice.message

        # 解析工具调用
        tool_calls = None
        if hasattr(message, 'tool_calls') and message.tool_calls:
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
        return True
