"""
Ollama LLM客户端
支持本地运行的开源模型
"""

from typing import Any, Dict, List, Optional
import httpx

from backend.llm.base import (
    BaseLLM,
    LLMError,
    LLMTimeoutError,
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


class OllamaLLM(BaseLLM):
    """
    Ollama LLM客户端

    支持本地运行的开源模型：
    - llama2, llama3, mistral, qwen等
    - 需要先安装Ollama并启动服务

    注意：
    - 工具调用支持取决于具体模型
    - 嵌入模型支持有限
    """

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        **kwargs,
    ):
        super().__init__(model=model, base_url=base_url, **kwargs)
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            base_url=base_url,
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
        """
        发送聊天请求到Ollama

        Args:
            messages: 消息列表
            tools: 工具定义列表（Ollama对工具支持有限）
            temperature: 温度参数
            max_tokens: 最大token数
            **kwargs: 其他参数

        Returns:
            ChatResponse: 聊天响应
        """
        try:
            # 构建请求
            request_data: Dict[str, Any] = {
                "model": self.model,
                "messages": self._convert_messages(messages),
                "stream": False,
                "options": {
                    "temperature": temperature,
                }
            }

            if max_tokens:
                request_data["options"]["num_predict"] = max_tokens

            # 发送请求
            response = await self.client.post("/api/chat", json=request_data)
            response.raise_for_status()

            data = response.json()

            # 解析响应
            return self._parse_chat_response(data)

        except httpx.TimeoutException:
            raise LLMTimeoutError(
                "Ollama请求超时",
                provider="Ollama",
                details={"model": self.model},
            )
        except httpx.HTTPError as e:
            raise LLMError(
                f"Ollama通信错误: {e}",
                provider="Ollama",
                details={"error": str(e)},
            )
        except Exception as e:
            raise LLMError(
                f"Ollama错误: {e}",
                provider="Ollama",
                details={"error": str(e)},
            )

    async def embed(
        self,
        texts: List[str],
        **kwargs,
    ) -> EmbeddingResponse:
        """
        生成文本嵌入向量

        注意：Ollama的嵌入支持取决于模型
        推荐使用：nomic-embed-text, mxbai-embed-large等
        """
        try:
            if len(texts) > 1:
                # 批量处理
                embeddings = []
                total_tokens = 0
                for text in texts:
                    response = await self.client.post("/api/embeddings", json={
                        "model": self.model,
                        "prompt": text,
                    })
                    response.raise_for_status()
                    data = response.json()
                    embeddings.append(data["embedding"])
                    total_tokens += data.get("prompt_eval_count", 0)

                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=self.model,
                    usage=TokenUsage(
                        prompt_tokens=total_tokens,
                        completion_tokens=0,
                        total_tokens=total_tokens,
                    ),
                )
            else:
                # 单个文本
                response = await self.client.post("/api/embeddings", json={
                    "model": self.model,
                    "prompt": texts[0],
                })
                response.raise_for_status()
                data = response.json()

                return EmbeddingResponse(
                    embeddings=[data["embedding"]],
                    model=self.model,
                    usage=TokenUsage(
                        prompt_tokens=data.get("prompt_eval_count", 0),
                        completion_tokens=0,
                        total_tokens=data.get("prompt_eval_count", 0),
                    ),
                )

        except Exception as e:
            raise LLMError(
                f"Ollama嵌入错误: {e}",
                provider="Ollama",
                details={"error": str(e)},
            )

    def _convert_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """将内部消息格式转换为Ollama API格式"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
            if msg.role in ["user", "assistant", "system"]
        ]

    def _parse_chat_response(self, data: Dict[str, Any]) -> ChatResponse:
        """解析Ollama API响应"""
        message = data.get("message", {})
        content = message.get("content", "")

        return ChatResponse(
            content=content,
            role="assistant",
            tool_calls=None,  # Ollama原生不支持工具调用
            finish_reason="stop",
            usage=TokenUsage(
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
            ),
            model=self.model,
            raw_response={"created_at": data.get("created_at")},
        )

    def supports_tools(self) -> bool:
        # Ollama原生不支持工具调用，但可以通过提示工程实现
        return False

    def supports_embedding(self) -> bool:
        # 取决于具体模型
        return True

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
