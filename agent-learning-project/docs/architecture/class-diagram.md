# Agent Learning Project - UML Class Diagram

> 完整的项目类图架构

## 1. 整体架构图

```mermaid
graph TB
    subgraph "API Layer"
        API[FastAPI Main]
        Schemas[Pydantic Schemas]
    end

    subgraph "Agent Layer"
        BaseAgent[BaseAgent]
        ReActAgent[ReActAgent]
        ConvAgent[ConversationalAgent]
        ToolAgent[ToolAgent]
        MultiAgent[MultiAgent]
    end

    subgraph "LLM Layer"
        LLMFactory[LLMFactory]
        BaseLLM[BaseLLM]
        DeepSeek[DeepSeekLLM]
        OpenAI[OpenAILLM]
        Anthropic[AnthropicLLM]
        Ollama[OllamaLLM]
        GLM[GLMLLM]
    end

    subgraph "Tools Layer"
        ToolRegistry[ToolRegistry]
        BaseTool[BaseTool]
        Calculator[Calculator]
        Search[SearchTool]
        FileOps[FileOperations]
    end

    subgraph "Memory Layer"
        ShortTerm[ShortTermMemory]
        LongTerm[LongTermMemory]
        Summary[ConversationSummary]
    end

    subgraph "RAG Layer"
        RAGPipeline[RAGPipeline]
        EmbedderFactory[EmbedderFactory]
        BaseEmbedder[BaseEmbedder]
        OAIEmbedder[OpenAIEmbedder]
        STEmbedder[SentenceTransformerEmbedder]
        VectorStore[VectorStore]
        Retriever[RAGRetriever]
    end

    subgraph "Data Models"
        Message[Message]
        ChatResponse[ChatResponse]
        TokenUsage[TokenUsage]
        ToolCall[ToolCall]
        ToolResult[ToolResult]
        AgentConfig[AgentConfig]
        AgentState[AgentState]
    end

    API --> Schemas
    API --> BaseAgent

    BaseAgent --> AgentConfig
    BaseAgent --> LLMFactory
    BaseAgent --> ToolRegistry
    BaseAgent --> ShortTerm

    ReActAgent --> BaseAgent
    ConvAgent --> BaseAgent
    ToolAgent --> BaseAgent
    MultiAgent --> BaseAgent

    LLMFactory --> BaseLLM
    DeepSeek --> BaseLLM
    OpenAI --> BaseLLM
    Anthropic --> BaseLLM
    Ollama --> BaseLLM
    GLM --> BaseLLM

    ToolRegistry --> BaseTool
    Calculator --> BaseTool
    Search --> BaseTool
    FileOps --> BaseTool

    ShortTerm --> Message
    ShortTerm --> Summary

    RAGPipeline --> EmbedderFactory
    RAGPipeline --> VectorStore
    RAGPipeline --> Retriever

    EmbedderFactory --> BaseEmbedder
    OAIEmbedder --> BaseEmbedder
    STEmbedder --> BaseEmbedder

    BaseLLM --> Message
    BaseLLM --> ChatResponse
    BaseTool --> ToolResult
    ChatResponse --> TokenUsage
    ChatResponse --> ToolCall
```

---

## 2. LLM 模块详细类图

```mermaid
classDiagram
    %% 抽象基类
    class BaseLLM {
        <<abstract>>
        +str model
        +str api_key
        +str base_url
        +dict extra_params
        +__init__(model, api_key, base_url)
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
        +supports_tools() bool
        +supports_embedding() bool
        +get_model_info() dict
    }

    class DeepSeekLLM {
        +int timeout
        +int max_retries
        +AsyncOpenAI client
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
        -_convert_messages(messages) list
        -_convert_tools(tools) list
        -_parse_chat_response(response) ChatResponse
    }

    class OpenAILLM {
        +int timeout
        +int max_retries
        +AsyncOpenAI client
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
    }

    class AnthropicLLM {
        +int timeout
        +int max_retries
        +AsyncAnthropic client
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
    }

    class OllamaLLM {
        +str base_url
        +httpx.AsyncClient client
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
    }

    class GLMLLM {
        +int timeout
        +int max_retries
        +httpx.AsyncClient client
        +chat(messages, tools, temperature) ChatResponse
        +embed(texts) EmbeddingResponse
    }

    class LLMFactory {
        <<factory>>
        -dict _providers
        +create(provider, model, **kwargs) BaseLLM
        +register_provider(name, llm_class)
        +list_providers() list
    }

    class LLMError {
        <<exception>>
        +str message
        +str provider
        +dict details
    }

    class LLMRateLimitError {}
    class LLMTimeoutError {}
    class LLMAuthenticationError {}
    class LLMInvalidRequestError {}

    %% 关系
    LLMFactory ..> BaseLLM : creates
    BaseLLM <|-- DeepSeekLLM : extends
    BaseLLM <|-- OpenAILLM : extends
    BaseLLM <|-- AnthropicLLM : extends
    BaseLLM <|-- OllamaLLM : extends
    BaseLLM <|-- GLMLLM : extends

    LLMError <|-- LLMRateLimitError : extends
    LLMError <|-- LLMTimeoutError : extends
    LLMError <|-- LLMAuthenticationError : extends
    LLMError <|-- LLMInvalidRequestError : extends
```

