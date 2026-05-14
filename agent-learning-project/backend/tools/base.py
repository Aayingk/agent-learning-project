"""
工具系统基础架构
定义工具的抽象接口和执行模型
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行结果"""

    success: bool = Field(..., description="执行是否成功")
    data: Any = Field(None, description="返回数据")
    error: Optional[str] = Field(None, description="错误信息（如果失败）")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")

    @classmethod
    def success_result(cls, data: Any, metadata: Optional[Dict] = None) -> "ToolResult":
        """创建成功结果"""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_result(cls, error: str, metadata: Optional[Dict] = None) -> "ToolResult":
        """创建失败结果"""
        return cls(success=False, error=error, metadata=metadata)


class ToolParameter(BaseModel):
    """工具参数定义"""

    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型: string/number/boolean/array/object")
    description: str = Field(..., description="参数描述")
    required: bool = Field(default=False, description="是否必填")
    default: Any = Field(None, description="默认值")
    enum: Optional[List[Any]] = Field(None, description="枚举值列表")


class BaseTool(ABC):
    """
    工具抽象基类

    所有工具都需要继承这个类并实现execute方法。
    工具可以被Agent调用，用于执行特定任务。
    """

    # 工具元数据（子类覆盖）
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []

    # 执行配置
    timeout: int = 30  # 默认超时时间（秒）
    async_execution: bool = False  # 是否支持异步执行

    def __init__(self):
        """初始化工具"""
        if not self.name:
            raise ValueError(f"{self.__class__.__name__} 必须定义 name 属性")
        if not self.description:
            raise ValueError(f"{self.__class__.__name__} 必须定义 description 属性")

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        pass

    async def aexecute(self, **kwargs) -> ToolResult:
        """
        异步执行工具（默认调用同步方法）

        子类可以覆盖此方法以实现真正的异步执行
        """
        return self.execute(**kwargs)

    def get_schema(self) -> Dict[str, Any]:
        """
        获取工具的JSON Schema格式

        用于LLM function calling
        """
        properties = {}
        required = []

        for param in self.parameters:
            prop_def: Dict[str, Any] = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop_def["enum"] = param.enum
            if param.default is not None:
                prop_def["default"] = param.default
            properties[param.name] = prop_def
            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def validate_parameters(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        验证参数

        Returns:
            (is_valid, error_message)
        """
        # 检查必填参数
        for param in self.parameters:
            if param.required and param.name not in params:
                return False, f"缺少必填参数: {param.name}"

            # 检查枚举值
            if param.name in params and param.enum:
                if params[param.name] not in param.enum:
                    return False, f"参数 {param.name} 的值必须在 {param.enum} 中"

        return True, None

    def to_llm_tool_definition(self) -> Dict[str, Any]:
        """
        转换为LLM工具定义格式

        兼容OpenAI和Anthropic的function calling格式
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.get_schema(),
            },
        }


class ToolError(Exception):
    """工具执行错误"""

    def __init__(self, tool_name: str, message: str, details: Optional[Dict] = None):
        self.tool_name = tool_name
        self.message = message
        self.details = details or {}
        super().__init__(f"[{tool_name}] {message}")


class ToolTimeoutError(ToolError):
    """工具执行超时"""


class ToolValidationError(ToolError):
    """工具参数验证失败"""
