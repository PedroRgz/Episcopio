"""Tests for the credentials → run → data pipeline."""
import pytest

from core.datastore import DataStore
from core.runs import ERROR, PARTIAL, SUCCESS, RunRegistry
from core.vault import CredentialVault
from ingesta.base import ConnectorResult
from orchestrator import pipeline as pl


@pytest.fixture
def wired(monkeypatch):
    """A pipeline wired to fresh, isolated stores."""
    vault = CredentialVault(ttl_seconds=3600)
    registry = RunRegistry()
    store = DataStore()

    monkeypatch.setattr(pl, "vault", vault)
    monkeypatch.setattr(pl, "run_registry", registry)
    monkeypatch.setattr(pl, "data_store", store)
    return vault, registry, store


def _official_rows():
    # 20 flat days then a spike, so the incremento rule has something to fire on.
    rows = [
        {"fecha": f"2025-01-{d:02d}", "cve_ent": "31", "casos": 10, "defunciones": 1}
        for d in range(1, 21)
    ]
    rows.append({"fecha": "2025-01-21", "cve_ent": "31", "casos": 90, "defunciones": 4})
    return rows


def _run(vault, registry, session):
    run = registry.create(session, pl.plan_steps(vault.connected_providers(session)))
    return pl.execute_run(session, run)


def test_public_only_run_produces_data(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()

    monkeypatch.setitem(
        pl.CONNECTORS, "dge",
        lambda creds: ConnectorResult.success("dge", 21, "ok", _official_rows()),
    )
    monkeypatch.setitem(
        pl.CONNECTORS, "conacyt",
        lambda creds: ConnectorResult.skipped("conacyt", "sin configurar"),
    )

    run = _run(vault, registry, session)

    assert run.status == SUCCESS
    dataset = store.get(session)
    assert dataset is not None
    assert dataset.serie_oficial
    assert dataset.kpis["31"]["casos_totales"] == 290
    assert "dge" in dataset.fuentes


def test_credentialed_source_receives_its_own_credentials(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()
    vault.set_credentials(session, "twitter", {"bearer_token": "tok-123456789"})

    seen = {}

    def fake_twitter(creds):
        seen.update(creds)
        return ConnectorResult.success(
            "twitter", 1, "ok",
            [{"fecha": "2025-01-21", "texto": "brote", "fuente": "twitter", "sentimiento": -0.5}],
        )

    monkeypatch.setitem(pl.CONNECTORS, "twitter", fake_twitter)
    monkeypatch.setitem(pl.CONNECTORS, "dge", lambda c: ConnectorResult.skipped("dge", "off"))
    monkeypatch.setitem(pl.CONNECTORS, "conacyt", lambda c: ConnectorResult.skipped("conacyt", "off"))
    # Skip the live validation call in this unit test.
    monkeypatch.setattr(pl, "get_provider", _passthrough_provider(pl.get_provider))

    _run(vault, registry, session)
    assert seen == {"bearer_token": "tok-123456789"}


def _passthrough_provider(original):
    """Wrap get_provider so validate() always succeeds, without touching the network."""
    class _Stub:
        def __init__(self, inner):
            self._inner = inner

        def __getattr__(self, item):
            return getattr(self._inner, item)

        def validate(self, creds):
            from ingesta.providers import ValidationResult
            return ValidationResult(True, "ok", "stub")

    def wrapper(provider_id):
        inner = original(provider_id)
        return _Stub(inner) if inner else None

    return wrapper


def test_one_dead_source_does_not_abort_the_run(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()

    monkeypatch.setitem(
        pl.CONNECTORS, "dge",
        lambda c: ConnectorResult.success("dge", 21, "ok", _official_rows()),
    )
    monkeypatch.setitem(
        pl.CONNECTORS, "conacyt",
        lambda c: ConnectorResult.unreachable("conacyt", "timeout"),
    )

    run = _run(vault, registry, session)

    assert run.status == PARTIAL
    assert store.get(session) is not None  # the healthy source still landed


def test_connector_exception_becomes_an_error_row(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()

    def explode(creds):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(pl.CONNECTORS, "dge", explode)
    monkeypatch.setitem(pl.CONNECTORS, "conacyt", lambda c: ConnectorResult.skipped("conacyt", "off"))

    run = _run(vault, registry, session)

    assert run.status == ERROR
    dge_step = run.step("dge")
    assert dge_step.status == "error"
    # The raw exception text must not surface to the user.
    assert "kaboom" not in dge_step.message


def test_run_with_no_usable_source_fails_loudly(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()

    for pid in ("dge", "conacyt"):
        monkeypatch.setitem(pl.CONNECTORS, pid, lambda c: ConnectorResult.skipped(pid, "off"))

    run = _run(vault, registry, session)

    assert run.status == ERROR
    assert store.get(session) is None


def test_alerts_fire_on_a_real_spike(wired, monkeypatch):
    vault, registry, store = wired
    session = vault.create_session()

    monkeypatch.setitem(
        pl.CONNECTORS, "dge",
        lambda c: ConnectorResult.success("dge", 21, "ok", _official_rows()),
    )
    monkeypatch.setitem(pl.CONNECTORS, "conacyt", lambda c: ConnectorResult.skipped("conacyt", "off"))

    _run(vault, registry, session)
    alertas = store.get(session).alertas
    assert any(a["tipo"] == "incremento_subito" for a in alertas)


def test_plan_skips_providers_without_credentials(wired):
    vault, _, _ = wired
    session = vault.create_session()
    keys = {s.key for s in pl.plan_steps(vault.connected_providers(session))}

    assert "dge" in keys          # public source always runs
    assert "twitter" not in keys  # no credentials supplied
    assert pl.ANALYTICS_STEP in keys


def test_runs_are_scoped_to_their_session(wired):
    _, registry, _ = wired
    run_a = registry.create("session-a", [])
    assert registry.get("session-b", run_a.id) is None
    assert registry.get("session-a", run_a.id) is run_a
