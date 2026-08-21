"""The pipeline that runs when a user supplies their keys.

This is the "paste your keys and it just works" path:

1. Read the session's credentials from the server-side vault.
2. Validate each one against its live upstream API.
3. Ingest from every source that validated, plus the public sources.
4. Normalise, compute KPIs, evaluate alerts.
5. Publish the result into the session's dataset.

The whole thing runs on a background thread and reports progress into the run
registry, so the UI can show live per-source status instead of freezing.

Failure is isolated per source: one dead API degrades that source to an error
row, it does not abort the run. A run that produced no data at all finishes as
``error`` — never as a silent success.
"""
from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from analytics.alertas import evaluar_alertas
from analytics.kpis import recalcular_kpis, serie_por_fecha
from core.datastore import Dataset, data_store
from core.runs import ERROR, PARTIAL, RUNNING, SUCCESS, PipelineRun, RunStep, run_registry
from core.vault import SessionExpired, vault
from etl.normaliza import normalizar_dge, normalizar_menciones
from ingesta.base import ConnectorResult
from ingesta.oficial import fetch_conacyt_covid, fetch_dge, fetch_inegi
from ingesta.providers import OFICIAL, PROVIDERS, get_provider
from ingesta.social import (
    fetch_facebook,
    fetch_instagram,
    fetch_news,
    fetch_reddit,
    fetch_twitter,
)

logger = logging.getLogger(__name__)

# Bounded so a run cannot spawn one thread per provider without limit.
MAX_PARALLEL_SOURCES = 4
ANALYTICS_STEP = "analytics"

# provider id -> connector. Every connector takes the credential dict for that
# provider and returns a ConnectorResult.
CONNECTORS: Dict[str, Callable[[Optional[Dict[str, str]]], ConnectorResult]] = {
    "dge": fetch_dge,
    "conacyt": fetch_conacyt_covid,
    "inegi": fetch_inegi,
    "twitter": fetch_twitter,
    "reddit": fetch_reddit,
    "newsapi": fetch_news,
    "facebook": fetch_facebook,
    "instagram": fetch_instagram,
}


def plan_steps(connected: List[str]) -> List[RunStep]:
    """Build the step list for a run.

    Public sources always participate; credentialed sources join only when the
    session actually supplied keys for them.
    """
    steps: List[RunStep] = []
    for provider in PROVIDERS:
        if provider.needs_credentials and provider.id not in connected:
            continue
        if provider.id not in CONNECTORS:
            continue
        steps.append(RunStep(key=provider.id, label=provider.label))
    steps.append(RunStep(key=ANALYTICS_STEP, label="KPIs y alertas"))
    return steps


def _run_source(provider_id: str, credentials: Dict[str, str]) -> ConnectorResult:
    """Validate then ingest one source, converting any surprise into a result.

    A connector raising is a bug, not a reason to take down the whole run, so
    unexpected exceptions become an ``error`` row with a generic message. The
    detail goes to the log, never to the user, because exception text can carry
    fragments of a request that included a credential.
    """
    provider = get_provider(provider_id)
    if provider is None:
        return ConnectorResult.error(provider_id, "Proveedor desconocido.")

    if provider.needs_credentials:
        validation = provider.validate(credentials)
        if not validation.ok:
            status = "error" if validation.status in ("invalid", "missing") else "unreachable"
            return ConnectorResult(
                source=provider_id, ok=False, status=status, message=validation.message
            )

    connector = CONNECTORS.get(provider_id)
    if connector is None:
        return ConnectorResult.skipped(provider_id, "Sin conector implementado.")

    try:
        return connector(credentials)
    except Exception:  # noqa: BLE001 - deliberately broad; see docstring
        logger.exception("Conector %s falló inesperadamente", provider_id)
        return ConnectorResult.error(provider_id, "Error inesperado en el conector.")


