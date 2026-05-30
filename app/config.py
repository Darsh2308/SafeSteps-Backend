from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    PROJECT_NAME: str = "Safe Steps AI Backend"
    API_V1_STR: str = ""
    SECRET_KEY: str = "supersecretjwtkeyforlocaldevelopmentsafesteps"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 11520  # 8 days
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "safesteps"

    # AI APIs
    GROQ_API_KEY: str = Field(default="")
    SARVAM_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")

    # LangSmith Observability
    LANGSMITH_TRACING: str = Field(default="false")
    LANGSMITH_API_KEY: str = Field(default="")
    LANGSMITH_PROJECT: str = Field(default="SafeSteps")
    LANGSMITH_ENDPOINT: str = Field(default="https://api.smith.langchain.com")

    # SMS is handled by the app via Android SmsManager (user's own SIM — no gateway needed)

    # Anthropic (reserved for future Claude integration)
    ANTHROPIC_API_KEY: str = Field(default="")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
