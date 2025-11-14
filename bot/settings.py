import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    LINKEDIN_BASE_URL: str = "https://www.linkedin.com"

    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "sqlite:///./storage/data.db")
    LOG_DIR: str = os.getenv("LOG_DIR", "storage/logs")
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() == "true"
    USER_DATA_DIR: str = os.getenv("USER_DATA_DIR", "/tmp/chrome-user-data")
    DELAY_TIME: int = int(os.getenv("DELAY_TIME", 5))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.95))
    MAX_STEPS_PER_APPLICATION: int = int(os.getenv("MAX_STEPS_PER_APPLICATION", 10))

    USER_INFORMATION: str = os.getenv("USER_INFORMATION")
    JOB_SEARCH_TIME_WINDOW: int = int(os.getenv("JOB_SEARCH_TIME_WINDOW", 24)) * 3600  # in hour
    WORK_TYPE: str = os.getenv("WORK_TYPE", "remote")
    KEYWORDS: str = os.getenv("KEYWORDS", "laravel,python,go")
    COUNTRIES: str = os.getenv("COUNTRIES")

    DEEPINFRA_EMBEDDING_API_URL: str = os.getenv(
        "DEEPINFRA_EMBEDDING_API_URL", "https://api.deepinfra.com/v1/inference/google/embeddinggemma-300m"
    )
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY")

    OPENROUTER_BASE_URL: str = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "openai:nvidia/nemotron-nano-12b-v2-vl:free")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")

    # AI
    AI_MAX_RETRIES: int = os.getenv("AI_MAX_RETRIES", 5)
    AI_BACKOFF_BASE: float = os.getenv("AI_BACKOFF_BASE", 0.5)


settings = Settings()
