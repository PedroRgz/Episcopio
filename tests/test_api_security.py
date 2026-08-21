"""Tests for API hardening: sessions, headers, validation and rate limits."""
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.security import RateLimitMiddleware
from config.loader import ConfigurationError, Secrets


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The limiter is process-global by design, so clear it between tests."""
    RateLimitMiddleware.reset_all()
    yield
    RateLimitMiddleware.reset_all()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session(client):
    return client.post("/api/v1/session").json()["session_id"]


def _headers(session_id):
    return {"X-Episcopio-Session": session_id}


# -- security headers ------------------------------------------------------

def test_security_headers_present(client):
    r = client.get("/api/v1/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_session_responses_are_not_cacheable(client, session):
    r = client.get("/api/v1/session/credentials", headers=_headers(session))
    assert r.headers["Cache-Control"] == "no-store"


# -- session scoping -------------------------------------------------------

def test_credentials_require_a_session(client):
    assert client.get("/api/v1/session/credentials").status_code == 401
    assert client.post("/api/v1/pipeline/run").status_code == 401


def test_forged_session_id_is_rejected(client):
    r = client.get("/api/v1/session/credentials", headers=_headers("a" * 43))
    assert r.status_code == 401


def test_credentials_are_never_echoed_back(client, session):
    secret = "super-secret-bearer-token-value"
    r = client.post(
        "/api/v1/session/credentials",
        headers=_headers(session),
        json={"provider": "twitter", "credentials": {"bearer_token": secret}},
    )
    assert r.status_code == 200
    assert secret not in r.text

    listed = client.get("/api/v1/session/credentials", headers=_headers(session))
    assert secret not in listed.text
    assert listed.json()["connected"] == ["twitter"]


def test_one_session_cannot_read_another(client):
    a = client.post("/api/v1/session").json()["session_id"]
    b = client.post("/api/v1/session").json()["session_id"]

    client.post(
        "/api/v1/session/credentials",
        headers=_headers(a),
        json={"provider": "twitter", "credentials": {"bearer_token": "token-a-123456"}},
    )
    assert client.get("/api/v1/session/credentials", headers=_headers(b)).json()["connected"] == []


def test_destroying_a_session_invalidates_it(client, session):
    assert client.delete("/api/v1/session", headers=_headers(session)).status_code == 200
    assert client.get("/api/v1/session/credentials", headers=_headers(session)).status_code == 401


def test_unknown_provider_is_rejected(client, session):
    r = client.post(
        "/api/v1/session/credentials",
        headers=_headers(session),
        json={"provider": "../../etc/passwd", "credentials": {}},
    )
    assert r.status_code == 404


def test_oversized_credential_is_rejected(client, session):
    r = client.post(
        "/api/v1/session/credentials",
        headers=_headers(session),
        json={"provider": "twitter", "credentials": {"bearer_token": "x" * 5000}},
    )
    assert r.status_code == 422


# -- input validation ------------------------------------------------------

@pytest.mark.parametrize(
    "payload",
    [
        {"cve_ent": "XX", "sintomas_observacion": "fiebre", "nivel_actividad": "alto"},
        {"cve_ent": "31", "sintomas_observacion": "fiebre", "nivel_actividad": "extremo"},
        {"cve_ent": "31", "sintomas_observacion": "", "nivel_actividad": "alto"},
        {"cve_ent": "3100", "sintomas_observacion": "fiebre", "nivel_actividad": "alto"},
    ],
)
def test_survey_rejects_bad_input(client, payload):
    assert client.post("/api/v1/survey", json=payload).status_code == 422


def test_survey_accepts_valid_input(client):
    r = client.post(
        "/api/v1/survey",
        json={"cve_ent": "31", "sintomas_observacion": "fiebre alta", "nivel_actividad": "alto"},
    )
    assert r.status_code == 200
    # The endpoint must not claim to have stored anything it did not store.
    assert r.json()["stored"] is False


def test_kpi_rejects_malformed_entity(client):
    assert client.post("/api/v1/kpi", json={"entidad": "abc"}).status_code == 422


# -- reads without a session ----------------------------------------------

def test_reads_without_a_session_report_sample_mode(client):
    body = client.get("/api/v1/timeseries").json()
    assert body["is_sample"] is True
    assert body["serie_oficial"] == []


# -- rate limiting ---------------------------------------------------------

def test_write_endpoints_are_rate_limited(client):
    payload = {"cve_ent": "31", "sintomas_observacion": "fiebre", "nivel_actividad": "alto"}
    statuses = [client.post("/api/v1/survey", json=payload).status_code for _ in range(30)]
    assert 429 in statuses


def test_health_is_exempt_from_rate_limiting(client):
    assert all(client.get("/api/v1/health").status_code == 200 for _ in range(80))


# -- configuration hardening ----------------------------------------------

def test_production_rejects_placeholder_secrets():
    secrets = Secrets(environment="production")
    with pytest.raises(ConfigurationError) as exc:
        secrets.validate_for_environment()
    assert "EP_SECURITY_JWT_SECRET" in str(exc.value)


def test_production_rejects_wildcard_cors():
    secrets = Secrets(
        environment="production",
        postgres_password="a-real-password",
        security_jwt_secret="x" * 40,
        security_cors_allowed_origins="*",
    )
    with pytest.raises(ConfigurationError) as exc:
        secrets.validate_for_environment()
    assert "CORS" in str(exc.value)


def test_production_rejects_plain_http_origins():
    secrets = Secrets(
        environment="production",
        postgres_password="a-real-password",
        security_jwt_secret="x" * 40,
        security_cors_allowed_origins="http://episcopio.mx",
    )
    with pytest.raises(ConfigurationError):
        secrets.validate_for_environment()


def test_valid_production_config_passes():
    secrets = Secrets(
        environment="production",
        postgres_password="a-real-password",
        security_jwt_secret="x" * 40,
        security_cors_allowed_origins="https://episcopio.mx, https://www.episcopio.mx",
    )
    secrets.validate_for_environment()
    assert secrets.cors_origins() == ["https://episcopio.mx", "https://www.episcopio.mx"]


def test_development_tolerates_placeholder_secrets():
    Secrets(environment="development").validate_for_environment()


def test_cors_origins_drops_empty_entries():
    secrets = Secrets(security_cors_allowed_origins="https://a.mx,,  ,https://b.mx")
    assert secrets.cors_origins() == ["https://a.mx", "https://b.mx"]


def test_dashboard_traffic_is_not_metered_as_api_writes(client):
    """Dash posts to /_dash-update-component on every interaction.

    Metering those against the API's write budget rate-limited the UI against
    itself after ~10 clicks, so only /api/v1 paths are in scope.
    """
    statuses = {client.post("/_dash-update-component", json={}).status_code for _ in range(40)}
    assert 429 not in statuses
