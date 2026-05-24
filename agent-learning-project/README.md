
# Agent Learning Project

> 一个全面的Agent开发教学项目，覆盖Agent开发岗位的核心技术栈

## 项目概述

本项目旨在帮助开发者掌握Agent开发的核心技能，通过实现一个功能完整的Agent系统，学习：
- 多LLM后端支持（OpenAI/Claude/Ollama）
- 工具调用（Tool Calling）
- 记忆系统（短期+长期）
- RAG检索增强
- 多Agent协作

## 技术栈

| 类别 | 技术 |
|------|------|
| Agent框架 | LangChain + LangGraph |
| LLM后端 | OpenAI / Anthropic / Ollama |
| 向量存储 | ChromaDB |
| API框架 | FastAPI |
| 前端 | Streamlit |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd agent-learning-project

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑.env，填入你的API密钥
# 至少配置一个LLM提供商
```

### 3. 运行

#### 方式一：API服务
```bash
uvicorn backend.api.main:app --reload
```
访问 http://localhost:8000/docs 查看API文档

#### 方式二：Streamlit前端
```bash
streamlit run frontend/app.py
```

## 项目结构

```
agent-learning-project/
├── backend/           # 后端核心逻辑
│   ├── api/          # FastAPI服务
│   ├── agents/       # Agent实现
│   ├── tools/        # 工具系统
│   ├── memory/       # 记忆系统
│   ├── rag/          # RAG模块
│   └── llm/          # LLM后端
├── frontend/         # Streamlit前端
├── config/           # 配置
├── docs/             # 文档
└── tests/            # 测试
```

## 核心功能

### 1. 多LLM后端
支持OpenAI、Claude、Ollama等多种LLM，可灵活切换：

```python
from backend.llm.factory import LLMFactory

llm = LLMFactory.create("openai")
response = await llm.chat("Hello!")
```

### 2. 工具调用
Agent可以调用外部工具完成复杂任务：

```python
from backend.tools.registry import get_tool

search_tool = get_tool("search")
result = await search_tool.execute(query="AI news")
```

### 3. 记忆系统
- **短期记忆**：对话历史管理
- **长期记忆**：向量存储的语义检索

### 4. RAG检索
上传文档，进行智能问答：

```python
from backend.rag.pipeline import RAGPipeline

rag = RAGPipeline()
await rag.add_document("./doc.pdf")
answer = await rag.query("文档讲了什么？")
```

### 5. 多Agent协作
多个Agent分工协作完成复杂任务：

```
用户任务 → 研究Agent → 代码Agent → 审查Agent → 最终结果
```

## 学习路线

1. **阶段一**：熟悉项目结构，理解架构设计
2. **阶段二**：学习LLM抽象层，了解多后端设计
3. **阶段三**：实现工具系统，理解Function Calling
4. **阶段四**：实现记忆系统，学习上下文管理
5. **阶段五**：实现RAG，学习检索增强
6. **阶段六**：实现单Agent，理解ReAct模式
7. **阶段七**：实现多Agent，学习LangGraph编排

## 文档

- [需求说明书](docs/spec.md) - 功能需求和约束
- [设计文档](docs/design.md) - 技术架构和实现方案
- [任务清单](docs/task.md) - 开发进度追踪

## 面试准备

本项目展示的核心能力：
- ✅ 主流Agent框架使用（LangChain/LangGraph）
- ✅ 多LLM集成能力
- ✅ 工具调用与Function Calling
- ✅ RAG系统设计
- ✅ 多Agent协作架构
- ✅ API设计与实现

## 开发状态

当前阶段：项目脚手架搭建

详细进度见 [task.md](docs/task.md)

## License

MIT
