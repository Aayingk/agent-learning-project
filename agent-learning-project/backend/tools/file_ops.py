"""
文件操作工具
读取和写入文件
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.tools.base import BaseTool, ToolResult, ToolParameter


class FileReadTool(BaseTool):
    """
    文件读取工具

    支持读取文本文件内容
    """

    name = "read_file"
    description = "读取文本文件的内容，支持txt、md、py、json等常见文本格式"
    parameters = [
        ToolParameter(
            name="path",
            type="string",
            description="文件的相对路径或绝对路径",
            required=True,
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="文件编码，默认utf-8",
            required=False,
            default="utf-8",
        ),
        ToolParameter(
            name="max_lines",
            type="number",
            description="最多读取的行数，-1表示读取全部",
            required=False,
            default=-1,
        ),
    ]

    def execute(
        self,
        path: str,
        encoding: str = "utf-8",
        max_lines: int = -1,
        **kwargs
    ) -> ToolResult:
        try:
            file_path = Path(path)

            # 检查文件是否存在
            if not file_path.exists():
                return ToolResult.error_result(f"文件不存在: {path}")

            # 检查是否为文件
            if not file_path.is_file():
                return ToolResult.error_result(f"路径不是文件: {path}")

            # 检查文件大小（限制10MB）
            file_size = file_path.stat().st_size
            if file_size > 10 * 1024 * 1024:
                return ToolResult.error_result(
                    f"文件过大({file_size / 1024 / 1024:.2f}MB)，超过10MB限制"
                )

            # 读取文件
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    if max_lines > 0:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= max_lines:
                                break
                            lines.append(line.rstrip("\n"))
                        content = "\n".join(lines)
                        truncated = i >= max_lines - 1
                    else:
                        content = f.read()
                        lines = content.split("\n")
                        truncated = False
            except UnicodeDecodeError:
                # 尝试其他编码
                encodings = ["gbk", "gb2312", "latin-1"]
                for enc in encodings:
                    try:
                        with open(file_path, "r", encoding=enc) as f:
                            content = f.read()
                        encoding = enc
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return ToolResult.error_result("无法解码文件，请指定正确的编码")

            # 获取文件信息
            return ToolResult.success_result(
                data={
                    "path": str(file_path.absolute()),
                    "content": content,
                    "encoding": encoding,
                    "size": file_size,
                    "lines": len(lines) if isinstance(lines, list) else len(content.split("\n")),
                    "truncated": truncated,
                },
                metadata={
                    "filename": file_path.name,
                    "extension": file_path.suffix,
                }
            )

        except PermissionError:
            return ToolResult.error_result(f"没有权限读取文件: {path}")
        except Exception as e:
            return ToolResult.error_result(f"读取文件失败: {str(e)}")


class FileWriteTool(BaseTool):
    """
    文件写入工具

    支持写入文本文件
    """

    name = "write_file"
    description = "将内容写入文本文件。注意：会覆盖已有文件"
    parameters = [
        ToolParameter(
            name="path",
            type="string",
            description="文件的相对路径或绝对路径",
            required=True,
        ),
        ToolParameter(
            name="content",
            type="string",
            description="要写入的内容",
            required=True,
        ),
        ToolParameter(
            name="encoding",
            type="string",
            description="文件编码，默认utf-8",
            required=False,
            default="utf-8",
        ),
        ToolParameter(
            name="mode",
            type="string",
            description="写入模式: write(覆盖) 或 append(追加)",
            required=False,
            default="write",
            enum=["write", "append"],
        ),
    ]

    def execute(
        self,
        path: str,
        content: str,
        encoding: str = "utf-8",
        mode: str = "write",
        **kwargs
    ) -> ToolResult:
        try:
            file_path = Path(path)

            # 检查内容长度（限制1MB）
            content_size = len(content.encode(encoding))
            if content_size > 1024 * 1024:
                return ToolResult.error_result(
                    f"内容过大({content_size / 1024:.2f}KB)，超过1MB限制"
                )

            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 检查文件是否已存在
            existed = file_path.exists()

            # 写入文件
            write_mode = "a" if mode == "append" else "w"
            with open(file_path, write_mode, encoding=encoding) as f:
                f.write(content)

            return ToolResult.success_result(
                data={
                    "path": str(file_path.absolute()),
                    "bytes_written": content_size,
                    "mode": mode,
                    "existed_before": existed,
                },
                metadata={
                    "filename": file_path.name,
                    "extension": file_path.suffix,
                }
            )

        except PermissionError:
            return ToolResult.error_result(f"没有权限写入文件: {path}")
        except Exception as e:
            return ToolResult.error_result(f"写入文件失败: {str(e)}")


class FileListTool(BaseTool):
    """
    文件列表工具

    列出目录下的文件和子目录
    """

    name = "list_files"
    description = "列出指定目录下的文件和子目录"
    parameters = [
        ToolParameter(
            name="path",
            type="string",
            description="目录的相对路径或绝对路径，默认为当前目录",
            required=False,
            default=".",
        ),
        ToolParameter(
            name="pattern",
            type="string",
            description="文件名匹配模式，如 *.py, *.txt",
            required=False,
            default="*",
        ),
        ToolParameter(
            name="recursive",
            type="boolean",
            description="是否递归列出子目录",
            required=False,
            default=False,
        ),
    ]

    def execute(
        self,
        path: str = ".",
        pattern: str = "*",
        recursive: bool = False,
        **kwargs
    ) -> ToolResult:
        try:
            dir_path = Path(path)

            # 检查目录是否存在
            if not dir_path.exists():
                return ToolResult.error_result(f"目录不存在: {path}")

            if not dir_path.is_dir():
                return ToolResult.error_result(f"路径不是目录: {path}")

            # 列出文件
            if recursive:
                items = list(dir_path.rglob(pattern))
            else:
                items = list(dir_path.glob(pattern))

            # 分类
            files = []
            directories = []

            for item in items:
                if item.is_file():
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "size": item.stat().st_size,
                    })
                elif item.is_dir() and item != dir_path:
                    directories.append({
                        "name": item.name,
                        "path": str(item),
                    })

            return ToolResult.success_result(
                data={
                    "path": str(dir_path.absolute()),
                    "files": files,
                    "directories": directories,
                    "counts": {
                        "files": len(files),
                        "directories": len(directories),
                    },
                }
            )

        except PermissionError:
            return ToolResult.error_result(f"没有权限访问目录: {path}")
        except Exception as e:
            return ToolResult.error_result(f"列出目录失败: {str(e)}")


class DirectoryCreateTool(BaseTool):
    """
    创建目录工具
    """

    name = "create_directory"
    description = "创建新目录"
    parameters = [
        ToolParameter(
            name="path",
            type="string",
            description="目录的相对路径或绝对路径",
            required=True,
        ),
        ToolParameter(
            name="parents",
            type="boolean",
            description="是否创建父目录（类似 mkdir -p）",
            required=False,
            default=True,
        ),
    ]

    def execute(self, path: str, parents: bool = True, **kwargs) -> ToolResult:
        try:
            dir_path = Path(path)

            # 检查是否已存在
            if dir_path.exists():
                if dir_path.is_dir():
                    return ToolResult.success_result(
                        data={"path": str(dir_path.absolute()), "created": False},
                        metadata={"note": "目录已存在"}
                    )
                else:
                    return ToolResult.error_result(f"路径已存在但不是目录: {path}")

            # 创建目录
            if parents:
                dir_path.mkdir(parents=True, exist_ok=True)
            else:
                dir_path.mkdir()

            return ToolResult.success_result(
                data={"path": str(dir_path.absolute()), "created": True}
            )

        except PermissionError:
            return ToolResult.error_result(f"没有权限创建目录: {path}")
        except Exception as e:
            return ToolResult.error_result(f"创建目录失败: {str(e)}")
