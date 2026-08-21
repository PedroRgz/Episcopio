"""Official data ingestion connectors.

These connectors talk to public Mexican health-data sources. Two rules apply
throughout:

* A connector that cannot run reports ``skipped``/``error`` — it never returns
  a fabricated success. The dashboard shows exactly which sources contributed.
* Bulk-download URLs change often, so they are configurable via environment
  variables rather than hard-coded and silently broken.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from ingesta.base import ConnectorResult
from ingesta.providers import USER_AGENT

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30
# Guard against a source handing us a multi-gigabyte file and exhausting RAM.
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024

# Bulk endpoints are deployment-specific; configure them to enable ingest.
DGE_DATA_URL = os.getenv("EP_DGE_DATA_URL", "").strip()
CONACYT_DATA_URL = os.getenv("EP_CONACYT_DATA_URL", "").strip()

INEGI_POPULATION_INDICATOR = "1002000001"


def _download_json(url: str, source: str) -> ConnectorResult:
    """Stream a JSON document with a hard size ceiling."""
    with requests.get(
        url, timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}, stream=True
    ) as r:
        if r.status_code != 200:
            return ConnectorResult.unreachable(
                source, f"La fuente respondió con estado {r.status_code}."
            )

        declared = r.headers.get("Content-Length")
        if declared and declared.isdigit() and int(declared) > MAX_DOWNLOAD_BYTES:
            return ConnectorResult.error(source, "El archivo excede el tamaño máximo permitido.")

        payload = bytearray()
        for chunk in r.iter_content(chunk_size=65536):
            payload.extend(chunk)
            if len(payload) > MAX_DOWNLOAD_BYTES:
                return ConnectorResult.error(
                    source, "El archivo excede el tamaño máximo permitido."
                )

    try:
        import json

        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return ConnectorResult.error(source, "La fuente no devolvió JSON válido.")

    rows = data if isinstance(data, list) else data.get("data", [])
    if not isinstance(rows, list):
        rows = []
    return ConnectorResult.success(
        source, len(rows), f"{len(rows)} registros descargados.", rows
    )


def fetch_dge(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Fetch open data from the Dirección General de Epidemiología.

    Set ``EP_DGE_DATA_URL`` to the JSON export you want ingested. Without it the
    connector reports ``skipped`` rather than pretending to have run.
    """
    source = "dge"
    if not DGE_DATA_URL:
        return ConnectorResult.skipped(
            source,
            "Configure EP_DGE_DATA_URL con el export de datos abiertos de la DGE.",
        )
    try:
        return _download_json(DGE_DATA_URL, source)
    except requests.Timeout:
        return ConnectorResult.unreachable(source, "Tiempo de espera agotado.")
    except requests.RequestException as exc:
        logger.warning("Ingesta DGE falló: %s", type(exc).__name__)
        return ConnectorResult.unreachable(source, "No fue posible contactar la fuente.")


def fetch_conacyt_covid(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Fetch COVID-19 data from the CONAHCYT open-data export."""
    source = "conacyt"
    if not CONACYT_DATA_URL:
        return ConnectorResult.skipped(
            source,
            "Configure EP_CONACYT_DATA_URL con el export público de CONAHCYT.",
        )
    try:
        return _download_json(CONACYT_DATA_URL, source)
    except requests.Timeout:
        return ConnectorResult.unreachable(source, "Tiempo de espera agotado.")
    except requests.RequestException as exc:
        logger.warning("Ingesta CONAHCYT falló: %s", type(exc).__name__)
        return ConnectorResult.unreachable(source, "No fue posible contactar la fuente.")


def fetch_inegi(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Fetch population indicators from INEGI, used for per-100k rates.

    Args:
        credentials: ``{"token": "..."}`` as supplied by the user.
    """
    source = "inegi"
    token = (credentials or {}).get("token", "").strip()
    if not token:
        return ConnectorResult.skipped(source, "Sin token de INEGI; se omiten tasas por 100 mil.")

    url = (
        "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/"
        f"INDICATOR/{INEGI_POPULATION_INDICATOR}/es/0700/false/BISE/2.0/"
        f"{requests.utils.quote(token, safe='')}"
    )
    try:
        r = requests.get(
            url,
            params={"type": "json"},
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.Timeout:
        return ConnectorResult.unreachable(source, "Tiempo de espera agotado.")
    except requests.RequestException as exc:
        logger.warning("Ingesta INEGI falló: %s", type(exc).__name__)
        return ConnectorResult.unreachable(source, "No fue posible contactar la API de INEGI.")

    if r.status_code in (401, 403):
        return ConnectorResult.error(source, "Token de INEGI rechazado.")
    if r.status_code != 200:
        return ConnectorResult.unreachable(source, f"INEGI respondió con estado {r.status_code}.")

    try:
        payload = r.json()
    except ValueError:
        return ConnectorResult.error(source, "INEGI no devolvió JSON válido.")

    series = payload.get("Series") or []
    observations: List[Dict[str, Any]] = []
    for serie in series:
        for obs in serie.get("OBSERVATIONS") or []:
            observations.append(
                {
                    "periodo": obs.get("TIME_PERIOD"),
                    "valor": obs.get("OBS_VALUE"),
                    "indicador": serie.get("INDICADOR", INEGI_POPULATION_INDICATOR),
                }
            )

    return ConnectorResult.success(
        source,
        len(observations),
        f"{len(observations)} observaciones demográficas obtenidas.",
        observations,
    )


def fetch_datos_abiertos_ssa(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Fetch SSA open data. Shares the DGE export configuration."""
    source = "ssa"
    if not DGE_DATA_URL:
        return ConnectorResult.skipped(source, "Configure EP_DGE_DATA_URL para habilitar SSA.")
    return fetch_dge(credentials)


def verificar_fuentes() -> List[Dict[str, Any]]:
    """Check reachability of the public official sources.

    Uses ``HEAD`` so the check stays cheap, and reports the failure mode rather
    than claiming every source is available.
    """
    checks = [
        ("DGE", "https://www.gob.mx/salud/documentos/datos-abiertos-152127"),
        ("INEGI", "https://www.inegi.org.mx/servicios/api_indicadores.html"),
        ("CONAHCYT", "https://datos.covid-19.conacyt.mx"),
    ]

    fuentes = []
    for nombre, url in checks:
        estado = "no disponible"
        try:
            r = requests.head(
                url, timeout=10, allow_redirects=True, headers={"User-Agent": USER_AGENT}
            )
            estado = "disponible" if r.status_code < 400 else f"error {r.status_code}"
        except requests.RequestException:
            estado = "inalcanzable"
        fuentes.append(
            {
                "nombre": nombre,
                "url": url,
                "estado": estado,
                "verificado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        )
    return fuentes
