"""Tests for the session-scoped credential vault.

The headline property under test is isolation: the bug this vault replaced let
one visitor's keys apply to every other visitor.
"""
import pytest

from core.vault import CredentialVault, SessionExpired


@pytest.fixture
def vault():
    return CredentialVault(ttl_seconds=3600, max_sessions=10)


def test_sessions_are_isolated(vault):
    """One session must never observe another session's credentials."""
    a = vault.create_session()
    b = vault.create_session()

    vault.set_credentials(a, "twitter", {"bearer_token": "token-for-a"})

    assert vault.get_credentials(a, "twitter") == {"bearer_token": "token-for-a"}
    assert vault.get_credentials(b, "twitter") == {}
    assert vault.connected_providers(b) == []


def test_session_ids_are_unpredictable(vault):
    ids = {vault.create_session() for _ in range(50)}
    assert len(ids) == 50
    assert all(len(i) >= 32 for i in ids)


def test_unknown_session_raises(vault):
    with pytest.raises(SessionExpired):
        vault.get_credentials("not-a-session", "twitter")


def test_expired_session_raises():
    vault = CredentialVault(ttl_seconds=0)
    session = vault.create_session()
    with pytest.raises(SessionExpired):
        vault.get_credentials(session, "twitter")


def test_is_active_never_raises(vault):
    assert vault.is_active(None) is False
    assert vault.is_active("nope") is False
    assert vault.is_active(vault.create_session()) is True


def test_ensure_session_revives_dead_ids(vault):
    fresh = vault.ensure_session("garbage")
    assert vault.is_active(fresh)
    assert fresh != "garbage"

    assert vault.ensure_session(fresh) == fresh


def test_unknown_field_names_are_dropped(vault):
    """Only fields the provider actually declares are stored."""
    session = vault.create_session()
    vault.set_credentials(session, "twitter", {"bearer_token": "ok", "evil": "payload"})
    assert vault.get_credentials(session, "twitter") == {"bearer_token": "ok"}


def test_unknown_provider_rejected(vault):
    session = vault.create_session()
    with pytest.raises(ValueError):
        vault.set_credentials(session, "not-a-provider", {"x": "y"})


def test_empty_credentials_disconnect_provider(vault):
    session = vault.create_session()
    vault.set_credentials(session, "twitter", {"bearer_token": "abc"})
    assert vault.connected_providers(session) == ["twitter"]

    vault.set_credentials(session, "twitter", {"bearer_token": "   "})
    assert vault.connected_providers(session) == []


def test_masked_snapshot_hides_secrets(vault):
    session = vault.create_session()
    vault.set_credentials(session, "reddit", {
        "client_id": "abcdef123456",
        "client_secret": "supersecretvalue999",
        "user_agent": "episcopio/test",
    })
    snapshot = vault.masked_snapshot(session)["reddit"]

    assert "supersecretvalue999" not in str(snapshot)
    assert "abcdef123456" not in str(snapshot)
    # Non-secret fields stay readable so the UI can show them.
    assert snapshot["user_agent"] == "episcopio/test"


def test_destroy_forgets_everything(vault):
    session = vault.create_session()
    vault.set_credentials(session, "twitter", {"bearer_token": "abc"})
    vault.destroy(session)
    assert vault.is_active(session) is False


def test_vault_is_bounded():
    vault = CredentialVault(ttl_seconds=3600, max_sessions=5)
    sessions = [vault.create_session() for _ in range(20)]
    assert vault.session_count() <= 5
    # The most recent session always survives eviction.
    assert vault.is_active(sessions[-1])
