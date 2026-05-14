# UV 使用指南

本项目使用 [uv](https://github.com/astral-sh/uv) 作为包管理器。uv 是一个极速的 Python 包管理器，由 Rust 编写。

## 环境已配置

- Python 版本：3.14.4
- uv 版本：0.11.13
- 虚拟环境：`.venv/`
- 镜像源：清华源

## 常用命令

### 激活虚拟环境

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 运行 Python 代码

```bash
# 直接运行（不需要激活环境）
uv run python script.py

# 或者先激活环境再运行
source .venv/bin/activate
python script.py
```

### 安装新依赖

```bash
# 安装单个包
uv add package_name

# 安装开发依赖
uv add --dev package_name

# 从 requirements.txt 安装
uv pip install -r requirements.txt
```

### 同步依赖

```bash
# 安装所有依赖
uv sync

# 安装所有可选依赖
uv sync --all-extras

# 只安装核心依赖
uv sync --extra core --extra llm
```

### 运行应用

```bash
# 运行 FastAPI 服务
uv run uvicorn backend.api.main:app --reload

# 运行 Streamlit
uv run streamlit run frontend/app.py

# 运行测试
uv run pytest
```

### 代码格式化

```bash
# 使用 Black 格式化代码
uv run black .

# 使用 Ruff 检查代码
uv run ruff check .

# 使用 Ruff 自动修复
uv run ruff check --fix .
```

## pyproject.toml 依赖组

本项目使用依赖组管理不同场景的依赖：

| 依赖组 | 说明 | 命令 |
|--------|------|------|
| core | 核心框架（LangChain等） | `uv sync --extra core` |
| llm | LLM提供商 | `uv sync --extra llm` |
| vectorstore | 向量存储 | `uv sync --extra vectorstore` |
| api | API框架 | `uv sync --extra api` |
| frontend | 前端 | `uv sync --extra frontend` |
| dev | 开发工具 | `uv sync --extra dev` |
| all | 全部依赖 | `uv sync --all-extras` |

## 与 pip 对比

| 操作 | pip | uv |
|------|-----|-----|
| 创建虚拟环境 | `python -m venv .venv` | `uv venv` |
| 安装依赖 | `pip install -r requirements.txt` | `uv sync` |
| 添加包 | `pip install package` | `uv add package` |
| 运行脚本 | `python script.py` | `uv run python script.py` |

uv 的优势：
- ⚡️ 极快（比 pip 快 10-100 倍）
- 🔒 一致性锁文件
- 📦 统一的项目配置
- 🚀 更好的依赖解析
