# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Management

This project uses **uv** as the package manager (not pip/poetry).

```bash
# Install all dependencies
uv sync

# Install specific dependency group
uv sync --extra core
uv sync --extra dev

# Run Python with uv
uv run python script.py
```

## Common Commands

```bash
# API Server (FastAPI with auto-reload)
uvicorn backend.api.main:app --reload
# Access API docs at http://localhost:8000/docs

# Frontend (Streamlit)
streamlit run frontend/app.py

# Code formatting
black backend/ config/ --line-length 100
ruff check backend/ config/

# Run tests (when implemented)
pytest tests/
pytest tests/test_tools.py -v  # single test file
```

## Architecture Overview

```
Frontend (Streamlit) → API (FastAPI) → Service Layer → Core Capabilities
                                                    ├─ LLM Provider
                                                    ├─ Tools Engine
                                                    ├─ Memory Manager
                                                    └─ Vector Store
```

### LLM Abstraction Layer

**Factory pattern** for multi-provider support. All LLM clients inherit from `BaseLLM`:

```python
from backend.llm import LLMFactory

llm = LLMFactory.create("deepseek")  # or "openai", "anthropic", "glm", "ollama"
response = await llm.chat(messages=[...])
```

- **Base classes**: `backend/llm/base.py`
- **Factory**: `backend/llm/factory.py`
- **Models**: `backend/llm/models.py` (Pydantic models for Message, ChatResponse, etc.)

Adding a new provider: Implement `BaseLLM`, register in `LLMFactory._providers`.

### Tools System

**Decorator-based registration**. Tools are registered via `@register_tool`:

```python
from backend.tools import register_tool, Tool

@register_tool
class MyTool(Tool):
    name = "my_tool"
    description = "Does something"
    # ...
```

- **Base**: `backend/tools/base.py`
- **Registry**: `backend/tools/registry.py`

### Memory System

**Two-tier storage** - short-term (session) vs long-term (vector):

- `backend/memory/short_term.py` - Conversation history, window management
- `backend/memory/long_term.py` - Vector-based semantic search

Memory solves the Context Window limit problem by selectively retrieving relevant content.

### RAG Pipeline

**Pipeline pattern** for retrieval-augmented generation:

```
Document → Embedder → Vector Store → Retriever → LLM
```

- `backend/rag/embeddings.py` - Text vectorization
- `backend/rag/vectorstore.py` - ChromaDB wrapper
- `backend/rag/retriever.py` - Semantic search
- `backend/rag/pipeline.py` - End-to-end RAG

### Multi-Agent

**LangGraph state machine** for agent orchestration. Agents are specialized roles (researcher, coder, reviewer) coordinated through a state graph.

- `backend/agents/base.py` - Base agent class
- `backend/agents/react_agent.py` - ReAct pattern implementation
- `backend/agents/multi_agent.py` - LangGraph orchestration

## Configuration

- **Settings**: `config/settings.py` - Pydantic Settings class
- **Environment**: `.env` file in project root

**Important**: `.env` files do NOT support inline comments. Use:
```bash
# Correct
KEY=value

# WRONG - will fail to parse
KEY=value  # comment
```

## Learning Materials

Jupyter notebooks are in `docs/lessons/`:
- `L01-LLM-Basics.ipynb` - LLM fundamentals (tokens, context window, temperature)
- Additional lessons follow the curriculum in `docs/learning-curriculum.md`

When working with notebooks, ensure:
1. First cell sets up `sys.path` to include project root
2. API keys are loaded from `.env` (settings singleton loads at import time)

## Key Design Patterns

| Pattern | Where | Why |
|--------|-------|-----|
| Factory | `LLMFactory` | Easy provider switching |
| Decorator Registration | `@register_tool` | Zero-intrusion tool additions |
| Pipeline | `RAGPipeline` | Each stage independently replaceable |
| State Machine | Multi-Agent (LangGraph) | Clear orchestration logic |
| Two-Tier Memory | `MemoryManager` | Separate concerns: window vs retrieval |
