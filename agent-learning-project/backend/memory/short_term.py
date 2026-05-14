"""
短期记忆模块
管理对话历史和上下文窗口
"""

import time
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime

from backend.llm.models import Message


class ShortTermMemory:
    """
    短期记忆管理器

    负责管理对话历史，实现：
    - 消息队列的添加和获取
    - 上下文窗口管理（限制token数量）
    - 会话过期管理
    - 消息摘要（当超限时压缩历史）
    """

    def __init__(
        self,
        max_messages: int = 100,
        max_tokens: int = 4000,
        session_ttl: int = 3600,
    ):
        """
        初始化短期记忆

        Args:
            max_messages: 最大消息数量
            max_tokens: 最大token数（粗略估算）
            session_ttl: 会话过期时间（秒）
        """
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.session_ttl = session_ttl

        # 消息存储：{session_id: deque of messages}
        self._sessions: Dict[str, deque] = {}

        # 会话最后活跃时间
        self._last_active: Dict[str, float] = {}

    def add_message(self, session_id: str, message: Message) -> None:
        """
        添加消息到会话

        Args:
            session_id: 会话ID
            message: 消息对象
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = deque(maxlen=self.max_messages)

        self._sessions[session_id].append(message)
        self._last_active[session_id] = time.time()

        # 检查是否需要清理
        self._cleanup_if_needed(session_id)

    def get_messages(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Message]:
        """
        获取会话消息

        Args:
            session_id: 会话ID
            limit: 最多返回的消息数量

        Returns:
            消息列表
        """
        if session_id not in self._sessions:
            return []

        messages = list(self._sessions[session_id])

        # 检查会话是否过期
        if self._is_expired(session_id):
            return []

        if limit:
            return messages[-limit:]

        return messages

    def get_context(
        self,
        session_id: str,
        max_tokens: Optional[int] = None,
    ) -> List[Message]:
        """
        获取适合作为LLM上下文的消息

        自动管理上下文窗口，确保不超过token限制

        Args:
            session_id: 会话ID
            max_tokens: 最大token数，默认使用实例设置

        Returns:
            消息列表（从旧到新）
        """
        if session_id not in self._sessions:
            return []

        max_tokens = max_tokens or self.max_tokens
        messages = list(self._sessions[session_id])

        # 粗略估算token数（中文约1.5字符=1token，英文约4字符=1token）
        # 简化为：每个字符约0.3-0.5token
        def estimate_tokens(text: str) -> int:
            return int(len(text) * 0.5)

        # 从最新消息开始向前选择
        selected = []
        total_tokens = 0

        for msg in reversed(messages):
            msg_tokens = estimate_tokens(msg.content)

            if total_tokens + msg_tokens > max_tokens:
                # 超出限制，停止
                break

            selected.insert(0, msg)
            total_tokens += msg_tokens

        return selected

    def get_system_context(
        self,
        session_id: str,
        system_message: str,
    ) -> List[Message]:
        """
        获取包含系统消息的完整上下文

        Args:
            session_id: 会话ID
            system_message: 系统提示词

        Returns:
            完整上下文消息列表
        """
        messages = [Message(role="system", content=system_message)]
        messages.extend(self.get_messages(session_id))
        return messages

    def clear_session(self, session_id: str) -> bool:
        """
        清除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功清除
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._last_active[session_id]
            return True
        return False

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息字典
        """
        if session_id not in self._sessions:
            return None

        messages = self._sessions[session_id]
        last_active = self._last_active[session_id]

        return {
            "session_id": session_id,
            "message_count": len(messages),
            "last_active": datetime.fromtimestamp(last_active),
            "expired": self._is_expired(session_id),
            "estimated_tokens": sum(int(len(m.content) * 0.5) for m in messages),
        }

    def list_sessions(self) -> List[str]:
        """列出所有活跃会话ID"""
        self._cleanup_expired()
        return list(self._sessions.keys())

    def _cleanup_if_needed(self, session_id: str) -> None:
        """如果消息过多，清理旧消息"""
        if session_id in self._sessions:
            messages = self._sessions[session_id]
            # 粗略估算总token数
            total_tokens = sum(int(len(m.content) * 0.5) for m in messages)

            if total_tokens > self.max_tokens:
                # 保留最新的70%消息
                keep_count = int(len(messages) * 0.7)
                # 保留system消息
                system_msgs = [m for m in messages if m.role == "system"]
                other_msgs = [m for m in messages if m.role != "system"]

                self._sessions[session_id] = deque(
                    system_msgs + other_msgs[-keep_count:],
                    maxlen=self.max_messages,
                )

    def _is_expired(self, session_id: str) -> bool:
        """检查会话是否过期"""
        if session_id not in self._last_active:
            return True

        last_active = self._last_active[session_id]
        return time.time() - last_active > self.session_ttl

    def _cleanup_expired(self) -> None:
        """清理所有过期会话"""
        now = time.time()
        expired = [
            sid for sid, last in self._last_active.items()
            if now - last > self.session_ttl
        ]

        for sid in expired:
            self.clear_session(sid)


class ConversationSummary:
    """
    对话摘要器

    当对话历史过长时，生成摘要以节省token
    """

    def __init__(self):
        """初始化摘要器"""
        # 简单实现：基于规则摘要
        # 生产环境可以使用LLM生成摘要
        pass

    def summarize(self, messages: List[Message]) -> str:
        """
        生成对话摘要

        Args:
            messages: 消息列表

        Returns:
            摘要文本
        """
        if not messages:
            return ""

        # 简单实现：提取关键信息
        user_msgs = [m for m in messages if m.role == "user"]
        assistant_msgs = [m for m in messages if m.role == "assistant"]

        summary_parts = [
            f"对话包含 {len(user_msgs)} 轮用户消息和 {len(assistant_msgs)} 轮助手回复。",
        ]

        # 提取用户消息的前几句
        if user_msgs:
            first_user = user_msgs[0].content[:100]
            summary_parts.append(f"用户首先询问: {first_user}...")

        if len(user_msgs) > 1:
            last_user = user_msgs[-1].content[:100]
            summary_parts.append(f"最后询问: {last_user}...")

        return " ".join(summary_parts)

    async def llm_summarize(
        self,
        messages: List[Message],
        llm,  # LLM客户端
    ) -> str:
        """
        使用LLM生成摘要

        Args:
            messages: 消息列表
            llm: LLM客户端

        Returns:
            摘要文本
        """
        conversation = "\n".join(
            f"{m.role}: {m.content}"
            for m in messages
        )

        prompt = f"""请将以下对话摘要为简洁的描述，保留关键信息：

{conversation}

摘要："""

        from backend.llm.models import Message as Msg
        response = await llm.chat([Msg(role="user", content=prompt)])
        return response.content
