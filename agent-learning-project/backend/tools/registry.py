"""
工具注册中心
管理所有可用工具的注册和查找
"""

from typing import Dict, List, Optional, Type
from backend.tools.base import BaseTool


class ToolRegistry:
    """
    工具注册中心（单例模式）

    所有工具都需要注册到这里才能被Agent使用。
    支持装饰器注册和直接注册两种方式。
    """

    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, tool: BaseTool) -> BaseTool:
        """
        注册工具

        Args:
            tool: 工具实例

        Returns:
            工具实例（支持装饰器链式调用）

        Raises:
            ValueError: 工具名称已存在
        """
        if tool.name in cls._tools:
            raise ValueError(f"工具名称 '{tool.name}' 已存在")

        cls._tools[tool.name] = tool
        return tool

    @classmethod
    def register_class(cls, tool_class: Type[BaseTool]) -> Type[BaseTool]:
        """
        注册工具类（装饰器用法）

        Args:
            tool_class: 工具类

        Returns:
            工具类
        """
        tool_instance = tool_class()
        cls.register(tool_instance)
        return tool_class

    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        """
        获取工具实例

        Args:
            name: 工具名称

        Returns:
            工具实例，不存在则返回None
        """
        return cls._tools.get(name)

    @classmethod
    def list_all(cls) -> List[str]:
        """获取所有已注册工具的名称列表"""
        return list(cls._tools.keys())

    @classmethod
    def get_all_tools(cls) -> Dict[str, BaseTool]:
        """获取所有工具实例"""
        return cls._tools.copy()

    @classmethod
    def get_llm_tool_definitions(cls) -> List[Dict]:
        """
        获取所有工具的LLM格式定义

        用于传递给LLM进行function calling
        """
        return [tool.to_llm_tool_definition() for tool in cls._tools.values()]

    @classmethod
    def clear(cls):
        """清空所有注册的工具（主要用于测试）"""
        cls._tools.clear()

    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销工具

        Args:
            name: 工具名称

        Returns:
            是否成功注销
        """
        if name in cls._tools:
            del cls._tools[name]
            return True
        return False


def register_tool(tool_class: Type[BaseTool]) -> Type[BaseTool]:
    """
    装饰器：注册工具类

    用法：
    @register_tool
    class MyTool(BaseTool):
        name = "my_tool"
        description = "我的工具"
        ...
    """
    return ToolRegistry.register_class(tool_class)
