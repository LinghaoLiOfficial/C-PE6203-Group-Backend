from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="FastAPI Application", alias="APP_NAME")
    database_url: str = Field(
        default="postgresql+psycopg://llh@localhost:5432/scaffold_fastapi",
        alias="DATABASE_URL",
    )
    backend_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="BACKEND_CORS_ORIGINS",
    )
    llm_provider: str = Field(default="groq", alias="LLM_PROVIDER")
    llm_base_url: str | None = Field(default="https://api.groq.com/openai/v1", alias="LLM_BASE_URL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_model: str | None = Field(default="llama-3.3-70b-versatile", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    llm_stream_read_timeout_seconds: float = Field(
        default=300.0, alias="LLM_STREAM_READ_TIMEOUT_SECONDS"
    )
    llm_thinking: bool = Field(default=False, alias="LLM_THINKING")
    llm_use_response_format: bool = Field(default=True, alias="LLM_USE_RESPONSE_FORMAT")
    llm_max_output_tokens: int = Field(
        default=8192, ge=256, le=32768, alias="LLM_MAX_OUTPUT_TOKENS"
    )
    llm_structured_max_retries: int = Field(default=2, ge=0, alias="LLM_STRUCTURED_MAX_RETRIES")
    queue_worker_concurrency: int = Field(default=1, ge=1, alias="QUEUE_WORKER_CONCURRENCY")
    queue_poll_interval_seconds: float = Field(default=2.0, alias="QUEUE_POLL_INTERVAL_SECONDS")
    queue_stale_after_seconds: int = Field(default=900, alias="QUEUE_STALE_AFTER_SECONDS")
    queue_worker_heartbeat_timeout_seconds: int = Field(
        default=15, alias="QUEUE_WORKER_HEARTBEAT_TIMEOUT_SECONDS"
    )
    queue_max_attempts: int = Field(default=3, alias="QUEUE_MAX_ATTEMPTS")
    queue_worker_id: str | None = Field(default=None, alias="QUEUE_WORKER_ID")
    auth_secret_key: str | None = Field(default=None, alias="AUTH_SECRET_KEY")
    auth_refresh_secret_key: str | None = Field(default=None, alias="AUTH_REFRESH_SECRET_KEY")
    auth_access_token_expire_minutes: int = Field(
        default=30, alias="AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    auth_refresh_token_expire_days: int = Field(default=7, alias="AUTH_REFRESH_TOKEN_EXPIRE_DAYS")
    email_verification_expire_minutes: int = Field(
        default=10, alias="EMAIL_VERIFICATION_EXPIRE_MINUTES"
    )
    email_verification_resend_seconds: int = Field(
        default=60, alias="EMAIL_VERIFICATION_RESEND_SECONDS"
    )
    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str | None = Field(default=None, alias="SMTP_USERNAME")
    smtp_code: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_CODE", "SMTP_PASSWORD"),
    )
    smtp_sender_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SMTP_SENDER_EMAIL", "SMTP_FROM_EMAIL"),
    )
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    bootstrap_admin_email: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_username: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_USERNAME")
    bootstrap_admin_password: str | None = Field(default=None, alias="BOOTSTRAP_ADMIN_PASSWORD")
    upload_dir: str = Field(default="storage", alias="UPLOAD_DIR")
    match_score_threshold: float = Field(default=0.73, alias="MATCH_SCORE_THRESHOLD")
    daily_rewrite_limit: int = Field(default=10, alias="DAILY_REWRITE_LIMIT")
    max_resume_upload_bytes: int = Field(default=3 * 1024 * 1024, alias="MAX_RESUME_UPLOAD_BYTES")
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL_NAME"
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    adzuna_app_id: str | None = Field(default=None, alias="ADZUNA_APP_ID")
    adzuna_app_key: str | None = Field(default=None, alias="ADZUNA_APP_KEY")
    arbeidnow_api_url: str = Field(
        default="https://www.arbeitnow.com/api/job-board-api", alias="ARBEITNOW_API_URL"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        if self.llm_provider.lower() == "groq":
            return bool(self.llm_api_key and self.llm_model)
        return bool(self.llm_base_url and self.llm_api_key and self.llm_model)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_sender_email)

    @property
    def smtp_login_username(self) -> str | None:
        return self.smtp_username or self.smtp_sender_email

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
