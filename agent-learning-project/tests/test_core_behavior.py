import asyncio

from backend.agents import ConversationalAgent
from backend.llm.models import ChatResponse, Message, TokenUsage
from backend.memory import MemoryManager
from backend.tools import ToolRegistry


class FakeLLM:
    async def chat(self, messages, tools=None, temperature=0.7, max_tokens=None, **kwargs):
        return ChatResponse(
            content="ok",
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
            model="fake",
        )


async def _run_conversation_with_memory():
    memory = MemoryManager()
    agent = ConversationalAgent(llm=FakeLLM(), memory_manager=memory)
    response = await agent.run("hello", session_id="pytest-session")
    messages = memory.short_term.get_messages("pytest-session")
    memory.clear_session("pytest-session")
    return response, messages


def test_conversational_agent_saves_memory_inside_event_loop():
    response, messages = asyncio.run(_run_conversation_with_memory())

    assert response.content == "ok"
    assert [message.role for message in messages] == ["user", "assistant"]
    assert messages[0].content == "hello"
    assert messages[1].content == "ok"


def test_calculator_tool_success_and_error_paths():
    calculator = ToolRegistry.get("calculator")

    success = calculator.execute(expression="10 * (5 + 3)")
    failure = calculator.execute(expression="10 / 0")

    assert success.success is True
    assert success.data["result"] == 80
    assert failure.success is False
    assert failure.error


def test_llm_factory_import_does_not_require_all_provider_sdks():
    from backend.llm import LLMFactory

    providers = LLMFactory.list_providers()

    assert "openai" in providers
    assert "glm" in providers