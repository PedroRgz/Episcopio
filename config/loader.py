"""Configuration loader for Episcopio.

Security notes
--------------
This loader is deliberately strict about the difference between a local
development run and a real deployment:

* ``EP_ENVIRONMENT`` selects the profile (``development`` by default).
* In ``production`` the loader refuses to start with placeholder secrets
  (``changeme``-style passwords, the sample JWT secret) or with a CORS
  configuration that would allow credentialed wildcard requests.

Failing fast at boot is much safer than silently serving traffic with the
values that ship in ``secrets.sample.yaml``.
"""
from pydantic import BaseModel, Field, ConfigDict
from pydantic_settings import BaseSettings
import yaml
import os
from typing import List, Optional


# Values that ship in the repository as placeholders. They must never reach a
# production deployment.
PLACEHOLDER_VALUES = {
    "changeme",
    "changeme_jwt_secret",
    "<YOUR_POSTGRES_PASSWORD>",
    "<CHANGE_THIS_SECRET_KEY>",
    "",
}

MIN_JWT_SECRET_LENGTH = 32


class ConfigurationError(RuntimeError):
    """Raised when the effective configuration is unsafe to run."""


class AppSettings(BaseModel):
    """Application settings from settings.yaml."""
    name: str = "Episcopio"
    version: str = "1.0.0-mvp"
    timezone: str = "America/Merida"
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}


class AlertSettings(BaseModel):
    """Alert configuration."""
    alert_windows_days: int = 14
    cooldown_hours: int = 24
    min_cases_threshold: int = 5
    delta_threshold: float = 0.2
    zscore_threshold: float = 2.0
    sentiment_negative_threshold: float = -0.2


class ApiSettings(BaseModel):
    """API behaviour settings from settings.yaml."""
    title: str = "Episcopio API"
    description: str = "API de lectura para monitoreo epidemiológico"
    version: str = "1.0"
    rate_limit_per_minute: int = 60
    write_rate_limit_per_minute: int = 10


class SessionSettings(BaseModel):
    """Lifetime of a browser session's server-side credential vault."""
    credential_ttl_minutes: int = 60
    max_sessions: int = 500


class Secrets(BaseSettings):
    """Secrets loaded from environment variables or secrets.local.yaml."""

    # Deployment profile
    environment: str = Field(default="development")

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
    security_cors_allowed_origins: str = Field(
        default="http://localhost:8050,http://localhost:8000"
    )

    model_config = ConfigDict(
        env_prefix="EP_",
        env_file=".env",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    def cors_origins(self) -> List[str]:
        """Parse the configured CORS origins into a clean list.

        An empty entry is dropped rather than turned into ``""``, which
        Starlette would otherwise treat as a literal (never-matching) origin.
        """
        return [o.strip() for o in self.security_cors_allowed_origins.split(",") if o.strip()]

    def has_placeholder_secrets(self) -> List[str]:
        """Return the names of secrets still holding placeholder values."""
        offenders = []
        if self.postgres_password in PLACEHOLDER_VALUES:
            offenders.append("EP_POSTGRES_PASSWORD")
        if (
            self.security_jwt_secret in PLACEHOLDER_VALUES
            or len(self.security_jwt_secret) < MIN_JWT_SECRET_LENGTH
        ):
            offenders.append("EP_SECURITY_JWT_SECRET")
        return offenders

    def validate_for_environment(self) -> None:
        """Fail fast when a production deployment is misconfigured.

        Outside production the same problems are reported by the caller as
        warnings so local development stays frictionless.
        """
        if not self.is_production:
            return

        problems = []

        offenders = self.has_placeholder_secrets()
        if offenders:
            problems.append(
                "these secrets still hold placeholder/insecure values: "
                + ", ".join(offenders)
            )

        origins = self.cors_origins()
        if "*" in origins:
            # CORSMiddleware is mounted with allow_credentials=True; a wildcard
            # there means any site can drive authenticated requests.
            problems.append(
                "EP_SECURITY_CORS_ALLOWED_ORIGINS may not be '*' because "
                "credentialed CORS is enabled; list explicit origins"
            )
        if not origins:
            problems.append("EP_SECURITY_CORS_ALLOWED_ORIGINS must list at least one origin")
        insecure = [o for o in origins if o.startswith("http://") and "localhost" not in o and "127.0.0.1" not in o]
        if insecure:
            problems.append(
                "plain-http CORS origins are not allowed in production: " + ", ".join(insecure)
            )

        if problems:
            raise ConfigurationError(
                "Refusing to start in production with an unsafe configuration:\n  - "
                + "\n  - ".join(problems)
            )


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


def _strip_placeholders(values: dict) -> dict:
    """Drop `<YOUR_...>` template values so they never look like real secrets."""
    return {
        k: v
        for k, v in values.items()
        if not (isinstance(v, str) and v.startswith("<") and v.endswith(">"))
    }


def load_config():
    """Load configuration from YAML files and environment variables.

    Returns:
        Tuple of ``(AppSettings, AlertSettings, Secrets, ApiSettings, SessionSettings)``.

    Raises:
        ConfigurationError: when running in production with unsafe settings.
    """
    settings_path = os.path.join(os.path.dirname(__file__), "settings.yaml")
    with open(settings_path, "r", encoding="utf-8") as f:
        static_cfg = yaml.safe_load(f) or {}

    app_settings = AppSettings(**static_cfg.get("app", {}))
    alert_settings = AlertSettings(**static_cfg.get("alerts", {}))
    api_settings = ApiSettings(**static_cfg.get("api", {}))
    session_settings = SessionSettings(**static_cfg.get("session", {}))

    # Load secrets.local.yaml if it exists (environment variables win).
    secrets_path = os.path.join(os.path.dirname(__file__), "secrets.local.yaml")
    secrets_yaml = {}
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            secrets_yaml = yaml.safe_load(f) or {}

    flattened = _strip_placeholders(flatten_yaml_keys(secrets_yaml))
    secrets = Secrets(**flattened)

    # EP_ENVIRONMENT overrides the value declared in settings.yaml.
    app_settings.environment = secrets.environment or app_settings.environment
    secrets.environment = app_settings.environment

    secrets.validate_for_environment()

    return app_settings, alert_settings, secrets, api_settings, session_settings


if __name__ == "__main__":
    app, alerts, secrets, api_cfg, session_cfg = load_config()
    print(f"App: {app.name} v{app.version} ({app.environment})")
    print(f"Timezone: {app.timezone}")
    print(f"Database: {secrets.postgres_database}")
    print(f"CORS origins: {secrets.cors_origins()}")
    weak = secrets.has_placeholder_secrets()
    print(f"Placeholder secrets: {weak or 'none'}")
