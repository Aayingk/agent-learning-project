# Agent Learning Project - 技术设计方案

## 1. 架构概览

### 1.1 整体架构
```
┌─────────────────────────────────────────────────────────┐
│                      Frontend Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Streamlit   │  │  FastAPI     │  │     CLI      │  │
│  │    Chat UI   │  │  REST API    │  │  Interface   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼─────────────────┼─────────────────┼──────────┘
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
┌───────────────────────────▼───────────────────────────┐
│                      Service Layer                     │
│  ┌─────────────────────────────────────────────────┐  │
│  │              Agent Orchestration                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │   Single │  │   Multi  │  │    RAG       │  │  │
│  │  │   Agent  │  │   Agent  │  │    Agent     │  │  │
│  │  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │  │
│  └───────┼─────────────┼─────────────────┼──────────┘  │
└──────────┼─────────────┼─────────────────┼─────────────┘
           │             │                 │
┌──────────▼─────────────▼─────────────────▼─────────────┐
│                      Core Capabilities                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │   LLM    │  │  Tools   │  │  Memory  │  │ Vector │ │
│  │ Provider │  │  Engine  │  │  Manager │  │  Store │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 1.2 技术栈选型

| 层次 | 技术选择 | 理由 |
|------|---------|------|
| Agent框架 | LangChain + LangGraph | 行业标准，生态完善，面试常问 |
| LLM后端 | OpenAI/Claude/Ollama | 覆盖主流API+本地方案 |
| 向量存储 | ChromaDB | 轻量、易部署、适合学习 |
| API框架 | FastAPI | 现代化、自动文档、异步支持 |
| 前端 | Streamlit | 快速原型、Python原生 |
| 嵌入模型 | OpenAI Embedding / 本地 | 成熟稳定 |

---

## 2. 模块设计

### 2.1 LLM Provider（多后端支持）
```python
# 设计思路：抽象基类 + 工厂模式
class BaseLLM(ABC):
    @abstractmethod
    async def chat(self, messages, tools=None) -> ChatResponse
    @abstractmethod
    async def embed(self, text) -> List[float]

class OpenAILLM(BaseLLM): ...
class AnthropicLLM(BaseLLM): ...
class OllamaLLM(BaseLLM): ...

class LLMFactory:
    @staticmethod
    def create(provider: str) -> BaseLLM
```

**为什么这样设计**：
- 易于扩展新的LLM提供商
- 统一接口，上层代码无需关心具体实现
- 便于测试和mock

### 2.2 Tools Engine（工具调用）
```python
# 设计思路：装饰器注册 + 标准化工具接口
class Tool(ABC):
    name: str
    description: str
    parameters: dict

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult

# 工具注册中心
class ToolRegistry:
    _tools: Dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool)
    @classmethod
    def get(cls, name: str) -> Tool
    @classmethod
    def list_all(cls) -> List[Tool]

# 内置工具
@register_tool
class SearchTool(Tool): ...
@register_tool
class CalculatorTool(Tool): ...
@register_tool
class FileReadTool(Tool): ...
```

**为什么这样设计**：
- 装饰器注册，添加新工具零侵入
- 标准化接口，所有工具行为一致
- 工具元数据自动生成LLM function calling schema

### 2.3 Memory Manager（记忆系统）
```python
# 设计思路：分层存储
class MemoryManager:
    def __init__(self):
        self.short_term = ShortTermMemory()  # 对话历史
        self.long_term = LongTermMemory()     # 向量存储

class ShortTermMemory:
    def add(self, message: Message)
    def get_recent(self, n: int) -> List[Message]
    def get_context_window(self, limit: int) -> List[Message]

class LongTermMemory:
    def add(self, content: str, metadata: dict)
    def search(self, query: str, top_k: int) -> List[Document]
    def clear(self)
```

**为什么这样设计**：
- 短期/长期分离，各司其职
- 短期关注窗口管理，长期关注语义检索
- 便于后续扩展（如Redis持久化）

### 2.4 RAG Pipeline
```python
# 设计思路：管道模式
class RAGPipeline:
    def __init__(self):
        self.embedder = Embedder()
        self.vector_store = ChromaDBStore()
        self.retriever = Retriever()
        self.reranker = Optional[Reranker]

    async def add_document(self, doc: Document)
    async def query(self, question: str) -> List[Document]

