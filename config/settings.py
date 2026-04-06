import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

SHARED_CONFIG = {"extra": "ignore"}


def _get_db_url() -> str:
    """Resolve database URL. Checks WEBREACH_DATABASE_URL first, then
    falls back to Railway's DATABASE_URL if it points to PostgreSQL."""
    url = os.environ.get("WEBREACH_DATABASE_URL", "")
    if url:
        return url.replace("postgres://", "postgresql://", 1)

    railway_url = os.environ.get("DATABASE_URL", "")
    if railway_url and railway_url.startswith(("postgres", "postgresql")):
        return railway_url.replace("postgres://", "postgresql://", 1)

    return "sqlite:///data/outreach.db"


class GoogleSettings(BaseSettings):
    places_api_key: str = ""
    search_radius_meters: int = 5000
    max_results_per_query: int = 60

    model_config = {**SHARED_CONFIG, "env_prefix": "GOOGLE_"}


class SerpApiSettings(BaseSettings):
    key: str = ""

    model_config = {**SHARED_CONFIG, "env_prefix": "SERPAPI_"}


class LLMSettings(BaseSettings):
    provider: str = "groq"
    api_key: str = ""
    model: str = "llama-3.3-70b-versatile"
    base_url: str = "https://api.groq.com/openai/v1"
    max_tokens: int = 4096

    model_config = {**SHARED_CONFIG, "env_prefix": "LLM_"}


class RailwaySettings(BaseSettings):
    api_token: str = ""
    app_base_url: str = "http://localhost:8000"
    project_id: str = ""
    default_region: str = "europe-west"

    model_config = {**SHARED_CONFIG, "env_prefix": "RAILWAY_"}


class EmailSettings(BaseSettings):
    resend_api_key: str = ""
    from_email: str = "outreach@example.com"
    from_name: str = "James von Amplivo.net"

    model_config = {**SHARED_CONFIG, "env_prefix": "OUTREACH_"}


class TwilioSettings(BaseSettings):
    account_sid: str = ""
    auth_token: str = ""
    from_number: str = ""

    model_config = {**SHARED_CONFIG, "env_prefix": "TWILIO_"}


class RetellSettings(BaseSettings):
    api_key: str = ""
    webhook_secret: str = ""

    model_config = {**SHARED_CONFIG, "env_prefix": "RETELL_"}


class PipelineSettings(BaseSettings):
    batch_size: int = 10
    outreach_daily_limit: int = 50
    follow_up_delay_days: int = 3
    max_follow_ups: int = 2
    scan_cooldown_hours: int = 24
    verification_timeout_seconds: int = 10

    model_config = {**SHARED_CONFIG, "env_prefix": "PIPELINE_"}


class Settings(BaseSettings):
    db_url: str = Field(default_factory=_get_db_url)
    log_level: str = "INFO"
    base_dir: Path = Path(__file__).resolve().parent.parent

    google: GoogleSettings = Field(default_factory=GoogleSettings)
    serpapi: SerpApiSettings = Field(default_factory=SerpApiSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    railway: RailwaySettings = Field(default_factory=RailwaySettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    twilio: TwilioSettings = Field(default_factory=TwilioSettings)
    retell: RetellSettings = Field(default_factory=RetellSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    model_config = {"extra": "ignore"}


settings = Settings()
