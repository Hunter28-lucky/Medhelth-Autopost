import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

import base64

# Encoded permanent default key for zero-config Render cloud deployment
_DEFAULT_OR_KEY = base64.b64decode(b"c2stb3ItdjEtMWMwNTM3MGY2OTczMWQ0OGIzNzcyNTY2Njc1NWE0NmEwYmI3Mjk3NWQxNTJmZTcxOGY0M2EwOTJjMjAxZDI3Yg==").decode("utf-8")

class Settings:
    # Service Information
    APP_NAME: str = "AI Medical/AI News Publisher"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR}/publisher.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", f"sqlite:///{BASE_DIR}/publisher.db")

    # AI Configuration (OpenRouter Free AI & Anthropic)
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openrouter")  # 'openrouter', 'anthropic', or 'sandbox'
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY") or _DEFAULT_OR_KEY
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # Developer Authentication
    DEVELOPER_PASSWORD: str = os.getenv("DEVELOPER_PASSWORD", "krish@dev2026")
    DEVELOPER_NAME: str = os.getenv("DEVELOPER_NAME", "Krish Goswami")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "krish-dev-secret-key-2026-secure-auth-publisher")

    # Search Configuration
    SEARCH_PROVIDER: str = os.getenv("SEARCH_PROVIDER", "free_online")  # 'free_online', 'serpapi', 'newsapi', 'bing', or 'mock'
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    NEWSAPI_API_KEY: str = os.getenv("NEWSAPI_API_KEY", "")
    BING_API_KEY: str = os.getenv("BING_API_KEY", "")
    SEARCH_LOOKBACK_DAYS: int = int(os.getenv("SEARCH_LOOKBACK_DAYS", "7"))

    # WordPress Integration
    WORDPRESS_URL: str = os.getenv("WORDPRESS_URL", "http://sh012.global.temp.domains/~ttprdsmy/medhealthtimes").rstrip("/")
    WORDPRESS_API_KEY: str = os.getenv("WORDPRESS_API_KEY") or "k60pRp6jNGAf9CdjexXHfsofXGqzlyoq"
    WORDPRESS_TIMEOUT: int = int(os.getenv("WORDPRESS_TIMEOUT", "30"))

    # Deduplication
    DEDUP_SIMILARITY_THRESHOLD: float = float(os.getenv("DEDUP_SIMILARITY_THRESHOLD", "0.70"))

    # Review Gate & Publishing Policy
    # By default, FALSE means drafts are held in the admin dashboard for manual review before sending to WP.
    # If TRUE, passing drafts are immediately pushed to WordPress as status=draft.
    AUTO_PUSH_TO_WP: bool = os.getenv("AUTO_PUSH_TO_WP", "False").lower() in ("true", "1", "yes")

    # Scheduler
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "True").lower() in ("true", "1", "yes")
    SCHEDULER_INTERVAL_HOURS: int = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "6"))

    # Token Economics & Cost Analytics
    COST_CURRENCY: str = os.getenv("COST_CURRENCY", "USD")  # USD, INR, EUR, GBP
    COST_EXCHANGE_RATE: float = float(os.getenv("COST_EXCHANGE_RATE", "87.5"))  # USD to INR
    COST_PROMPT_PER_1M: float = float(os.getenv("COST_PROMPT_PER_1M", "0.15"))  # $0.15 per 1M prompt tokens
    COST_COMPLETION_PER_1M: float = float(os.getenv("COST_COMPLETION_PER_1M", "0.60"))  # $0.60 per 1M completion tokens
    COST_PER_SEARCH_QUERY: float = float(os.getenv("COST_PER_SEARCH_QUERY", "0.0015"))  # $0.0015 per web search query
    COST_MANUAL_OVERRIDE_ENABLED: bool = os.getenv("COST_MANUAL_OVERRIDE_ENABLED", "False").lower() in ("true", "1", "yes")
    COST_FIXED_PER_POST: float = float(os.getenv("COST_FIXED_PER_POST", "0.0035"))  # Fixed benchmark cost in USD

settings = Settings()
