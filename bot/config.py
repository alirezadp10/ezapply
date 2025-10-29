import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "sqlite:///./data.db")
    HEADLESS: bool = os.getenv("HEADLESS", "True").lower() == "true"
    USER_DATA_DIR: str = os.getenv("USER_DATA_DIR", "/tmp/chrome-user-data")
    DELAY_TIME: int = int(os.getenv("DELAY_TIME", 5))
    WAIT_WARN_AFTER: int = int(os.getenv("WAIT_WARN_AFTER", 10))
    TIMEOUT: int = int(os.getenv("TIMEOUT", 60))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", 0.95))
    MAX_STEPS_PER_APPLICATION: int = int(os.getenv("MAX_STEPS_PER_APPLICATION", 3))

    LINKEDIN_BASE_URL: str = "https://www.linkedin.com"
    LINKEDIN_USERNAME: str = os.getenv("LINKEDIN_USERNAME")
    LINKEDIN_PASSWORD: str = os.getenv("LINKEDIN_PASSWORD")

    USER_INFORMATION: str = os.getenv("USER_INFORMATION")
    JOB_SEARCH_TIME_WINDOW: int = int(os.getenv("JOB_SEARCH_TIME_WINDOW", 3600 * 6))
    WORK_TYPE: str = os.getenv("WORK_TYPE", "remote")
    KEYWORDS: str = os.getenv("KEYWORDS", "laravel,python,go")
    COUNTRIES: str = os.getenv("COUNTRIES")

    DEEPINFRA_API_URL: str = os.getenv("DEEPINFRA_API_URL", "https://api.deepinfra.com/v1/openai/chat/completions")
    DEEPINFRA_EMBEDDING_API_URL: str = os.getenv("DEEPINFRA_EMBEDDING_API_URL", "https://api.deepinfra.com/v1/inference/google/embeddinggemma-300m")
    DEEPINFRA_MODEL_NAME: str = os.getenv("DEEPINFRA_MODEL_NAME", "meta-llama/Meta-Llama-3-8B-Instruct")
    DEEPINFRA_API_KEY: str = os.getenv("DEEPINFRA_API_KEY")

settings = Settings()
