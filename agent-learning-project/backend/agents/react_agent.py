"""
ReAct Agent实现
基于Reasoning + Acting的Agent模式
"""

import json
from typing import Any, Dict, List, Optional

from backend.agents.base import BaseAgent, AgentConfig, AgentState
from backend.llm.models import Message, ChatResponse, ToolCall
from backend.tools import ToolRegistry


class ReActAgent(BaseAgent):
    """
    ReAct Agent

    实现Reasoning + Acting循环：
    1. Thought: 思考当前情况
    2. Action: 决定采取的行动（调用工具或直接回答）
    3. Observation: 观察行动结果
    4. 重复直到完成任务
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm=None,
        memory_manager=None,
    ):
        """
        初始化ReAct Agent

        Args:
            config: Agent配置
            llm: LLM客户端
            memory_manager: 记忆管理器
        """
        if config is None:
            config = AgentConfig(
                name="react_agent",
                description="基于ReAct模式的智能Agent",
                system_prompt=self._get_default_system_prompt(),
                enable_tools=True,
            )

        super().__init__(config, llm, memory_manager)

    async def run(
        self,
        input_message: str,
        session_id: str = "default",
        **kwargs,
    ) -> ChatResponse:
        """
        运行ReAct Agent

        Args:
            input_message: 用户输入
            session_id: 会话ID
            **kwargs: 其他参数

        Returns:
            Agent响应
        """
        # 获取历史消息
        messages = self.get_messages(session_id)

        # 添加用户消息
        user_msg = Message(role="user", content=input_message)
        messages.append(user_msg)

        # ReAct循环
        self._state = AgentState.THINKING
        iteration = 0
        max_iterations = self.config.max_iterations

        while iteration < max_iterations:
            iteration += 1

            # 思考并决定行动
            response = await self.think(messages)

            # 检查是否有工具调用
            if response.tool_calls:
                # 执行工具
                tool_results = await self.act(response.tool_calls)

                # 构建工具结果消息
                for i, (tc, result) in enumerate(zip(response.tool_calls, tool_results)):
                    tool_msg = Message(
                        role="tool",
                        content=json.dumps(result, ensure_ascii=False),
                        tool_call_id=tc.id,
                    )
                    messages.append(tool_msg)

                # 添加助手消息（包含工具调用）
                assistant_msg = Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
                messages.append(assistant_msg)

                # 继续循环
                continue

            # 没有工具调用，任务完成
            final_response = response
            break

        else:
            # 达到最大迭代次数
            final_response = ChatResponse(
                content="抱歉，我尝试了多次但无法完成任务。请提供更多信息或换个方式描述。",
                role="assistant",
                finish_reason="max_iterations",
                usage=response.usage,
                model=response.model,
            )

        # 保存对话到记忆
        await self.add_message(session_id, user_msg)
        await self.add_message(
            session_id,
            Message(
                role="assistant",
                content=final_response.content,
            ),
        )

        self._state = AgentState.DONE
        return final_response

    def _get_default_system_prompt(self) -> str:
        """获取默认系统提示词"""
        tools_desc = self._get_tools_description()

        return f"""你是一个基于ReAct模式的智能助手，可以使用工具来帮助用户。

可用工具：
{tools_desc}

工作流程：
1. 理解用户的需求
2. 分析需要哪些信息
3. 选择合适的工具获取信息
4. 基于工具结果给出最终答案

注意事项：
- 优先使用工具获取准确信息
- 如果不需要工具，直接回答
- 工具调用失败时，尝试其他方法或告知用户
- 保持回答简洁、准确、有帮助"""

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        tools = self._tool_registry.get_all_tools()
        descriptions = []
        for name, tool in tools.items():
            descriptions.append(f"- {name}: {tool.description}")
        return "\n".join(descriptions)


class ConversationalAgent(BaseAgent):
    """
    对话Agent

    专注于多轮对话的Agent，不使用工具
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm=None,
        memory_manager=None,
    ):
        if config is None:
            config = AgentConfig(
                name="conversational_agent",
                description="专注于对话的AI助手",
                system_prompt="你是一个友好、专业的AI助手。你擅长多轮对话，能记住上下文。",
                enable_tools=False,
                enable_memory=True,
            )

        super().__init__(config, llm, memory_manager)

    async def run(
        self,
        input_message: str,
        session_id: str = "default",
        **kwargs,
    ) -> ChatResponse:
        """
        运行对话Agent

        Args:
            input_message: 用户输入
            session_id: 会话ID
            **kwargs: 其他参数

        Returns:
            Agent响应
        """
        # 获取历史消息
        messages = self.get_messages(session_id)

        # 添加用户消息
        user_msg = Message(role="user", content=input_message)
        messages.append(user_msg)

        # 获取上下文（管理token数量）
        if self.memory:
            context_messages = self.memory.short_term.get_context(
                session_id,
                max_tokens=3000,
            )
            # 确保包含当前消息
            if user_msg not in context_messages:
                context_messages.append(user_msg)
            messages = context_messages
        else:
            messages = [user_msg]

        # 添加系统提示
        system_msg = Message(
            role="system",
            content=self.config.system_prompt,
        )
        all_messages = [system_msg] + messages

        # 调用LLM
        response = await self.llm.chat(
            messages=all_messages,
            temperature=self.config.temperature,
        )

        # 保存对话
        await self.add_message(session_id, user_msg)
        await self.add_message(
            session_id,
            Message(role="assistant", content=response.content),
        )

        self._state = AgentState.DONE
        return response


