"""
项目完整性检查脚本
检查所有模块是否可以正确导入
"""

import sys
import io
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def check_imports():
    """检查所有模块导入"""
    print("=" * 60)
    print("检查项目模块导入...")
    print("=" * 60)

    errors = []
    successes = []

    # 检查LLM模块
    try:
        from backend.llm import LLMFactory, Message, ChatResponse
        successes.append("LLM模块")
    except Exception as e:
        errors.append(("LLM模块", str(e)))

    # 检查工具模块
    try:
        from backend.tools import ToolRegistry, CalculatorTool
        tools = ToolRegistry.list_all()
        successes.append(f"工具模块 ({len(tools)}个工具)")
    except Exception as e:
        errors.append(("工具模块", str(e)))

    # 检查记忆模块
    try:
        from backend.memory import MemoryManager, ShortTermMemory, LongTermMemory
        successes.append("记忆模块")
    except Exception as e:
        errors.append(("记忆模块", str(e)))

    # 检查RAG模块
    try:
        from backend.rag import RAGPipeline, VectorStore, DocumentLoader
        successes.append("RAG模块")
    except Exception as e:
        errors.append(("RAG模块", str(e)))

    # 检查Agent模块
    try:
        from backend.agents import (
            BaseAgent, ReActAgent, ConversationalAgent,
            ToolAgent, MultiAgentOrchestrator
        )
        successes.append("Agent模块")
    except Exception as e:
        errors.append(("Agent模块", str(e)))

    # 检查API模块
    try:
        from backend.api.main import app
        successes.append("API模块")
    except Exception as e:
        errors.append(("API模块", str(e)))

    # 检查配置模块
    try:
        from config.settings import settings
        successes.append("配置模块")
    except Exception as e:
        errors.append(("配置模块", str(e)))

    # 打印结果
    print("\n成功:")
    for s in successes:
        print(f"  [OK] {s}")

    if errors:
        print("\n失败:")
        for name, error in errors:
            print(f"  [FAIL] {name}: {error}")
        return False

    print("\n" + "=" * 60)
    print("所有模块检查通过!")
    print("=" * 60)
    return True


def check_project_structure():
    """检查项目结构"""
    print("\n检查项目结构...")

    required_dirs = [
        "backend/llm",
        "backend/tools",
        "backend/memory",
        "backend/rag",
        "backend/agents",
        "backend/api",
        "frontend",
        "config",
        "docs",
        "tests",
    ]

    required_files = [
        "pyproject.toml",
        ".env.example",
        "README.md",
        "docs/spec.md",
        "docs/design.md",
        "docs/task.md",
    ]

    missing = []
    for d in required_dirs:
        import os
        if not os.path.isdir(d):
            missing.append(f"目录: {d}")

    for f in required_files:
        import os
        if not os.path.isfile(f):
            missing.append(f"文件: {f}")

    if missing:
        print("  缺失:")
        for m in missing:
            print(f"    - {m}")
        return False

    print("  [OK] 项目结构完整")
    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Agent Learning Project - 项目完整性检查")
    print("=" * 60)

    structure_ok = check_project_structure()
    imports_ok = check_imports()

    print("\n" + "=" * 60)
    if structure_ok and imports_ok:
        print("项目检查通过！可以开始使用。")
        print("\n下一步:")
        print("1. 配置 .env 文件，填入API密钥")
        print("2. 运行 API: uv run uvicorn backend.api.main:app --reload")
        print("3. 运行前端: uv run streamlit run frontend/app.py")
    else:
        print("项目检查发现问题，请先解决上述错误。")
    print("=" * 60)


if __name__ == "__main__":
    main()
