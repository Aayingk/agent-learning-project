"""
配置管理模块
从环境变量加载配置，提供类型安全的配置访问
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration
    openai_api_key: str = ""
    openai_api_base: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-sonnet-20240229"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-4-flash"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    default_llm_provider: str = "openai"

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    # Streamlit Configuration
    streamlit_host: str = "localhost"
    streamlit_port: int = 8501

    # Storage Configuration
    chroma_persist_dir: str = "./data/chroma"
    chroma_collection_name: str = "agent_memory"
    session_ttl: int = 3600

    # Agent Configuration
    max_context_tokens: int = 4000
    memory_summary_threshold: int = 3000
    tool_timeout: int = 30
    max_tool_iterations: int = 5

    # RAG Configuration
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.7

    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"

    # Feature Flags
    enable_multi_agent: bool = True
    enable_rag: bool = True
    enable_long_term_memory: bool = True

    def get_llm_credentials(self, provider: str) -> dict:
        """获取指定LLM提供商的凭据"""
        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "base_url": self.openai_api_base,
                "model": self.openai_model,
            }
        elif provider == "anthropic":
            return {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            }
        elif provider == "ollama":
            return {
                "base_url": self.ollama_base_url,
                "model": self.ollama_model,
            }
        elif provider == "glm":
            return {
                "api_key": self.glm_api_key,
                "base_url": self.glm_base_url,
                "model": self.glm_model,
            }
        elif provider == "deepseek":
            return {
                "api_key": self.deepseek_api_key,
                "base_url": self.deepseek_base_url,
                "model": self.deepseek_model,
            }
        raise ValueError(f"Unknown LLM provider: {provider}")


# 全局配置实例
settings = Settings()
