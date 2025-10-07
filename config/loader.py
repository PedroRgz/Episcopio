"""Configuration loader for Episcopio."""
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import yaml
import os
from typing import Optional


class AppSettings(BaseModel):
    """Application settings from settings.yaml."""
    name: str = "Episcopio"
    version: str = "1.0.0-mvp"
    timezone: str = "America/Merida"


class AlertSettings(BaseModel):
    """Alert configuration."""
    alert_windows_days: int = 14
    cooldown_hours: int = 24
    min_cases_threshold: int = 5
    delta_threshold: float = 0.2
    zscore_threshold: float = 2.0
    sentiment_negative_threshold: float = -0.2


class Secrets(BaseSettings):
    """Secrets loaded from environment variables or secrets.local.yaml."""
    
    # PostgreSQL
    postgres_user: str = Field(default="episcopio")
    postgres_password: str = Field(default="changeme")
    postgres_host: str = Field(default="db")
    postgres_port: int = Field(default=5432)
    postgres_database: str = Field(default="episcopio")
    
    # Redis
    redis_url: str = Field(default="redis://redis:6379/0")
    
    # APIs
    apis_inegi_token: Optional[str] = None
    apis_twitter_bearer_token: Optional[str] = None
    apis_facebook_app_id: Optional[str] = None
    apis_facebook_app_secret: Optional[str] = None
    apis_facebook_access_token: Optional[str] = None
    apis_instagram_app_id: Optional[str] = None
    apis_instagram_app_secret: Optional[str] = None
    apis_instagram_access_token: Optional[str] = None
    apis_reddit_client_id: Optional[str] = None
    apis_reddit_client_secret: Optional[str] = None
    apis_reddit_user_agent: str = Field(default="episcopio/1.0")
    apis_newsapi_key: Optional[str] = None
    
    # Security
    security_jwt_secret: str = Field(default="changeme_jwt_secret")
    security_cors_allowed_origins: str = Field(default="http://localhost:8050,http://localhost:8000")

    class Config:
        env_prefix = "EP_"
        env_file = ".env"


def flatten_yaml_keys(d: dict, prefix: str = "") -> dict:
    """Flatten nested YAML keys to Pydantic format."""
    out = {}
    for k, v in (d or {}).items():
        key = (prefix + "_" + k) if prefix else k
        if isinstance(v, dict):
            out.update(flatten_yaml_keys(v, key))
        else:
            out[key.replace(".", "_")] = v
    return out


def load_config():
    """Load configuration from YAML files and environment variables."""
    # Load settings.yaml
    settings_path = os.path.join(os.path.dirname(__file__), "settings.yaml")
    with open(settings_path, "r", encoding="utf-8") as f:
        static_cfg = yaml.safe_load(f)
    
    app_settings = AppSettings(**static_cfg.get("app", {}))
    alert_settings = AlertSettings(**static_cfg.get("alerts", {}))
    
    # Load secrets.local.yaml if it exists
    secrets_path = os.path.join(os.path.dirname(__file__), "secrets.local.yaml")
    secrets_yaml = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            secrets_yaml = yaml.safe_load(f) or {}
    
    # Flatten and load secrets (environment variables take precedence)
    flattened = flatten_yaml_keys(secrets_yaml)
    secrets = Secrets(**flattened)
    
    return app_settings, alert_settings, secrets


if __name__ == "__main__":
    # Test configuration loading
    app, alerts, secrets = load_config()
    print(f"App: {app.name} v{app.version}")
    print(f"Timezone: {app.timezone}")
    print(f"Database: {secrets.postgres_database}")
