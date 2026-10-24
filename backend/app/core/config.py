"""Application settings, read from environment variables or a .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Agentic Code Review Framework"

    # API protection. If empty, the API is open (fine for local testing only).
    api_key: str = ""

    # JWT Authentication
    jwt_secret_key: str = "codesentinel-enterprise-jwt-super-secret-key-2026"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    jwt_refresh_token_expire_days: int = 7

    # LLM (NVIDIA NIM API; default: nvidia/nemotron-3.5-lightning-30b-a3b)
    llm_enabled: bool = True
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_api_key: str = ""
    nvidia_api_key: str = ""
    llm_model: str = "nvidia/nemotron-3.5-lightning-30b-a3b"
    llm_timeout: float = 120.0
    llm_temperature: float = 0.1
    llm_concurrency: int = 4
    max_file_chars: int = 60000

    # GitHub
    github_token: str = ""
    github_webhook_secret: str = ""
    github_api_url: str = "https://api.github.com"
    bot_branch_prefix: str = "ai-review/"

    # Rules an automated revision must satisfy before it can be submitted
    min_resolution_ratio: float = 1.0
    max_new_issues: int = 0
    max_fix_retries: int = 2
    generate_unit_tests: bool = True

    # Advanced Analysis & Agents
    enable_secrets_scanner: bool = True
    enable_cwe_mapping: bool = True
    enable_performance_agent: bool = True
    enable_architecture_agent: bool = True
    enable_test_coverage_agent: bool = True

    # Self-verification: threshold = base + risk_weight * (risk / 100)
    verify_base_threshold: float = 0.5
    verify_risk_weight: float = 0.3

    @property
    def effective_llm_api_key(self) -> str:
        import os
        return self.llm_api_key or self.nvidia_api_key or os.getenv("NVIDIA_API_KEY", "") or os.getenv("LLM_API_KEY", "")

    @property
    def llm_ready(self) -> bool:
        return self.llm_enabled and bool(self.effective_llm_api_key)


def get_settings() -> Settings:
    import sys
    if not hasattr(sys, "_codesentinel_settings"):
        sys._codesentinel_settings = Settings()
    return sys._codesentinel_settings

