"""Tests for the provider registry and credential validation."""
import requests

from ingesta.providers import PROVIDERS, get_provider, mask, public_providers


def test_mask_never_leaks_short_secrets():
    assert mask("abc123") == "••••••"
    assert "abc123" not in mask("abc123")


def test_mask_keeps_long_secrets_recognisable_but_redacted():
    masked = mask("AAAAAAAAAAAAAAAAAAAAsecret")
    assert "AAAAAAAAAAAAAAAAAAAAsecret" not in masked
    assert masked.startswith("AAA")


def test_mask_handles_empty():
    assert mask(None) == ""
    assert mask("") == ""


def test_unknown_provider_returns_none():
    assert get_provider("does-not-exist") is None
    assert get_provider("") is None


def test_public_providers_need_no_credentials():
    for provider in public_providers():
        assert provider.validate({}).ok


def test_missing_required_field_is_reported():
    twitter = get_provider("twitter")
    result = twitter.validate({})
    assert not result.ok
    assert result.status == "missing"


def test_optional_field_is_not_required():
    reddit = get_provider("reddit")
    # user_agent is optional; leaving it out must not read as "missing".
    assert reddit.missing_fields({"client_id": "a", "client_secret": "b"}) == []


def test_validation_survives_network_failure(monkeypatch):
    """A dead upstream must degrade to 'unreachable', not raise."""
    def boom(*args, **kwargs):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(requests, "get", boom)
    result = get_provider("twitter").validate({"bearer_token": "x" * 20})
    assert not result.ok
    assert result.status == "unreachable"


def test_validation_maps_401_to_invalid(monkeypatch):
    class FakeResponse:
        status_code = 401
        text = ""

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResponse())
    result = get_provider("twitter").validate({"bearer_token": "x" * 20})
    assert not result.ok
    assert result.status == "invalid"


def test_validation_error_message_never_contains_the_secret(monkeypatch):
    secret = "super-secret-bearer-token"

    def boom(*args, **kwargs):
        raise requests.ConnectionError(f"failed calling with {secret}")

    monkeypatch.setattr(requests, "get", boom)
    result = get_provider("twitter").validate({"bearer_token": secret})
    assert secret not in result.message


def test_every_provider_declares_docs_and_kind():
    for provider in PROVIDERS:
        assert provider.doc_url.startswith("https://")
        assert provider.kind in ("oficial", "social")
        assert provider.label