class Embedder:
    async def embed(self, texts: List[str]) -> List[List[float]]

class Retriever:
    async def retrieve(self, query: str, top_k: int) -> List[Document]
```

**为什么这样设计**：
- 管道模式，每个环节职责单一
- 可替换组件（如更换embedder）
- 支持后续优化（如重排序、混合检索）

### 2.5 Multi-Agent（多Agent协作）
```python
# 设计思路：基于LangGraph的状态机
class MultiAgentOrchestrator:
    def __init__(self):
        self.agents = {
            "researcher": ResearchAgent(),
            "coder": CodeAgent(),
            "reviewer": ReviewAgent()
        }
        self.workflow = self._build_workflow()

    def _build_workflow(self):
        # LangGraph定义状态流转
        graph = StateGraph(AgentState)
        graph.add_node("researcher", self.agents["researcher"])
        graph.add_node("coder", self.agents["coder"])
        graph.add_node("reviewer", self.agents["reviewer"])
        # 定义边和条件边
        graph.add_edge("researcher", "coder")
        graph.add_conditional_edges("coder", self._should_review)
        return graph.compile()
```

**为什么这样设计**：
- LangGraph是标准的多Agent编排框架
- 状态机清晰，易于理解和调试
- 支持复杂的条件流转

---

## 3. 数据流设计

### 3.1 单Agent对话流程
```
用户输入
    ↓
[会话管理] 加载历史
    ↓
[LLM] 决策：直接回复 or 调用工具
    ↓
    ├→ 直接回复 → 输出
    │
    └→ 工具调用
        ↓
    [Tool Engine] 执行工具
        ↓
    [LLM] 基于工具结果生成回复
        ↓
    输出 + 更新历史
```

### 3.2 RAG查询流程
```
用户问题
    ↓
[Embedder] 问题向量化
    ↓
[Vector Store] 语义检索
    ↓
[Retriever] 获取Top-K文档
    ↓
[LLM] 基于检索结果生成答案
    ↓
输出答案 + 引用来源
```

### 3.3 多Agent协作流程
```
用户任务
    ↓
[Orchestrator] 任务分解
    ↓
┌──────────┐
│ Agent A  │ 执行子任务1
└────┬─────┘
     ↓ 结果1
┌──────────┐
│ Agent B  │ 基于结果1执行子任务2
└────┬─────┘
     ↓ 结果2
┌──────────┐
│ Agent C  │ 整合最终结果
└────┬─────┘
     ↓
    输出
