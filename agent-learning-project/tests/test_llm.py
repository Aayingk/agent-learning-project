"""
LLM后端测试脚本
测试各LLM客户端的基本功能
"""

import asyncio
import os
from dotenv import load_dotenv

from backend.llm import LLMFactory, Message

load_dotenv()


async def demo_openai():
    """测试OpenAI客户端"""
    print("\n=== 测试 OpenAI ===")

    if not os.getenv("OPENAI_API_KEY"):
        print("跳过：未配置OPENAI_API_KEY")
        return

    try:
        llm = LLMFactory.create("openai")

        # 测试基本信息
        print(f"模型信息: {llm.get_model_info()}")

        # 测试对话
        messages = [
            Message(role="user", content="用一句话介绍你自己"),
        ]
        response = await llm.chat(messages)

        print(f"回复: {response.content}")
        print(f"Token使用: {response.usage.model_dump()}")

        # 测试嵌入
        embed_response = await llm.embed(["hello world"])
        print(f"嵌入向量维度: {len(embed_response.embeddings[0])}")

        print("✅ OpenAI测试通过")

    except Exception as e:
        print(f"❌ OpenAI测试失败: {e}")


async def demo_anthropic():
    """测试Anthropic客户端"""
    print("\n=== 测试 Anthropic ===")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("跳过：未配置ANTHROPIC_API_KEY")
        return

    try:
        llm = LLMFactory.create("anthropic")

        print(f"模型信息: {llm.get_model_info()}")

        messages = [
            Message(role="user", content="用一句话介绍你自己"),
        ]
        response = await llm.chat(messages)

        print(f"回复: {response.content}")
        print(f"Token使用: {response.usage.model_dump()}")

        print("✅ Anthropic测试通过")

    except Exception as e:
        print(f"❌ Anthropic测试失败: {e}")


async def demo_ollama():
    """测试Ollama客户端"""
    print("\n=== 测试 Ollama ===")

    try:
        llm = LLMFactory.create("ollama")

        print(f"模型信息: {llm.get_model_info()}")

        messages = [
            Message(role="user", content="Say hello"),
        ]
        response = await llm.chat(messages)

        print(f"回复: {response.content}")
        print(f"Token使用: {response.usage.model_dump()}")

        print("✅ Ollama测试通过")

    except Exception as e:
        print(f"❌ Ollama测试失败: {e}")
        print("提示：请确保已安装并启动Ollama服务")


async def demo_tool_calling():
    """测试工具调用功能"""
    print("\n=== 测试工具调用 ===")

    if not os.getenv("OPENAI_API_KEY"):
        print("跳过：未配置OPENAI_API_KEY")
        return

    from backend.llm.models import ToolDefinition, FunctionDefinition

    try:
        llm = LLMFactory.create("openai")

        # 定义一个计算器工具
        calculator_tool = ToolDefinition(
            type="function",
            function=FunctionDefinition(
                name="calculator",
                description="执行数学计算",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "要计算的数学表达式，如 '2 + 2'",
                        }
                    },
                    "required": ["expression"],
                },
            ),
        )

        messages = [
            Message(role="user", content="帮我计算 123 + 456 等于多少"),
        ]

        response = await llm.chat(messages, tools=[calculator_tool])

        print(f"回复内容: {response.content}")
        if response.tool_calls:
            print(f"工具调用:")
            for tc in response.tool_calls:
                print(f"  - 工具: {tc.function.name}")
                print(f"  - 参数: {tc.function.arguments}")

        print("✅ 工具调用测试通过")

    except Exception as e:
        print(f"❌ 工具调用测试失败: {e}")


async def main():
    """运行所有测试"""
    print("开始测试LLM后端...")
    print(f"当前工作目录: {os.getcwd()}")

    await demo_openai()
    await demo_anthropic()
    await demo_ollama()
    await demo_tool_calling()

    print("\n" + "=" * 40)
    print("测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