def execute_run(session_id: str, run: PipelineRun) -> PipelineRun:
    """Run the pipeline synchronously and publish the result.

    Exposed separately from :func:`start_run` so tests can drive it without
    threads.
    """
    run_registry.mark_running(run)

    try:
        credentials = vault.all_credentials(session_id)
    except SessionExpired:
        run_registry.finish(run, ERROR, "La sesión expiró; vuelva a ingresar sus credenciales.")
        return run

    source_steps = [s for s in run.steps if s.key != ANALYTICS_STEP]
    for step in source_steps:
        run_registry.update_step(run, step.key, status=RUNNING, message="En progreso…")

    results: Dict[str, ConnectorResult] = {}
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_SOURCES) as pool:
        futures = {
            pool.submit(_run_source, step.key, credentials.get(step.key, {})): step.key
            for step in source_steps
        }
        for future in as_completed(futures):
            provider_id = futures[future]
            try:
                result = future.result()
            except Exception:  # noqa: BLE001 - a crashed worker must not abort the run
                logger.exception("Ejecución de %s falló", provider_id)
                result = ConnectorResult.error(provider_id, "Error inesperado en el conector.")
            results[provider_id] = result
            run_registry.update_step(
                run,
                provider_id,
                status=SUCCESS if result.ok else result.status,
                message=result.message,
                records=result.records,
            )

    # -- assemble -------------------------------------------------------
    run_registry.update_step(run, ANALYTICS_STEP, status=RUNNING, message="Calculando…")

    raw_oficial: List[Dict[str, Any]] = []
    raw_social: List[Dict[str, Any]] = []
    for provider_id, result in results.items():
        if not result.ok:
            continue
        provider = get_provider(provider_id)
        if provider and provider.kind == OFICIAL:
            raw_oficial.extend(result.data)
        else:
            raw_social.extend(result.data)

    normalizado = normalizar_dge(raw_oficial)
    serie_oficial = serie_por_fecha(normalizado["serie"])
    social = normalizar_menciones(raw_social)
    serie_social = social["menciones"]

    kpi_result = recalcular_kpis(normalizado["serie"])
    alert_result = evaluar_alertas(serie_oficial, serie_social)

    fuentes_ok = sorted(pid for pid, r in results.items() if r.ok)
    n_kpis = kpi_result["kpis_updated"]
    n_alertas = alert_result["alertas_activas"]
    run_registry.update_step(
        run,
        ANALYTICS_STEP,
        status=SUCCESS,
        message=(
            f"{n_kpis} conjunto{'s' if n_kpis != 1 else ''} de KPIs, "
            f"{n_alertas} alerta{'s' if n_alertas != 1 else ''} activa{'s' if n_alertas != 1 else ''}."
        ),
        records=n_alertas,
    )

    if fuentes_ok:
        data_store.put(
            session_id,
            Dataset(
                serie_oficial=serie_oficial,
                serie_social=serie_social,
                kpis=kpi_result["kpis"],
                alertas=alert_result["alertas"],
                fuentes=fuentes_ok,
            ),
        )

    # -- classify the run ------------------------------------------------
    failed = [pid for pid, r in results.items() if r.status in ("error", "unreachable")]
    if not fuentes_ok:
        run_registry.finish(
            run,
            ERROR,
            "Ninguna fuente entregó datos. Revise sus credenciales y la configuración de fuentes.",
        )
    elif failed:
        run_registry.finish(
            run,
            PARTIAL,
            f"{len(fuentes_ok)} fuente(s) actualizadas, {len(failed)} con problemas.",
        )
    else:
        run_registry.finish(
            run,
            SUCCESS,
            f"{len(fuentes_ok)} fuente(s) actualizadas correctamente.",
        )
    return run


def start_run(session_id: str) -> PipelineRun:
    """Kick off a pipeline run in the background and return it immediately.

    Raises:
        SessionExpired: if the session id is unknown or has timed out.
    """
    connected = vault.connected_providers(session_id)  # raises SessionExpired
    run = run_registry.create(session_id, plan_steps(connected))

    thread = threading.Thread(
        target=_run_guarded,
        args=(session_id, run),
        name=f"episcopio-pipeline-{run.id}",
        daemon=True,
    )
    thread.start()
    return run


def _run_guarded(session_id: str, run: PipelineRun) -> None:
    """Thread entry point: a crash here must still close out the run."""
    try:
        execute_run(session_id, run)
    except Exception:  # noqa: BLE001 - background thread of last resort
        logger.exception("Run %s falló", run.id)
        run_registry.finish(run, ERROR, "El proceso falló de forma inesperada.")
