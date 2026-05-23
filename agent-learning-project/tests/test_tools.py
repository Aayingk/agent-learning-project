"""
工具系统测试脚本
"""

import os

from backend.tools import (
    ToolRegistry,
    CalculatorTool,
    FileReadTool,
    FileWriteTool,
    HybridSearchTool,
)


def test_registry():
    """测试工具注册"""
    print("\n=== 测试工具注册 ===")

    # 列出所有已注册工具
    tools = ToolRegistry.list_all()
    print(f"已注册工具: {tools}")
    print(f"工具数量: {len(tools)}")

    # 获取特定工具
    calc = ToolRegistry.get("calculator")
    if calc:
        print(f"[OK] 成功获取计算器工具: {calc.name}")
        print(f"   描述: {calc.description}")
    else:
        print("[FAIL] 未找到计算器工具")


def test_calculator():
    """测试计算器工具"""
    print("\n=== 测试计算器 ===")

    calc = ToolRegistry.get("calculator")
    if not calc:
        print("[FAIL] 计算器工具未注册")
        return

    # 测试基本运算
    test_cases = [
        ("2 + 2", 4),
        ("10 * (5 + 3)", 80),
        ("100 / 4", 25),
        ("2 ** 8", 256),
        ("(10 + 5) * 2 - 8", 22),
    ]

    for expr, expected in test_cases:
        result = calc.execute(expression=expr)
        if result.success:
            actual = result.data["result"]
            if abs(actual - expected) < 0.0001:
                print(f"[OK] {expr} = {actual}")
            else:
                print(f"[FAIL] {expr} = {actual}, 期望 {expected}")
        else:
            print(f"[FAIL] {expr} 计算失败: {result.error}")

    # 测试错误处理
    error_cases = [
        "10 / 0",  # 除零
        "2 + ",    # 语法错误
        "print('hello')",  # 不支持的操作
    ]

    for expr in error_cases:
        result = calc.execute(expression=expr)
        if not result.success:
            print(f"[OK] 正确捕获错误: {expr} -> {result.error}")
        else:
            print(f"[FAIL] 应该失败但成功了: {expr}")


def test_file_operations():
    """测试文件操作工具"""
    print("\n=== 测试文件操作 ===")

    write_tool = ToolRegistry.get("write_file")
    read_tool = ToolRegistry.get("read_file")

    if not write_tool or not read_tool:
        print("[FAIL] 文件工具未注册")
        return

    # 写入测试文件
    test_content = "Hello, Agent Learning Project!\n这是测试内容。"
    write_result = write_tool.execute(
        path="./test_output.txt",
        content=test_content,
    )

    if write_result.success:
        print(f"[OK] 文件写入成功: {write_result.data['bytes_written']} bytes")
    else:
        print(f"[FAIL] 文件写入失败: {write_result.error}")
        return

    # 读取测试文件
    read_result = read_tool.execute(path="./test_output.txt")

    if read_result.success:
        content = read_result.data["content"]
        if content == test_content:
            print(f"[OK] 文件读取成功，内容匹配")
            print(f"   文件大小: {read_result.data['size']} bytes")
            print(f"   行数: {read_result.data['lines']}")
        else:
            print(f"[FAIL] 内容不匹配")
            print(f"   期望: {test_content}")
            print(f"   实际: {content}")
    else:
        print(f"[FAIL] 文件读取失败: {read_result.error}")

    # 清理测试文件
    import os
    try:
        os.remove("./test_output.txt")
        print("[OK] 测试文件已清理")
    except:
        pass


def test_search():
    """测试搜索工具（需要网络）"""
    if os.getenv("RUN_NETWORK_TESTS") != "1":
        print("\n=== 跳过搜索工具网络测试（设置 RUN_NETWORK_TESTS=1 启用）===")
        return
    print("\n=== 测试搜索工具 ===")

    search = ToolRegistry.get("search")
    if not search:
        print("[FAIL] 搜索工具未注册")
        return

    # 测试搜索
    try:
        result = search.execute(query="AI agent", num_results=3)

        if result.success:
            print(f"[OK] 搜索成功")
            print(f"   查询: {result.data.get('query', 'N/A')}")
            print(f"   结果数: {result.data.get('count', 'N/A')}")
            if result.data.get('results'):
                first = result.data['results'][0]
                print(f"   首条: {first.get('title', 'N/A')}")
                print(f"   URL: {first.get('url', 'N/A')}")
        else:
            print(f"[SKIP] 搜索失败: {result.error}")
            print("   提示: 搜索需要网络连接")
    except Exception as e:
        print(f"[SKIP] 搜索测试异常: {e}")
        print("   提示: 搜索需要网络连接")


def test_tool_schema():
    """测试工具Schema生成"""
    print("\n=== 测试工具Schema生成 ===")

    calc = ToolRegistry.get("calculator")
    if not calc:
        return

    schema = calc.get_schema()
    print(f"计算器Schema:")
    import json
    print(json.dumps(schema, indent=2, ensure_ascii=False))

    # 获取LLM格式定义
    llm_def = calc.to_llm_tool_definition()
    print(f"\nLLM工具定义:")
    print(json.dumps(llm_def, indent=2, ensure_ascii=False))


def main():
    """运行所有测试"""
    print("=" * 50)
    print("工具系统测试")
    print("=" * 50)

    test_registry()
    test_calculator()
    test_file_operations()
    test_search()
    test_tool_schema()

    print("\n" + "=" * 50)
    print("测试完成！")


if __name__ == "__main__":
    main()
