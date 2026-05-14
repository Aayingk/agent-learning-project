"""
API数据模型
定义API请求和响应的数据结构
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(default="default", description="会话ID")
    agent_type: str = Field(default="react", description="Agent类型: react/conversational/tool")
    llm_provider: str = Field(default="openai", description="LLM提供商")
    workflow: Optional[str] = Field(None, description="多Agent工作流类型")
    temperature: Optional[float] = Field(None, description="温度参数")


class ToolCall(BaseModel):
    """工具调用记录"""
    tool: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None


class ChatResponse(BaseModel):
    """聊天响应"""
    response: str = Field(..., description="Agent回复")
    session_id: str = Field(..., description="会话ID")
    agent_type: str = Field(..., description="使用的Agent类型")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="工具调用记录")
    tokens_used: Optional[Dict[str, int]] = Field(None, description="Token使用情况")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class AgentInfo(BaseModel):
    """Agent信息"""
    name: str
    description: str
    capabilities: List[str]


class MultiAgentRequest(BaseModel):
    """多Agent请求"""
    task: str = Field(..., description="任务描述")
    session_id: str = Field(default="default", description="会话ID")
    workflow: str = Field(default="standard", description="工作流类型")
    llm_provider: str = Field(default="openai", description="LLM提供商")


class MultiAgentResponse(BaseModel):
    """多Agent响应"""
    answer: str = Field(..., description="最终答案")
    workflow: str = Field(..., description="使用的工作流")
    steps: List[Dict[str, Any]] = Field(..., description="执行步骤")
    session_id: str = Field(..., description="会话ID")


class DocumentUploadRequest(BaseModel):
    """文档上传请求"""
    file_path: str = Field(..., description="文档路径")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    message: str
    chunks_added: Optional[int] = None
    document_id: Optional[str] = None


class RAGQueryRequest(BaseModel):
    """RAG查询请求"""
    question: str = Field(..., description="问题")
    top_k: int = Field(default=5, description="返回文档数量")
    context_only: bool = Field(default=False, description="是否只返回检索结果")


class RAGQueryResponse(BaseModel):
    """RAG查询响应"""
    answer: str
    sources: List[Dict[str, Any]]
    usage: Optional[Dict[str, int]] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    agents_available: List[str]
    tools_available: List[str]
    llm_providers: List[str] = Field(default_factory=list, description="可用的LLM提供商")


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: Optional[str] = None