```

---

## 4. 关键技术决策

### 4.1 为什么用LangChain而不是自己实现？
| 方案 | 优点 | 缺点 |
|------|------|------|
| LangChain | 标准框架、生态丰富、面试常问 | 抽象多、学习曲线 |
| 自实现 | 完全控制、学习原理 | 重复造轮子、非生产级 |

**决策**：使用LangChain
- 求职需要展示主流框架使用能力
- 企业级项目都是用框架，不是从零写
- 通过阅读源码也能学习原理

### 4.2 为什么ChromaDB而不是其他向量库？
| 方案 | 优点 | 缺点 |
|------|------|------|
| ChromaDB | 轻量、易部署、Python原生 | 性能不如专业方案 |
| Pinecone | 云服务、高性能 | 需要付费、有网络延迟 |
| Milvus | 性能强、功能全 | 部署复杂、重量级 |

**决策**：ChromaDB
- 学习阶段不需要高性能
- 本地运行，无需云服务
- 快速上手，专注Agent逻辑

### 4.3 为什么Streamlit而不是Gradio？
| 方案 | 优点 | 缺点 |
|------|------|------|
| Streamlit | 纯Python、快速开发 | 定制能力有限 |
| Gradio | ML友好、组件丰富 | 依赖稍重 |

**决策**：Streamlit
- 代码更简洁，适合快速原型
- 对用户来说前端不重要
- 满足demo需求即可

---

## 5. 非功能性设计

### 5.1 可扩展性
- 新增LLM：继承BaseLLM，在工厂注册
- 新增工具：用@register_tool装饰器
- 新增Agent：继承BaseAgent

### 5.2 可测试性
- 所有核心逻辑有接口，便于mock
- 工具可独立测试
- LLM调用可mock响应

### 5.3 可观测性
- 日志记录关键决策点
- Token使用统计
- 工具调用追踪

### 5.4 错误处理
| 场景 | 处理策略 |
|------|---------|
| LLM超时 | 重试1次，失败则返回友好提示 |
| 工具失败 | 记录错误，让LLM知道并尝试恢复 |
| 向量检索无结果 | 不使用RAG，直接回答 |
| 配置错误 | 启动时校验，给出明确提示 |

---

## 6. 目录结构设计

```
agent-learning-project/
├── backend/
│   ├── api/                    # FastAPI服务
│   │   ├── __init__.py
│   │   ├── main.py             # API入口
│   │   ├── routes/             # 路由模块
│   │   │   ├── chat.py
│   │   │   ├── rag.py
│   │   │   └── agents.py
│   │   └── models/             # Pydantic模型
│   │       └── schemas.py
│   │
│   ├── agents/                 # Agent实现
│   │   ├── __init__.py
│   │   ├── base.py             # 基类
│   │   ├── single_agent.py     # 单Agent
│   │   └── multi_agent.py      # 多Agent
│   │
│   ├── tools/                  # 工具系统
│   │   ├── __init__.py
│   │   ├── base.py             # 工具基类
│   │   ├── registry.py         # 工具注册
│   │   ├── search.py           # 搜索工具
│   │   ├── calculator.py       # 计算器
│   │   └── file_ops.py         # 文件操作
│   │
│   ├── memory/                 # 记忆系统
│   │   ├── __init__.py
│   │   ├── short_term.py       # 短期记忆
│   │   └── long_term.py        # 长期记忆
│   │
│   ├── rag/                    # RAG模块
│   │   ├── __init__.py
│   │   ├── embeddings.py       # 嵌入模型
│   │   ├── vectorstore.py      # 向量存储
│   │   └── retriever.py        # 检索器
│   │
│   └── llm/                    # LLM后端
│       ├── __init__.py
│       ├── base.py             # 基类
│       ├── factory.py          # 工厂
│       ├── openai_client.py
│       ├── anthropic_client.py
│       └── ollama_client.py
│
├── frontend/                   # Streamlit前端
│   ├── app.py                  # 主应用
│   ├── pages/                  # 多页面
│   │   ├── chat.py
│   │   ├── rag.py
│   │   └── multi_agent.py
│   └── components/             # UI组件
│
├── config/                     # 配置
│   ├── __init__.py
│   ├── settings.py             # 配置类
│   └── prompts.py              # 提示词模板
│
├── tests/                      # 测试
│   ├── test_tools.py
│   ├── test_memory.py
│   └── test_agents.py
│
├── docs/                       # 文档
│   ├── spec.md                 # 需求说明书
│   ├── design.md               # 设计文档
│   └── task.md                 # 任务清单
│
├── requirements.txt            # 依赖
├── .env.example                # 环境变量示例
├── .gitignore
└── README.md                   # 项目说明
```

---

## 7. Trade-offs与风险

### 7.1 已知Trade-offs
| 决策 | 收益 | 代价 |
|------|------|------|
| 使用ChromaDB | 快速上手 | 生产需替换 |
| 同步API | 简单易理解 | 高并发需改造 |
| 内存存储 | 零配置 | 重启丢失 |

### 7.2 潜在风险与缓解
| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| LLM API限流 | 中 | 中 | 实现重试+降级 |
| Token超限 | 高 | 低 | 实现窗口管理 |
| 依赖版本冲突 | 中 | 中 | 固定版本号 |

---

## 8. 后续优化方向

1. **性能优化**：异步并发、连接池、缓存
2. **可观测性**：APM、链路追踪、指标监控
3. **部署**：Docker化、K8s编排、CI/CD
4. **安全**：API鉴权、输入校验、敏感信息过滤
