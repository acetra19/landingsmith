from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class GoogleSettings(BaseSettings):
    places_api_key: str = ""
    search_radius_meters: int = 5000
    max_results_per_query: int = 60

    model_config = {"env_prefix": "GOOGLE_"}


class SerpApiSettings(BaseSettings):
    key: str = ""

    model_config = {"env_prefix": "SERPAPI_"}


class OpenAISettings(BaseSettings):
    api_key: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096

    model_config = {"env_prefix": "OPENAI_"}


class RailwaySettings(BaseSettings):
    api_token: str = ""
    default_region: str = "europe-west"

    model_config = {"env_prefix": "RAILWAY_"}


class EmailSettings(BaseSettings):
    resend_api_key: str = ""
    from_email: str = "outreach@example.com"
    from_name: str = "WebReach"

    model_config = {"env_prefix": "OUTREACH_"}


class PipelineSettings(BaseSettings):
    batch_size: int = 10
    outreach_daily_limit: int = 50
    follow_up_delay_days: int = 3
    max_follow_ups: int = 2
    scan_cooldown_hours: int = 24
    verification_timeout_seconds: int = 10

    model_config = {"env_prefix": "PIPELINE_"}


class Settings(BaseSettings):
    database_url: str = "sqlite:///data/outreach.db"
    log_level: str = "INFO"
    base_dir: Path = Path(__file__).resolve().parent.parent

    google: GoogleSettings = Field(default_factory=GoogleSettings)
    serpapi: SerpApiSettings = Field(default_factory=SerpApiSettings)
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    railway: RailwaySettings = Field(default_factory=RailwaySettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