class ToolAgent(BaseAgent):
    """
    工具Agent

    专注于工具调用的Agent
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        llm=None,
        memory_manager=None,
        allowed_tools: Optional[List[str]] = None,
    ):
        if config is None:
            config = AgentConfig(
                name="tool_agent",
                description="擅长使用工具的AI助手",
                system_prompt=self._get_system_prompt(),
                enable_tools=True,
                enable_memory=False,
            )

        super().__init__(config, llm, memory_manager)

        # 限制可用工具
        self.allowed_tools = allowed_tools

    async def run(
        self,
        input_message: str,
        session_id: str = "default",
        **kwargs,
    ) -> ChatResponse:
        """
        运行工具Agent

        Args:
            input_message: 用户输入
            session_id: 会话ID
            **kwargs: 其他参数

        Returns:
            Agent响应
        """
        # 构建消息
        messages = [Message(role="user", content=input_message)]

        # 添加系统提示
        system_msg = Message(
            role="system",
            content=self.config.system_prompt,
        )
        all_messages = [system_msg] + messages

        # 获取可用工具
        tools = self._tool_registry.get_llm_tool_definitions()
        if self.allowed_tools:
            tools = [t for t in tools if t["function"]["name"] in self.allowed_tools]

        # 调用LLM
        response = await self.llm.chat(
            messages=all_messages,
            tools=tools if tools else None,
            temperature=self.config.temperature,
        )

        # 如果有工具调用，执行一次
        if response.tool_calls:
            tool_results = await self.act(response.tool_calls)

            # 格式化工具结果
            results_text = self._format_tool_results(tool_results)

            # 基于工具结果生成最终回复
            followup_msg = Message(
                role="user",
                content=f"工具执行结果：\n{results_text}\n\n请基于以上结果给用户一个清晰的回复。",
            )
            all_messages.append(
                Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )
            all_messages.append(followup_msg)

            final_response = await self.llm.chat(
                messages=all_messages,
                temperature=self.config.temperature,
            )
            return final_response

        return response

    def _get_system_prompt(self) -> str:
        """获取系统提示"""
        tools_desc = self._get_tools_description()
        return f"""你是一个专业的工具使用助手。

可用工具：
{tools_desc}

工作方式：
1. 理解用户需求
2. 选择合适的工具
3. 执行工具并获取结果
4. 向用户清晰地解释结果

注意：
- 一次只调用一个工具
- 确保工具参数正确
- 向用户清晰地解释结果"""

    def _get_tools_description(self) -> str:
        """获取工具描述"""
        tools = self._tool_registry.get_all_tools()
        if self.allowed_tools:
            tools = {
                k: v for k, v in tools.items()
                if k in self.allowed_tools
            }

        descriptions = []
        for name, tool in tools.items():
            params = ", ".join([p.name for p in tool.parameters if p.required])
            descriptions.append(f"- {name}({params}): {tool.description}")
        return "\n".join(descriptions)

    def _format_tool_results(self, results: List[Dict]) -> str:
        """格式化工具执行结果"""
        parts = []
        for i, result in enumerate(results, 1):
            tool_name = result.get("tool", "unknown")
            if result.get("success"):
                data = result.get("data", {})
                parts.append(f"工具{i} ({tool_name}): {data}")
            else:
                error = result.get("error", "未知错误")
                parts.append(f"工具{i} ({tool_name}) 失败: {error}")
        return "\n".join(parts)