---

## 3. Agent 模块详细类图

```mermaid
classDiagram
    %% 枚举
    class AgentState {
        <<enumeration>>
        IDLE
        THINKING
        ACTING
        DONE
        ERROR
    }

    %% 配置类
    class AgentConfig {
        +str name
        +str description
        +str system_prompt
        +float temperature
        +int max_iterations
        +bool enable_tools
        +bool enable_memory
    }

    class AgentContext {
        +str session_id
        +list messages
        +int current_iteration
        +dict metadata
    }

    %% 抽象基类
    class BaseAgent {
        <<abstract>>
        #AgentConfig config
        #BaseLLM llm
        #MemoryManager memory
        #ToolRegistry _tool_registry
        #AgentState _state
        +__init__(config, llm, memory_manager)
        +run(input_message, session_id) ChatResponse
        +think(messages) ChatResponse
        +act(tool_calls) list
        +add_message(session_id, message)
        +get_messages(session_id) list
        +reset(session_id)
        +get_state() dict
    }

    %% 具体实现
    class ReActAgent {
        +__init__(config, llm, memory_manager)
        +run(input_message, session_id) ChatResponse
        -_get_default_system_prompt() str
        -_get_tools_description() str
    }

    class ConversationalAgent {
        +__init__(config, llm, memory_manager)
        +run(input_message, session_id) ChatResponse
    }

    class ToolAgent {
        +list allowed_tools
        +__init__(config, llm, memory_manager, allowed_tools)
        +run(input_message, session_id) ChatResponse
        -_get_system_prompt() str
        -_format_tool_results(results) str
    }

    %% 关系
    AgentState --o BaseAgent : uses
    AgentConfig --o BaseAgent : configures
    AgentContext --o BaseAgent : context

    BaseAgent <|-- ReActAgent : extends
    BaseAgent <|-- ConversationalAgent : extends
    BaseAgent <|-- ToolAgent : extends

    BaseAgent --> BaseLLM : uses
    BaseAgent --> ToolRegistry : uses
    BaseAgent --> MemoryManager : uses
```

---

## 4. Tools 模块详细类图

```mermaid
classDiagram
    %% 数据模型
    class ToolResult {
        +bool success
        +any data
        +str error
        +dict metadata
        +success_result(data, metadata) ToolResult
        +error_result(error, metadata) ToolResult
    }

    class ToolParameter {
        +str name
        +str type
        +str description
        +bool required
        +any default
        +list enum
    }

    %% 抽象基类
    class BaseTool {
        <<abstract>>
        +str name
        +str description
        +list parameters
        +int timeout
        +bool async_execution
        +__init__()
        +execute(**kwargs) ToolResult
        +aexecute(**kwargs) ToolResult
        +get_schema() dict
        +validate_parameters(params) tuple
        +to_llm_tool_definition() dict
    }

    %% 单例注册表
    class ToolRegistry {
        <<singleton>>
        -ToolRegistry _instance
        -dict _tools
        +__new__() ToolRegistry
        +register(tool) BaseTool
        +register_class(tool_class) type
        +get(name) BaseTool
        +list_all() list
        +get_all_tools() dict
        +get_llm_tool_definitions() list
        +clear()
        +unregister(name) bool
    }

    %% 具体工具
    class Calculator {
        +str name = "calculator"
        +str description
        +list parameters
        +execute(expression) ToolResult
    }

    class SearchTool {
        +str name = "search"
        +str description
        +list parameters
        +execute(query, num_results) ToolResult
    }

    class FileOperations {
        +str name = "file_ops"
        +str description
        +list parameters
        +execute(action, path, content) ToolResult
    }

    %% 装饰器
    class register_tool {
        <<decorator>>
        +register_tool(tool_class) type
    }

    %% 异常
    class ToolError {
        <<exception>>
        +str tool_name
        +str message
        +dict details
    }

    class ToolTimeoutError {}
    class ToolValidationError {}

    %% 关系
    ToolRegistry --> BaseTool : manages
    BaseTool <|-- Calculator : extends
    BaseTool <|-- SearchTool : extends
    BaseTool <|-- FileOperations : extends
    BaseTool --> ToolResult : returns
    BaseTool --> ToolParameter : contains

    register_tool ..> ToolRegistry : uses

    ToolError <|-- ToolTimeoutError : extends
    ToolError <|-- ToolValidationError : extends
```

