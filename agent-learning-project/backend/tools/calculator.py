"""
计算器工具
执行数学计算
"""

import ast
import operator
from typing import Any, Dict
from backend.tools.base import BaseTool, ToolResult, ToolParameter


class CalculatorTool(BaseTool):
    """
    安全计算器工具

    支持基本数学运算，使用eval的安全替代方案
    """

    name = "calculator"
    description = "执行数学计算，支持加减乘除、括号等基本运算"
    parameters = [
        ToolParameter(
            name="expression",
            type="string",
            description="要计算的数学表达式，例如: 2 + 2, 10 * (5 + 3), 100 / 4",
            required=True,
        ),
    ]

    # 支持的运算符
    OPERATORS: Dict[str, Any] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def execute(self, expression: str, **kwargs) -> ToolResult:
        try:
            # 清理表达式
            expression = expression.strip()
            if not expression:
                return ToolResult.error_result("表达式不能为空")

            # 安全计算
            result = self._safe_eval(expression)

            return ToolResult.success_result(
                data={
                    "expression": expression,
                    "result": result,
                    "result_type": type(result).__name__,
                }
            )

        except ZeroDivisionError:
            return ToolResult.error_result("除零错误")
        except SyntaxError:
            return ToolResult.error_result("表达式语法错误")
        except (ValueError, TypeError) as e:
            return ToolResult.error_result(f"计算错误: {str(e)}")
        except Exception as e:
            return ToolResult.error_result(f"未知错误: {str(e)}")

    def _safe_eval(self, expr: str) -> Any:
        """
        安全计算表达式

        只允许数学运算，不允许执行任意代码
        """
        try:
            # 解析表达式为AST
            node = ast.parse(expr, mode="eval")

            # 递归计算
            return self._eval_node(node.body)

        except Exception:
            raise ValueError(f"无法计算表达式: {expr}")

    def _eval_node(self, node: ast.AST) -> Any:
        """递归计算AST节点"""

        # 数字字面量
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value)}")

        # 一元运算（负号）
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_type = type(node.op)
            if op_type in self.OPERATORS:
                return self.OPERATORS[op_type](operand)
            raise ValueError(f"不支持的一元运算符: {op_type}")

        # 二元运算
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_type = type(node.op)

            if op_type in self.OPERATORS:
                try:
                    return self.OPERATORS[op_type](left, right)
                except ZeroDivisionError:
                    raise
                except Exception as e:
                    raise ValueError(f"运算错误: {e}")

            raise ValueError(f"不支持的二元运算符: {op_type}")

        # 括号分组
        if isinstance(node, ast.Expression):
            return self._eval_node(node.body)

        raise ValueError(f"不支持的语法结构: {type(node)}")


class AdvancedCalculatorTool(BaseTool):
    """
    高级计算器工具

    支持更多数学函数
    """

    name = "advanced_calculator"
    description = "执行高级数学计算，支持三角函数、对数、平方根等"
    parameters = [
        ToolParameter(
            name="expression",
            type="string",
            description="数学表达式，支持函数: sin, cos, tan, sqrt, log, pow, abs 等",
            required=True,
        ),
    ]

    def execute(self, expression: str, **kwargs) -> ToolResult:
        try:
            import math

            # 创建安全的计算环境
            safe_dict = {
                # 常数
                "pi": math.pi,
                "e": math.e,
                # 函数
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "asin": math.asin,
                "acos": math.acos,
                "atan": math.atan,
                "sqrt": math.sqrt,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pow": pow,
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                # 运算符
                "__builtins__": {},
            }

            # 添加运算符
            safe_dict.update({
                "add": lambda x, y: x + y,
                "sub": lambda x, y: x - y,
                "mul": lambda x, y: x * y,
                "div": lambda x, y: x / y,
            })

            result = eval(expression, safe_dict, {})

            return ToolResult.success_result(
                data={
                    "expression": expression,
                    "result": result,
                }
            )

        except ZeroDivisionError:
            return ToolResult.error_result("除零错误")
        except NameError as e:
            return ToolResult.error_result(f"不支持的函数或变量: {str(e)}")
        except Exception as e:
            return ToolResult.error_result(f"计算错误: {str(e)}")
