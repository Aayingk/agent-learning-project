"""
Streamlit前端应用
Agent Learning Project的可视化界面
"""

import asyncio
import io
import sys

# 设置编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Agent Learning Project",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义CSS
st.markdown("""
<style>
    .stChatMessage {
        background-color: #f0f2f6;
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        font-weight: 500;
        color: #4b5563;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ============ 会话状态初始化 ============

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

if "agent_type" not in st.session_state:
    st.session_state.agent_type = "react"

if "llm_provider" not in st.session_state:
    st.session_state.llm_provider = "openai"


# ============ 侧边栏配置 ============

with st.sidebar:
    st.markdown("## ⚙️ 配置")

    # LLM选择
    st.session_state.llm_provider = st.selectbox(
        "LLM提供商",
        ["openai", "anthropic", "ollama", "glm", "deepseek"],
        index=0,
    )

    # Agent类型选择
    st.markdown("---")
    st.markdown("### 🤖 Agent模式")
    st.session_state.agent_type = st.radio(
        "选择Agent类型",
        ["react", "conversational", "tool", "multi"],
        format_func=lambda x: {
            "react": "ReAct Agent",
            "conversational": "对话Agent",
            "tool": "工具Agent",
            "multi": "多Agent协作",
        }.get(x, x),
    )

    # 多Agent工作流选择
    if st.session_state.agent_type == "multi":
        st.session_state.workflow = st.selectbox(
            "工作流类型",
            ["standard", "code_review", "research"],
            format_func=lambda x: {
                "standard": "标准流程",
                "code_review": "代码审查",
                "research": "深度研究",
            }.get(x, x),
        )

    # 温度参数
    st.markdown("---")
    st.session_state.temperature = st.slider(
        "温度参数",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.1,
    )

    # 会话操作
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 新对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.rerun()
    with col2:
        if st.button("🗑️ 清除", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    # 系统信息
    st.markdown("---")
    st.markdown("### 📊 系统信息")
    st.markdown(f"""
    - **会话ID**: `{st.session_state.session_id[-8:]}`
    - **消息数**: {len(st.session_state.messages)}
    - **Agent**: {st.session_state.agent_type}
    """)


# ============ 主界面 ============

st.markdown('<h1 class="main-header">🤖 Agent Learning Project</h1>', unsafe_allow_html=True)

# 标签页
tab1, tab2, tab3 = st.tabs(["💬 对话", "📚 RAG问答", "ℹ️ 关于"])


# ============ 对话标签页 ============

with tab1:
    st.markdown('<div class="sub-header">与Agent对话</div>', unsafe_allow_html=True)

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "tool_calls" in msg and msg["tool_calls"]:
                with st.expander("🔧 工具调用"):
                    for tc in msg["tool_calls"]:
                        st.code(f"{tc['tool']}: {tc['arguments']}")

    # 用户输入
    if prompt := st.chat_input("输入你的消息..."):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 调用Agent
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                try:
                    # 动态导入以避免启动时加载
                    from backend.llm import LLMFactory
                    from backend.agents import ReActAgent, ConversationalAgent, ToolAgent
                    from backend.agents.multi_agent import MultiAgentOrchestrator
                    from backend.memory import MemoryManager

                    # 初始化
                    llm = LLMFactory.create(st.session_state.llm_provider)
                    memory_manager = MemoryManager()

                    # 根据类型创建Agent
                    if st.session_state.agent_type == "react":
                        agent = ReActAgent(llm=llm, memory_manager=memory_manager)
                        response = await asyncio.run(agent.run(
                            input_message=prompt,
                            session_id=st.session_state.session_id,
                        ))
                        response_text = response.content

                    elif st.session_state.agent_type == "conversational":
                        agent = ConversationalAgent(llm=llm, memory_manager=memory_manager)
                        response = await asyncio.run(agent.run(
                            input_message=prompt,
                            session_id=st.session_state.session_id,
                        ))
                        response_text = response.content

                    elif st.session_state.agent_type == "tool":
                        agent = ToolAgent(llm=llm, memory_manager=memory_manager)
                        response = await asyncio.run(agent.run(
                            input_message=prompt,
                            session_id=st.session_state.session_id,
                        ))
                        response_text = response.content

                    elif st.session_state.agent_type == "multi":
                        orchestrator = MultiAgentOrchestrator(llm=llm)
                        result = await asyncio.run(orchestrator.execute(
                            task=prompt,
                            session_id=st.session_state.session_id,
                            workflow=getattr(st.session_state, 'workflow', 'standard'),
                        ))
                        response_text = result["answer"]

                        # 显示工作流步骤
                        with st.expander("📋 执行步骤"):
                            for step in result.get("steps", []):
                                st.markdown(f"**{step['agent']}**: {step['action']}")

                    # 显示回复
                    st.markdown(response_text)

                    # 保存到历史
                    assistant_msg = {"role": "assistant", "content": response_text}
                    st.session_state.messages.append(assistant_msg)

                except Exception as e:
                    error_msg = f"❌ 错误: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                    })


# ============ RAG标签页 ============

with tab2:
    st.markdown('<div class="sub-header">RAG文档问答</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 上传文档")
        file_path = st.text_input("文档路径", "./test.pdf", help="本地文件路径")

        if st.button("添加文档", use_container_width=True):
            try:
                from backend.llm import LLMFactory
                from backend.rag import RAGPipeline

                llm = LLMFactory.create(st.session_state.llm_provider)
                rag = RAGPipeline()

                result = asyncio.run(rag.add_document(file_path))
                st.success(f"✅ 已添加 {result['chunks_added']} 个文档块")

            except FileNotFoundError:
                st.error("❌ 文件不存在")
            except Exception as e:
                st.error(f"❌ 错误: {str(e)}")

        st.markdown("---")
        st.markdown("### 📊 RAG统计")
        try:
            stats = rag.get_stats()
            st.json(stats)
        except:
            st.info("RAG系统未初始化")

    with col2:
        st.markdown("### 🔍 问答")

        rag_question = st.text_area("问题")

        if st.button("查询", use_container_width=True):
            if rag_question:
                try:
                    from backend.llm import LLMFactory
                    from backend.rag import RAGPipeline

                    llm = LLMFactory.create(st.session_state.llm_provider)
                    rag = RAGPipeline()

                    result = asyncio.run(rag.query(
                        question=rag_question,
                        llm=llm,
                        top_k=5,
                    ))

                    st.markdown("#### 📖 检索结果")
                    for i, source in enumerate(result.get("sources", []), 1):
                        with st.expander(f"来源 {i} (相关度: {source.get('score', 0):.2f})"):
                            st.markdown(source.get("content", "")[:500] + "...")
                            st.caption(f"元数据: {source.get('metadata', {})}")

                    st.markdown("---")
                    st.markdown("#### 💡 答案")
                    st.markdown(result.get("answer", "无法生成答案"))

                except Exception as e:
                    st.error(f"❌ 错误: {str(e)}")


# ============ 关于标签页 ============

with tab3:
    st.markdown('<div class="sub-header">关于本项目</div>', unsafe_allow_html=True)

    st.markdown("""
    ### 🎯 项目简介

    这是一个**Agent开发学习项目**，展示了现代AI Agent的核心技术。

    ### ✨ 核心功能

    | 功能 | 描述 |
    |------|------|
    | **多LLM支持** | OpenAI、Anthropic、Ollama、GLM、DeepSeek |
    | **工具调用** | 搜索、计算、文件操作 |
    | **记忆系统** | 短期对话 + 长期向量存储 |
    | **RAG检索** | 文档问答 |
    | **多Agent** | 协作完成复杂任务 |

    ### 🏗️ 技术架构

    - **框架**: LangChain + LangGraph
    - **向量库**: ChromaDB
    - **API**: FastAPI
    - **前端**: Streamlit

    ### 📚 学习资源

    - [项目文档](./docs/spec.md)
    - [设计文档](./docs/design.md)
    - [任务清单](./docs/task.md)
    - [UV使用指南](./docs/uv-guide.md)

    ### 📝 开发状态

    - ✅ LLM后端
    - ✅ 工具系统
    - ✅ 记忆系统
    - ✅ RAG系统
    - ✅ 单Agent
    - ✅ 多Agent
    - ✅ API服务
    - ✅ Streamlit前端

    ### 📄 许可证

    MIT License
    """)

    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #6b7280;'>
    Built with ❤️ for learning Agent Development
    </div>
    """, unsafe_allow_html=True)