---

## 5. Memory 模块详细类图

```mermaid
classDiagram
    class ShortTermMemory {
        -int max_messages
        -int max_tokens
        -int session_ttl
        -dict _sessions
        -dict _last_active
        +add_message(session_id, message)
        +get_messages(session_id, limit) list
        +get_context(session_id, max_tokens) list
        +get_system_context(session_id, system_message) list
        +clear_session(session_id) bool
        +get_session_info(session_id) dict
        +list_sessions() list
        -_cleanup_if_needed(session_id)
        -_is_expired(session_id) bool
        -_cleanup_expired()
    }

    class ConversationSummary {
        +__init__()
        +summarize(messages) str
        +llm_summarize(messages, llm) str
    }

    class LongTermMemory {
        -VectorStore vector_store
        -BaseEmbedder embedder
        +add_memory(session_id, content, metadata)
        +search(query, top_k) list
        +get_memories(session_id) list
        +clear_session(session_id)
    }

    class MemoryManager {
        +ShortTermMemory short_term
        +LongTermMemory long_term
        +add_message(session_id, message)
        +get_context(session_id, max_tokens) list
        +search_memory(query, top_k) list
        +clear_session(session_id)
    }

    class Message {
        +str role
        +str content
        +str tool_call_id
        +list tool_calls
        +dict metadata
    }

    %% 关系
    MemoryManager --> ShortTermMemory : has
    MemoryManager --> LongTermMemory : has
    ShortTermMemory --> Message : stores
    ShortTermMemory --> ConversationSummary : uses
    LongTermMemory --> VectorStore : uses
    LongTermMemory --> BaseEmbedder : uses
```

---

## 6. RAG 模块详细类图

```mermaid
classDiagram
    %% 嵌入模型
    class BaseEmbedder {
        <<abstract>>
        +embed(texts) list
        +get_dimension() int
    }

    class OpenAIEmbedder {
        -BaseLLM llm
        -str model
        +embed(texts) list
        +get_dimension() int
    }

    class SentenceTransformerEmbedder {
        -str model_name
        -str device
        -SentenceTransformer _model
        +embed(texts) list
        +get_dimension() int
        -_load_model()
    }

    class EmbedderFactory {
        <<factory>>
        +create(provider, model, **kwargs) BaseEmbedder
    }

    %% 向量存储
    class VectorStore {
        -str persist_dir
        -str collection_name
        -int embedding_dimension
        -ChromaDB client
        +add_texts(texts, metadatas)
        +search(query_vector, top_k) list
        +delete(ids)
        +get_stats() dict
        +clear()
    }

    %% 检索器
    class RAGRetriever {
        -VectorStore vector_store
        -BaseEmbedder embedder
        +retrieve(query, top_k) list
        +add_document(path, metadata) dict
        +delete_document(document_id)
    }

    %% RAG 管道
    class RAGPipeline {
        -BaseEmbedder embedder
        -VectorStore vector_store
        -RAGRetriever retriever
        +__init__(embedder_provider, persist_dir, collection_name)
        +add_document(path, metadata) dict
        +add_directory(directory, pattern, metadata) dict
        +query(question, llm, top_k, context_only) dict
        +get_stats() dict
        +clear()
        -_format_context(results) str
        -_get_system_prompt() str
        -_build_prompt(question, context) str
    }

    %% 关系
    EmbedderFactory ..> BaseEmbedder : creates
    BaseEmbedder <|-- OpenAIEmbedder : extends
    BaseEmbedder <|-- SentenceTransformerEmbedder : extends

    RAGPipeline --> BaseEmbedder : uses
    RAGPipeline --> VectorStore : uses
    RAGPipeline --> RAGRetriever : uses

    RAGRetriever --> VectorStore : uses
    RAGRetriever --> BaseEmbedder : uses
```

---

## 7. 数据模型详细类图

```mermaid
classDiagram
    class Message {
        +str role
        +str content
        +str tool_call_id
        +list~ToolCall~ tool_calls
        +dict metadata
    }

    class ToolCall {
        +str id
        +str type
        +FunctionCall function
    }

    class FunctionCall {
        +str name
        +str arguments
    }

    class ToolDefinition {
        +str type
        +FunctionDefinition function
    }

    class FunctionDefinition {
        +str name
        +str description
        +dict parameters
    }

    class ChatResponse {
        +str content
        +str role
        +list~ToolCall~ tool_calls
        +str finish_reason
        +TokenUsage usage
        +str model
        +dict raw_response
    }

    class TokenUsage {
        +int prompt_tokens
        +int completion_tokens
        +int total_tokens
        +__add__(other) TokenUsage
    }

    class EmbeddingResponse {
        +list~list~ embeddings
        +str model
        +TokenUsage usage
    }

    class AgentConfig {
        +str name
        +str description
        +str system_prompt
        +float temperature
        +int max_iterations
        +bool enable_tools
        +bool enable_memory
    }

    class ToolResult {
        +bool success
        +any data
        +str error
        +dict metadata
    }

    class ToolParameter {
        +str name
        +str type
        +str description
        +bool required
        +any default
        +list enum
    }

    %% 关系
    Message --> ToolCall : contains
    ToolCall --> FunctionCall : contains
    ToolDefinition --> FunctionDefinition : contains
    ChatResponse --> TokenUsage : contains
    ChatResponse --> ToolCall : contains
```

