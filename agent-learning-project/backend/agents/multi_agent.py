"""
多Agent协作模块
实现多个Agent分工协作
"""

from typing import Any, Dict, List, Optional
from enum import Enum

from backend.agents.base import BaseAgent, AgentConfig, AgentState
from backend.agents.react_agent import ReActAgent, ConversationalAgent, ToolAgent
from backend.llm.models import Message, ChatResponse


class AgentRole(str, Enum):
    """Agent角色"""
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


class MultiAgentOrchestrator:
    """
    多Agent编排器

    协调多个Agent分工协作完成复杂任务
    """

    def __init__(
        self,
        llm,
        memory_manager=None,
    ):
        """
        初始化编排器

        Args:
            llm: LLM客户端
            memory_manager: 记忆管理器
        """
        self.llm = llm
        self.memory = memory_manager

        # 创建各个Agent
        self.agents = {
            AgentRole.RESEARCHER: self._create_research_agent(),
            AgentRole.CODER: self._create_coder_agent(),
            AgentRole.REVIEWER: self._create_reviewer_agent(),
            AgentRole.COORDINATOR: self._create_coordinator_agent(),
        }

    def _create_research_agent(self) -> BaseAgent:
        """创建研究Agent"""
        config = AgentConfig(
            name="researcher",
            description="负责信息收集和研究",
            system_prompt="""你是一个研究专家。你的任务是：
1. 深入研究给定主题
2. 收集相关信息和数据
3. 整理研究结果

请保持客观、全面，引用可靠来源。""",
            enable_tools=True,
        )
        return ToolAgent(config=config, llm=self.llm)

    def _create_coder_agent(self) -> BaseAgent:
        """创建代码Agent"""
        config = AgentConfig(
            name="coder",
            description="负责代码编写",
            system_prompt="""你是一个编程专家。你的任务是：
1. 根据需求编写高质量代码
2. 确保代码清晰、可维护
3. 添加必要的注释

使用Python编写代码。""",
            enable_tools=True,
        )
        return ToolAgent(config=config, llm=self.llm)

    def _create_reviewer_agent(self) -> BaseAgent:
        """创建审查Agent"""
        config = AgentConfig(
            name="reviewer",
            description="负责审查工作",
            system_prompt="""你是一个审查专家。你的任务是：
1. 审查研究结果或代码质量
2. 指出问题和改进建议
3. 给出客观评价

请提供建设性的反馈。""",
            enable_tools=False,
        )
        return ConversationalAgent(config=config, llm=self.llm)

    def _create_coordinator_agent(self) -> BaseAgent:
        """创建协调Agent"""
        config = AgentConfig(
            name="coordinator",
            description="负责协调和整合",
            system_prompt="""你是任务协调专家。你的任务是：
1. 理解用户需求
2. 分配任务给合适的专家
3. 整合专家的工作成果
4. 给出最终答案

请确保最终答案完整、准确。""",
            enable_tools=False,
        )
        return ConversationalAgent(config=config, llm=self.llm)

    async def execute(
        self,
        task: str,
        session_id: str = "default",
        workflow: str = "standard",
    ) -> Dict[str, Any]:
        """
        执行多Agent任务

        Args:
            task: 任务描述
            session_id: 会话ID
            workflow: 工作流类型

        Returns:
            执行结果
        """
        if workflow == "standard":
            return await self._standard_workflow(task, session_id)
        elif workflow == "code_review":
            return await self._code_review_workflow(task, session_id)
        elif workflow == "research":
            return await self._research_workflow(task, session_id)
        else:
            raise ValueError(f"未知工作流: {workflow}")

    async def _standard_workflow(
        self,
        task: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        标准工作流：
        Coordinator -> Researcher -> Coordinator
        """
        steps = []

        # 步骤1：协调者分析任务
        coordinator = self.agents[AgentRole.COORDINATOR]
        analysis_prompt = f"""请分析以下任务，确定是否需要研究：

任务：{task}

如果需要研究，请明确指出需要研究什么。
如果不需要，请直接回答。"""

        analysis = await coordinator.run(
            analysis_prompt,
            session_id=f"{session_id}_coord_1",
        )
        steps.append({
            "agent": "coordinator",
            "action": "analyze_task",
            "result": analysis.content,
        })

        # 步骤2：研究者收集信息
        researcher = self.agents[AgentRole.RESEARCHER]
        research_task = f"""任务：{task}

协调者分析：{analysis.content}

请进行必要的研究。"""

        research_result = await researcher.run(
            research_task,
            session_id=f"{session_id}_research",
        )
        steps.append({
            "agent": "researcher",
            "action": "research",
            "result": research_result.content,
        })

        # 步骤3：协调者整合结果
        final_prompt = f"""原始任务：{task}

研究结果：{research_result.content}

请基于研究结果，给用户一个完整、准确的答案。"""

        final_result = await coordinator.run(
            final_prompt,
            session_id=f"{session_id}_coord_2",
        )
        steps.append({
            "agent": "coordinator",
            "action": "finalize",
            "result": final_result.content,
        })

        return {
            "answer": final_result.content,
            "steps": steps,
            "workflow": "standard",
        }

    async def _code_review_workflow(
        self,
        task: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        代码审查工作流：
        Coder -> Reviewer -> Coordinator
        """
        steps = []

        # 步骤1：代码编写
        coder = self.agents[AgentRole.CODER]
        code_result = await coder.run(
            task,
            session_id=f"{session_id}_code",
        )
        steps.append({
            "agent": "coder",
            "action": "write_code",
            "result": code_result.content,
        })

        # 步骤2：代码审查
        reviewer = self.agents[AgentRole.REVIEWER]
        review_prompt = f"""请审查以下代码或方案：

任务：{task}
代码/方案：{code_result.content}

请指出问题和改进建议。"""

        review_result = await reviewer.run(
            review_prompt,
            session_id=f"{session_id}_review",
        )
        steps.append({
            "agent": "reviewer",
            "action": "review",
            "result": review_result.content,
        })

        # 步骤3：协调者整合
        coordinator = self.agents[AgentRole.COORDINATOR]
        final_prompt = f"""任务：{task}

原始代码：{code_result.content}

审查意见：{review_result.content}

请基于审查意见，给出最终版本。"""

        final_result = await coordinator.run(
            final_prompt,
            session_id=f"{session_id}_coord",
        )
        steps.append({
            "agent": "coordinator",
            "action": "finalize",
            "result": final_result.content,
        })

        return {
            "answer": final_result.content,
            "code": code_result.content,
            "review": review_result.content,
            "steps": steps,
            "workflow": "code_review",
        }

    async def _research_workflow(
        self,
        task: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        深度研究工作流：
        Researcher -> Reviewer -> Coordinator
        """
        steps = []

        # 深度研究
        researcher = self.agents[AgentRole.RESEARCHER]
        research_result = await researcher.run(
            f"""请对以下主题进行深入研究：{task}

要求：
1. 收集多方面信息
2. 分析关键点
3. 给出全面总结""",
            session_id=f"{session_id}_research",
        )
        steps.append({
            "agent": "researcher",
            "action": "deep_research",
            "result": research_result.content,
        })

        # 研究质量审查
        reviewer = self.agents[AgentRole.REVIEWER]
        review_result = await reviewer.run(
            f"""请评估以下研究的质量：{research_result.content}""",
            session_id=f"{session_id}_review",
        )
        steps.append({
            "agent": "reviewer",
            "action": "evaluate_research",
            "result": review_result.content,
        })

        # 最终整合
        coordinator = self.agents[AgentRole.COORDINATOR]
        final_result = await coordinator.run(
            f"""原始问题：{task}

研究：{research_result.content}

评估：{review_result.content}

请给出最终答案。""",
            session_id=f"{session_id}_coord",
        )
        steps.append({
            "agent": "coordinator",
            "action": "finalize",
            "result": final_result.content,
        })

        return {
            "answer": final_result.content,
            "research": research_result.content,
            "evaluation": review_result.content,
            "steps": steps,
            "workflow": "research",
        }

    def get_agents_info(self) -> List[Dict[str, Any]]:
        """获取所有Agent信息"""
        return [
            {
                "role": role.value,
                "name": agent.config.name,
                "description": agent.config.description,
                "state": agent.state.value,
            }
            for role, agent in self.agents.items()
        ]
