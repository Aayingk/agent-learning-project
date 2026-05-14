"""工具系统模块"""

from backend.tools.base import (
    BaseTool,
    ToolResult,
    ToolParameter,
    ToolError,
    ToolTimeoutError,
    ToolValidationError,
)
from backend.tools.registry import ToolRegistry, register_tool

# 导入所有内置工具
from backend.tools.search import HybridSearchTool, DuckDuckGoSearchTool, WikipediaSearchTool
from backend.tools.calculator import CalculatorTool, AdvancedCalculatorTool
from backend.tools.file_ops import (
    FileReadTool,
    FileWriteTool,
    FileListTool,
    DirectoryCreateTool,
)

__all__ = [
    # Base
    "BaseTool",
    "ToolResult",
    "ToolParameter",
    "ToolError",
    "ToolTimeoutError",
    "ToolValidationError",
    # Registry
    "ToolRegistry",
    "register_tool",
    # Tools
    "HybridSearchTool",
    "DuckDuckGoSearchTool",
    "WikipediaSearchTool",
    "CalculatorTool",
    "AdvancedCalculatorTool",
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    "DirectoryCreateTool",
]


def register_default_tools():
    """注册所有默认工具"""
    registry = ToolRegistry()

    # 搜索工具
    registry.register(HybridSearchTool())
    registry.register(DuckDuckGoSearchTool())
    registry.register(WikipediaSearchTool())

    # 计算工具
    registry.register(CalculatorTool())
    registry.register(AdvancedCalculatorTool())

    # 文件工具
    registry.register(FileReadTool())
    registry.register(FileWriteTool())
    registry.register(FileListTool())
    registry.register(DirectoryCreateTool())


# 自动注册默认工具
register_default_tools()
