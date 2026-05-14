"""
LLM数据模型
定义LLM交互中使用的消息、响应等数据结构
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Message(BaseModel):
    """聊天消息模型"""

    role: str = Field(..., description="消息角色: system/user/assistant/tool")
    content: str = Field(..., description="消息内容")
    tool_call_id: Optional[str] = Field(None, description="工具调用ID（tool消息用）")
    tool_calls: Optional[List["ToolCall"]] = Field(None, description="工具调用列表（assistant消息用）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class ToolCall(BaseModel):
    """工具调用模型"""

    id: str = Field(..., description="工具调用ID")
    type: str = Field(default="function", description="调用类型")
    function: "FunctionCall" = Field(..., description="函数调用信息")


class FunctionCall(BaseModel):
    """函数调用信息"""

    name: str = Field(..., description="函数名称")
    arguments: str = Field(..., description="函数参数（JSON字符串）")


class ToolDefinition(BaseModel):
    """工具定义模型（用于LLM function calling）"""

    type: str = Field(default="function", description="工具类型")
    function: "FunctionDefinition" = Field(..., description="函数定义")


class FunctionDefinition(BaseModel):
    """函数定义"""

    name: str = Field(..., description="函数名称")
    description: str = Field(..., description="函数描述")
    parameters: Dict[str, Any] = Field(..., description="参数schema（JSON Schema格式）")


class ChatResponse(BaseModel):
    """聊天响应模型"""

    content: str = Field(..., description="回复内容")
    role: str = Field(default="assistant", description="回复角色")
    tool_calls: Optional[List[ToolCall]] = Field(None, description="工具调用列表")
    finish_reason: Optional[str] = Field(None, description="结束原因: stop/length/tool_calls/error")
    usage: "TokenUsage" = Field(..., description="Token使用情况")
    model: str = Field(..., description="使用的模型名称")
    raw_response: Optional[Dict[str, Any]] = Field(None, description="原始响应（用于调试）")


class TokenUsage(BaseModel):
    """Token使用统计"""

    prompt_tokens: int = Field(0, description="输入token数")
    completion_tokens: int = Field(0, description="输出token数")
    total_tokens: int = Field(0, description="总token数")

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        """合并两个TokenUsage"""
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class EmbeddingResponse(BaseModel):
    """嵌入响应模型"""

    embeddings: List[List[float]] = Field(..., description="向量列表")
    model: str = Field(..., description="使用的嵌入模型")
    usage: "TokenUsage" = Field(..., description="Token使用情况")


# 更新前向引用
Message.model_rebuild()
ToolCall.model_rebuild()
ChatResponse.model_rebuild()
