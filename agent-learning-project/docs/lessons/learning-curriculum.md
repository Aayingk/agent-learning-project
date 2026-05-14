# Agent 开发学习大纲

> 从零开始，系统学习 Agent 开发和大模型基础知识

**📊 [查看学习进度](./progress.md)**

---

## 学习路径图

```
补充材料
├── L0: 设计模式专题 ✅

第一阶段: 基础知识 (3-5天) [▓▓▓▓▓▓▓▓▓▓▓▓] 100% (5/5) ✅
├── L1: 大语言模型基础 ✅
├── L2: Agent 核心概念 ✅
├── L3: Prompt Engineering ✅
├── L4: 数据模型与验证 📅
└── L5: 异步编程基础 📅

第二阶段: LLM 调用 (2-3天)
├── L6: LLM API 调用
├── L7: 多模型抽象设计
├── L8: 错误处理与重试
└── L9: Function Calling

第三阶段: 工具系统 (2天)
├── L10: 工具定义与注册
├── L11: 工具参数解析
└── L12: 自定义工具开发

第四阶段: 记忆系统 (2天)
├── L13: 短期记忆设计
├── L14: 向量数据库基础
└── L15: 长期记忆实现

第五阶段: Agent 模式 (3天)
├── L16: ReAct 模式
├── L17: 对话 Agent
└── L18: 多 Agent 协作

第六阶段: RAG 系统 (2天)
├── L19: 文档分割与嵌入
├── L20: 向量检索
└── L21: RAG 完整流程

第七阶段: 实战项目 (3天)
├── L22: API 服务开发
├── L23: 前端界面开发
└── L24: 完整项目部署
```

---

## 补充材料

### L0: 设计模式专题 ✅

**学习目标**: 理解项目中使用的设计模式

**核心模式**:
- 工厂模式 (Factory Pattern)
- 单例模式 (Singleton Pattern)
- 装饰器模式 (Decorator Pattern)
- 模板方法模式 (Template Method Pattern)
- 管道模式 (Pipeline Pattern)
- 策略模式 (Strategy Pattern)
- 状态模式 (State Pattern)

**实战代码位置**: `backend/llm/factory.py`, `backend/tools/registry.py`, `backend/rag/pipeline.py`

---

## 第一阶段: 基础知识

### L1: 大语言模型基础 ✅

**学习目标**: 理解 LLM 是什么，如何工作

**核心概念**:
- 什么是大语言模型 (LLM)
- Token 与 Tokenization
- Context Window (上下文窗口)
- Temperature (温度参数)
- Top-p / Top-k 采样
- System Prompt / User Prompt

**实战代码位置**: `backend/llm/`

**练习**:
1. 调用 DeepSeek API 完成简单问答
2. 理解 Token 计费方式
3. 测试不同温度参数的效果

---

### L2: Agent 核心概念 ✅

**学习目标**: 理解什么是 Agent，为什么需要 Agent

**核心概念**:
- Agent vs Chatbot
- ReAct 模式 (Reasoning + Acting)
- Tool Use (工具使用)
- Memory (记忆)
- Planning (规划)

**实战代码位置**: `backend/agents/`

**练习**:
1. 阅读 ReAct 论文摘要
2. 理解 Thought-Action-Observation 循环

---

### L3: Prompt Engineering ✅

**学习目标**: 学会编写有效的 Prompt

**核心技巧**:
- 明确的角色设定
- 具体的任务描述
- 示例驱动 (Few-shot)
- 思维链 (Chain of Thought)
- 结构化输出要求

**实战代码位置**: 各 Agent 类中的 system_prompt

**练习**:
1. 编写一个计算器 prompt
2. 编写一个搜索助手 prompt

---

### L4: 数据模型与验证

**学习目标**: 使用 Pydantic 进行数据验证

**核心概念**:
- Pydantic BaseModel
- Field 验证
- 类型注解
- JSON 序列化/反序列化

**实战代码位置**: `backend/llm/models.py`, `backend/api/schemas.py`

**练习**:
1. 定义一个 Message 模型
2. 实现 JSON Schema 生成

---

### L5: 异步编程基础

**学习目标**: 理解 Python 异步编程

**核心概念**:
- async/await
- asyncio
- 异步上下文管理器
- 并发 vs 并行

**实战代码位置**: 所有 LLM 客户端的 chat 方法

**练习**:
1. 编写简单的异步函数
2. 理解为什么 LLM 调用需要异步

---

## 学习方式

1. **概念讲解**: 理论知识
2. **代码阅读**: 在项目中找到对应实现
3. **动手实践**: 运行代码，观察效果
4. **扩展练习**: 添加新功能

---

## 推荐资源

- **论文**: ReAct: Synergizing Reasoning and Acting in Language Models
- **文档**: LangChain, LangGraph 官方文档
- **实践**: 本项目源码
- **视频**: 吴恩达 AI 课程

---

## 学习检验

完成学习后，你应能够:
- ✅ 解释 LLM 工作原理
- ✅ 设计一个简单的 Agent
- ✅ 集成新的 LLM API
- ✅ 开发自定义工具
- ✅ 实现 RAG 系统
- ✅ 理解多 Agent 协作模式
