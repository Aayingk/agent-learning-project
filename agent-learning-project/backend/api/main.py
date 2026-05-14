"""
FastAPI主应用
Agent系统的REST API服务
"""

import sys
import io

# 设置stdout编码为utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List

from backend.api.schemas import (
    ChatRequest,
    ChatResponse as APIChatResponse,
    ToolCall as APIToolCall,
    MultiAgentRequest,
    MultiAgentResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    HealthResponse,
    ErrorResponse,
)
from backend.llm import LLMFactory, Message
from backend.agents import ReActAgent, ConversationalAgent, ToolAgent
from backend.agents.multi_agent import MultiAgentOrchestrator
from backend.memory import MemoryManager
from backend.tools import ToolRegistry
from backend.rag import RAGPipeline
from config.settings import settings


# 全局依赖
memory_manager = MemoryManager()
rag_pipeline: RAGPipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    global rag_pipeline
    try:
        rag_pipeline = RAGPipeline()
        print("RAG pipeline initialized")
    except Exception as e:
        print(f"Warning: RAG pipeline initialization failed: {e}")

    yield

    # 关闭时清理
    print("Shutting down...")


# 创建FastAPI应用
app = FastAPI(
    title="Agent Learning Project API",
    description="基于多Agent的智能助手API",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 依赖注入
def get_llm(provider: str = "openai"):
    """获取LLM客户端"""
    try:
        return LLMFactory.create(provider)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM初始化失败: {str(e)}")


# ============ 基础端点 ============

@app.get("/", response_model=HealthResponse)
async def root():
    """根路径"""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        agents_available=["react", "conversational", "tool", "multi"],
        tools_available=ToolRegistry.list_all(),
        llm_providers=LLMFactory.list_providers(),
    )


@app.get("/health", response_model=HealthResponse)
async def health():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        agents_available=["react", "conversational", "tool", "multi"],
        tools_available=ToolRegistry.list_all(),
        llm_providers=LLMFactory.list_providers(),
    )


@app.get("/tools")
async def list_tools():
    """列出所有可用工具"""
    tools = ToolRegistry.get_all_tools()
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "parameters": [p.model_dump() for p in tool.parameters],
            }
            for name, tool in tools.items()
        ]
    }


@app.get("/agents")
async def list_agents():
    """列出所有可用Agent"""
    return {
        "agents": [
            {
                "type": "react",
                "name": "ReAct Agent",
                "description": "基于推理-行动模式的智能Agent",
            },
            {
                "type": "conversational",
                "name": "Conversational Agent",
                "description": "专注于多轮对话的Agent",
            },
            {
                "type": "tool",
                "name": "Tool Agent",
                "description": "专注于工具调用的Agent",
            },
            {
                "type": "multi",
                "name": "Multi-Agent",
                "description": "多Agent协作系统",
            },
        ]
    }


# ============ 单Agent端点 ============

@app.post("/chat", response_model=APIChatResponse)
async def chat(request: ChatRequest, llm=Depends(get_llm)):
    """单Agent对话"""
    try:
        # 创建Agent
        if request.agent_type == "react":
            agent = ReActAgent(llm=llm, memory_manager=memory_manager)
        elif request.agent_type == "conversational":
            agent = ConversationalAgent(llm=llm, memory_manager=memory_manager)
        elif request.agent_type == "tool":
            agent = ToolAgent(llm=llm, memory_manager=memory_manager)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"未知Agent类型: {request.agent_type}",
            )

        # 设置温度参数
        if request.temperature is not None:
            agent.config.temperature = request.temperature

        # 运行Agent
        response = await agent.run(
            input_message=request.message,
            session_id=request.session_id,
        )

        # 转换工具调用
        tool_calls = []
        if response.tool_calls:
            import json
            for tc in response.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except:
                    args = {}
                tool_calls.append(
                    APIToolCall(
                        tool=tc.function.name,
                        arguments=args,
                    )
                )

        return APIChatResponse(
            response=response.content,
            session_id=request.session_id,
            agent_type=request.agent_type,
            tool_calls=tool_calls,
            tokens_used=response.usage.model_dump() if response.usage else None,
            metadata={
                "model": response.model,
                "finish_reason": response.finish_reason,
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat/{session_id}")
async def clear_chat(session_id: str):
    """清除会话"""
    memory_manager.clear_session(session_id)
    return {"message": f"会话 {session_id} 已清除"}


# ============ 多Agent端点 ============

@app.post("/chat/multi", response_model=MultiAgentResponse)
async def multi_agent_chat(request: MultiAgentRequest, llm=Depends(get_llm)):
    """多Agent协作对话"""
    try:
        orchestrator = MultiAgentOrchestrator(llm=llm)

        result = await orchestrator.execute(
            task=request.task,
            session_id=request.session_id,
            workflow=request.workflow,
        )

        return MultiAgentResponse(
            answer=result["answer"],
            workflow=result["workflow"],
            steps=result["steps"],
            session_id=request.session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/multi/info")
async def multi_agent_info(llm=Depends(get_llm)):
    """多Agent系统信息"""
    orchestrator = MultiAgentOrchestrator(llm=llm)
    return {"agents": orchestrator.get_agents_info()}


# ============ RAG端点 ============

@app.post("/rag/upload", response_model=DocumentUploadResponse)
async def upload_document(request: DocumentUploadRequest, llm=Depends(get_llm)):
    """上传文档到RAG系统"""
    try:
        if rag_pipeline is None:
            raise HTTPException(
                status_code=503,
                detail="RAG系统未初始化",
            )

        result = await rag_pipeline.add_document(
            path=request.file_path,
            metadata=request.metadata,
        )

        return DocumentUploadResponse(
            success=True,
            message=f"文档已添加，共分割为 {result['chunks_added']} 个块",
            chunks_added=result["chunks_added"],
            document_id=result["ids"][0] if result["ids"] else None,
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(request: RAGQueryRequest, llm=Depends(get_llm)):
    """RAG查询"""
    try:
        if rag_pipeline is None:
            raise HTTPException(
                status_code=503,
                detail="RAG系统未初始化",
            )

        result = await rag_pipeline.query(
            question=request.question,
            llm=llm,
            top_k=request.top_k,
            context_only=request.context_only,
        )

        if request.context_only:
            return RAGQueryResponse(
                answer=result.get("context", ""),
                sources=result.get("sources", []),
            )

        return RAGQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            usage=result.get("usage"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/rag/stats")
async def rag_stats():
    """RAG系统统计"""
    if rag_pipeline is None:
        return {"status": "not_initialized"}

    return rag_pipeline.get_stats()


@app.delete("/rag/clear")
async def rag_clear():
    """清空RAG文档"""
    if rag_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail="RAG系统未初始化",
        )

    rag_pipeline.clear()
    return {"message": "RAG文档已清空"}


# ============ 异常处理 ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