---

## 8. 设计模式标记

```mermaid
graph TB
    subgraph "工厂模式 Factory Pattern"
        F1[LLMFactory]
        F2[EmbedderFactory]
    end

    subgraph "单例模式 Singleton Pattern"
        S1[ToolRegistry]
    end

    subgraph "装饰器模式 Decorator Pattern"
        D1[@register_tool]
    end

    subgraph "模板方法模式 Template Method Pattern"
        T1[BaseLLM]
        T2[BaseAgent]
        T3[BaseTool]
        T4[BaseEmbedder]
    end

    subgraph "策略模式 Strategy Pattern"
        ST1[DeepSeekLLM]
        ST2[OpenAILLM]
        ST3[AnthropicLLM]
    end

    subgraph "状态模式 State Pattern"
        ST[AgentState]
    end

    subgraph "管道模式 Pipeline Pattern"
        P1[RAGPipeline]
    end

    subgraph "观察者模式 Observer Pattern"
        O1[ConversationSummary]
    end
```

---

## 9. 时序图：ReAct Agent 执行流程

```mermaid
sequenceDiagram
    participant User
    participant ReActAgent
    participant BaseLLM
    participant ToolRegistry
    participant BaseTool
    participant ShortTermMemory

    User->>ReActAgent: run("现在几点?")
    ReActAgent->>ShortTermMemory: get_messages(session_id)
    ShortTermMemory-->>ReActAgent: [历史消息]

    ReActAgent->>ReActAgent: iteration = 0
    ReActAgent->>BaseLLM: think(messages + system_prompt)
    BaseLLM-->>ReActAgent: ChatResponse(tool_calls=[get_time])

    ReActAgent->>ToolRegistry: get("get_time")
    ToolRegistry-->>ReActAgent: TimeTool

    ReActAgent->>BaseTool: aexecute()
    BaseTool-->>ReActAgent: ToolResult(data="2024-01-15 14:30")

    ReActAgent->>ReActAgent: iteration = 1
    ReActAgent->>BaseLLM: think(messages + tool_result)
    BaseLLM-->>ReActAgent: ChatResponse(content="现在时间是...")

    ReActAgent->>ShortTermMemory: add_message(user_msg)
    ReActAgent->>ShortTermMemory: add_message(assistant_msg)

    ReActAgent-->>User: ChatResponse
```

---

## 10. 时序图：LLM 工厂创建

```mermaid
sequenceDiagram
    participant Client
    participant LLMFactory
    participant DeepSeekLLM
    participant OpenAILLM
    participant BaseLLM

    Client->>LLMFactory: create("deepseek", api_key="...")
    LLMFactory->>LLMFactory: check provider in _providers
    LLMFactory->>LLMFactory: get_llm_credentials("deepseek")
    LLMFactory->>DeepSeekLLM: new DeepSeekLLM(model, api_key)
    DeepSeekLLM->>BaseLLM: __init__(model, api_key)
    DeepSeekLLM-->>LLMFactory: instance
    LLMFactory-->>Client: DeepSeekLLM instance

    Client->>LLMFactory: create("openai", api_key="...")
    LLMFactory->>OpenAILLM: new OpenAILLM(model, api_key)
    OpenAILLM-->>LLMFactory: instance
    LLMFactory-->>Client: OpenAILM instance
```

---

## 11. 组件交互图

```mermaid
graph LR
    subgraph "用户请求"
        U[用户输入]
    end

    subgraph "Agent 处理"
        A[Agent]
        A1[思考: LLM]
        A2[行动: Tool]
        A3[观察: Result]
    end

    subgraph "数据存储"
        M[Memory]
        V[VectorStore]
    end

    subgraph "外部服务"
        L[LLM API]
        S[Search API]
    end

    U --> A
    A --> A1
    A1 --> L
    L --> A1
    A1 --> A2
    A2 --> S
    S --> A3
    A3 --> A1

    A --> M
    A --> V
    M --> A
```

---

> 本类图涵盖了项目的核心架构：
> - **LLM 抽象层**：多提供商支持
> - **Agent 系统**：ReAct 循环实现
> - **工具系统**：装饰器注册模式
> - **记忆系统**：短期 + 长期记忆
> - **RAG 系统**：检索增强生成
