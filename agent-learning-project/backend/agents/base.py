"""
Agent基础架构
定义Agent的抽象接口和状态管理
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

from backend.llm.models import Message, ChatResponse
from backend.tools import ToolRegistry


class AgentState(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"           # 空闲
    THINKING = "thinking"   # 思考中
    ACTING = "acting"       # 执行动作
    DONE = "done"           # 完成
    ERROR = "error"         # 错误


class AgentConfig(BaseModel):
    """Agent配置"""
    name: str = "agent"
    description: str = ""
    system_prompt: str = "你是一个有用的AI助手。"
    temperature: float = 0.7
    max_iterations: int = 10
    enable_tools: bool = True
    enable_memory: bool = True


class AgentContext(BaseModel):
    """Agent上下文"""
    session_id: str = "default"
    messages: List[Message] = Field(default_factory=list)
    current_iteration: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """
    Agent抽象基类

    所有Agent都需要继承这个类并实现核心逻辑
    """

    def __init__(
        self,
        config: AgentConfig,
        llm,
        memory_manager=None,
    ):
        """
        初始化Agent

        Args:
            config: Agent配置
            llm: LLM客户端
            memory_manager: 记忆管理器（可选）
        """
        self.config = config
        self.llm = llm
        self.memory = memory_manager

        # 工具注册表
        self._tool_registry = ToolRegistry()

        # 当前状态
        self._state = AgentState.IDLE

    @property
    def state(self) -> AgentState:
        """获取当前状态"""
        return self._state

    @abstractmethod
    async def run(
        self,
        input_message: str,
        session_id: str = "default",
        **kwargs,
    ) -> ChatResponse:
        """
        运行Agent

        Args:
            input_message: 用户输入
            session_id: 会话ID
            **kwargs: 其他参数

        Returns:
            Agent响应
        """
        pass

    async def think(
        self,
        messages: List[Message],
    ) -> ChatResponse:
        """
        思考：让LLM生成响应

        Args:
            messages: 消息列表

        Returns:
            LLM响应
        """
        self._state = AgentState.THINKING

        # 添加系统提示
        system_msg = Message(
            role="system",
            content=self.config.system_prompt,
        )
        all_messages = [system_msg] + messages

        # 获取工具定义
        tools = None
        if self.config.enable_tools:
            tools = self._tool_registry.get_llm_tool_definitions()

        # 调用LLM
        response = await self.llm.chat(
            messages=all_messages,
            tools=tools,
            temperature=self.config.temperature,
        )

        return response

    async def act(
        self,
        tool_calls: List,
    ) -> List[Dict[str, Any]]:
        """
        行动：执行工具调用

        Args:
            tool_calls: 工具调用列表

        Returns:
            工具执行结果列表
        """
        self._state = AgentState.ACTING

        results = []
        for tc in tool_calls:
            # 获取工具
            tool = self._tool_registry.get(tc.function.name)
            if not tool:
                results.append({
                    "error": f"工具不存在: {tc.function.name}",
                })
                continue

            # 解析参数
            import json
            try:
                params = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                results.append({
                    "error": f"无效的JSON参数: {tc.function.arguments}",
                })
                continue

            # 执行工具
            try:
                result = await tool.aexecute(**params)
                results.append({
                    "tool": tool.name,
                    "success": result.success,
                    "data": result.data,
                    "error": result.error,
                })
            except Exception as e:
                results.append({
                    "tool": tool.name,
                    "error": str(e),
                })

        return results

    async def add_message(
        self,
        session_id: str,
        message: Message,
    ) -> None:
        """Add a message to memory without nesting event loops."""
        if self.memory and self.config.enable_memory:
            await self.memory.add_message(session_id, message)

    def get_messages(
        self,
        session_id: str,
    ) -> List[Message]:
        """获取会话消息"""
        if self.memory and self.config.enable_memory:
            return self.memory.short_term.get_messages(session_id)
        return []

    def get_context_messages(
        self,
        session_id: str,
    ) -> List[Message]:
        """获取上下文消息（包含系统提示）"""
        messages = self.get_messages(session_id)
        system_msg = Message(
            role="system",
            content=self.config.system_prompt,
        )
        return [system_msg] + messages

    def reset(self, session_id: str = "default") -> None:
        """重置会话"""
        if self.memory:
            self.memory.clear_session(session_id)
        self._state = AgentState.IDLE

    def get_state(self) -> Dict[str, Any]:
        """获取Agent状态信息"""
        return {
            "name": self.config.name,
            "state": self._state.value,
            "description": self.config.description,
            "enable_tools": self.config.enable_tools,
            "enable_memory": self.config.enable_memory,
        }
