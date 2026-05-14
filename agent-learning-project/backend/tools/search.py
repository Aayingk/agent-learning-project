"""
搜索工具
支持多种搜索引擎
"""

from typing import Any, Dict, List
from backend.tools.base import BaseTool, ToolResult, ToolParameter, ToolError


class SearchTool(BaseTool):
    """
    搜索工具基类
    """

    name = "search"
    description = "在互联网上搜索信息，返回相关结果"
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="搜索查询内容",
            required=True,
        ),
        ToolParameter(
            name="num_results",
            type="number",
            description="返回结果数量，默认5",
            required=False,
            default=5,
        ),
    ]

    def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        """执行搜索（子类实现具体逻辑）"""
        raise NotImplementedError("子类必须实现execute方法")


class DuckDuckGoSearchTool(SearchTool):
    """
    DuckDuckGo搜索工具

    优点：无需API密钥，免费使用
    缺点：结果质量可能不如Google
    """

    name = "ddg_search"
    description = "使用DuckDuckGo搜索引擎在互联网上搜索信息"

    def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query,
                    max_results=num_results,
                )

                for r in search_results:
                    if r is None:
                        continue
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("link", ""),
                        "snippet": r.get("body", ""),
                    })

            return ToolResult.success_result(
                data={
                    "query": query,
                    "results": results,
                    "count": len(results),
                },
                metadata={"engine": "duckduckgo"},
            )

        except ImportError:
            return ToolResult.error_result(
                "duckduckgo_search未安装，请运行: uv add duckduckgo-search"
            )
        except Exception as e:
            return ToolResult.error_result(f"搜索失败: {str(e)}")


class WikipediaSearchTool(BaseTool):
    """
    维基百科搜索工具

    适合查找百科类信息
    """

    name = "wikipedia_search"
    description = "在维基百科中搜索信息，适合查找百科类内容"
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="搜索查询内容",
            required=True,
        ),
        ToolParameter(
            name="sentences",
            type="number",
            description="返回结果的句子数量，默认3",
            required=False,
            default=3,
        ),
    ]

    def execute(self, query: str, sentences: int = 3, **kwargs) -> ToolResult:
        try:
            import wikipedia

            # 设置中文
            wikipedia.set_lang("zh")

            # 搜索页面
            search_results = wikipedia.search(query, results=1)

            if not search_results:
                return ToolResult.error_result(f"未找到关于 '{query}' 的维基百科条目")

            # 获取页面摘要
            page = wikipedia.page(search_results[0])
            summary = wikipedia.summary(search_results[0], sentences=sentences)

            # 返回与DuckDuckGo一致的格式
            return ToolResult.success_result(
                data={
                    "query": query,
                    "results": [{
                        "title": page.title,
                        "url": page.url,
                        "snippet": summary,
                    }],
                    "count": 1,
                },
                metadata={"source": "wikipedia"},
            )

        except ImportError:
            return ToolResult.error_result(
                "wikipedia未安装，请运行: uv add wikipedia"
            )
        except wikipedia.exceptions.DisambiguationError as e:
            return ToolResult.error_result(
                f"查询有歧义，可能指: {', '.join(e.options[:5])}"
            )
        except wikipedia.exceptions.PageError:
            return ToolResult.error_result(f"维基百科页面不存在")
        except Exception as e:
            return ToolResult.error_result(f"搜索失败: {str(e)}")


class HybridSearchTool(BaseTool):
    """
    混合搜索工具

    优先使用维基百科，如果没有结果则使用DuckDuckGo
    """

    name = "search"
    description = "在互联网上搜索信息（优先使用维基百科，百科类信息更准确）"
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="搜索查询内容",
            required=True,
        ),
        ToolParameter(
            name="num_results",
            type="number",
            description="返回结果数量，默认5",
            required=False,
            default=5,
        ),
    ]

    def __init__(self):
        super().__init__()
        self._wiki_tool = WikipediaSearchTool()
        self._ddg_tool = DuckDuckGoSearchTool()

    def execute(self, query: str, num_results: int = 5, **kwargs) -> ToolResult:
        # 先尝试维基百科
        wiki_result = self._wiki_tool.execute(query=query, sentences=3)

        if wiki_result.success:
            # 维基百科有结果，返回
            metadata = wiki_result.metadata or {}
            metadata["engine"] = "wikipedia"
            return ToolResult.success_result(
                data=wiki_result.data,
                metadata=metadata
            )

        # 维基百科无结果，使用DuckDuckGo
        ddg_result = self._ddg_tool.execute(query=query, num_results=num_results)
        metadata = ddg_result.metadata or {}
        metadata["fallback_from"] = "wikipedia"
        return ToolResult(
            success=ddg_result.success,
            data=ddg_result.data,
            error=ddg_result.error,
            metadata=metadata
        )
