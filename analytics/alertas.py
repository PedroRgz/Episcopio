"""Alert evaluation module.

Rules are declared in ``analytics/reglas/alertas.yaml`` and evaluated against
the normalized series produced by the pipeline. Two families are supported:

* ``incremento`` — the latest official value exceeds its trailing mean by a
  configured margin.
* ``social`` — mention volume spikes (z-score) while sentiment stays negative.
"""
from __future__ import annotations

import logging
import os
import statistics
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Resolve relative to this file: the previous relative path only worked when
# the process happened to be started from the repository root.
REGLAS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reglas", "alertas.yaml")

DEFAULT_RULES: List[Dict[str, Any]] = [
    {
        "id": "a1",
        "nombre": "Incremento súbito oficial",
        "tipo": "incremento",
        "serie": "casos",
        "ventana_ref": 14,
        "umbral_delta": 0.2,
        "min_casos": 5,
    },
    {
        "id": "a2",
        "nombre": "Pico social con sentimiento negativo",
        "tipo": "social",
        "serie": "menciones",
        "zscore": 2.0,
        "sentimiento_max": -0.2,
    },
]


def cargar_reglas() -> List[Dict[str, Any]]:
    """Load alert rules, falling back to the built-in defaults."""
    try:
        with open(REGLAS_PATH, "r", encoding="utf-8") as f:
            reglas = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("No se encontró %s; usando reglas por defecto", REGLAS_PATH)
        return list(DEFAULT_RULES)
    except yaml.YAMLError as exc:
        logger.error("Archivo de reglas inválido (%s); usando reglas por defecto", exc.__class__.__name__)
        return list(DEFAULT_RULES)

    if isinstance(reglas, dict):
        reglas = reglas.get("reglas", [])
    if not isinstance(reglas, list) or not reglas:
        return list(DEFAULT_RULES)
    return [r for r in reglas if isinstance(r, dict)]


def evaluar_regla_incremento(
    regla: Dict[str, Any], datos: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Fire when the latest value beats its trailing mean by ``umbral_delta``.

    Args:
        regla: Rule configuration.
        datos: Daily official series, oldest first.

    Returns:
        Evidence dict when the rule fires, otherwise ``None``.
    """
    campo = regla.get("serie", "casos")
    ventana = int(regla.get("ventana_ref", 14))
    umbral = float(regla.get("umbral_delta", 0.2))
    min_casos = int(regla.get("min_casos", 5))

    valores = [float(d.get(campo, 0) or 0) for d in datos if campo in d]
    # Need the current point plus at least two reference points for a mean.
    if len(valores) < 3:
        return None

    actual = valores[-1]
    referencia = valores[max(0, len(valores) - 1 - ventana): -1]
    if not referencia:
        return None

    promedio = statistics.fmean(referencia)
    if actual < min_casos or promedio <= 0:
        return None

    delta = (actual - promedio) / promedio
    if delta < umbral:
        return None

    return {
        "delta_porcentaje": round(delta * 100, 1),
        "valor_actual": actual,
        "promedio_referencia": round(promedio, 2),
        "ventana_dias": ventana,
        "fecha": datos[-1].get("fecha"),
    }


def evaluar_regla_social(
    regla: Dict[str, Any], datos: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Fire on a mention-volume spike coinciding with negative sentiment."""
    umbral_z = float(regla.get("zscore", 2.0))
    sentimiento_max = float(regla.get("sentimiento_max", -0.2))

    conteos = [float(d.get("conteo", 0) or 0) for d in datos]
    if len(conteos) < 4:
        return None

    actual = conteos[-1]
    referencia = conteos[:-1]
    media = statistics.fmean(referencia)
    try:
        desviacion = statistics.stdev(referencia)
    except statistics.StatisticsError:
        return None
    if desviacion == 0:
        return None

    zscore = (actual - media) / desviacion
    sentimiento = float(datos[-1].get("sentimiento", 0) or 0)

    if zscore < umbral_z or sentimiento > sentimiento_max:
        return None

    return {
        "zscore": round(zscore, 2),
        "menciones_actual": actual,
        "menciones_promedio": round(media, 2),
        "sentimiento": sentimiento,
        "fecha": datos[-1].get("fecha"),
    }


def crear_alerta(tipo: str, regla: Dict[str, Any], evidencia: Dict[str, Any], alert_id: int) -> Dict[str, Any]:
    """Build an alert record from a fired rule."""
    return {
        "id": alert_id,
        "tipo": tipo,
        "regla": regla.get("id", "desconocida"),
        "nombre": regla.get("nombre", tipo),
        "estado": "activa",
        "evidencia": evidencia,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def evaluar_alertas(
    serie_oficial: List[Dict[str, Any]] | None = None,
    serie_social: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """Evaluate every configured rule against the supplied series.

    Args:
        serie_oficial: Daily official series (``fecha``, ``casos``, ``defunciones``).
        serie_social: Daily social series (``fecha``, ``conteo``, ``sentimiento``).

    Returns:
        ``{"alertas": [...], "alertas_evaluadas": int, "alertas_activas": int}``.
    """
    serie_oficial = serie_oficial or []
    serie_social = serie_social or []

    alertas: List[Dict[str, Any]] = []
    reglas = cargar_reglas()

    for regla in reglas:
        tipo = regla.get("tipo") or ("social" if regla.get("serie") == "menciones" else "incremento")
        if tipo == "social":
            evidencia = evaluar_regla_social(regla, serie_social)
            etiqueta = "pico_social"
        else:
            evidencia = evaluar_regla_incremento(regla, serie_oficial)
            etiqueta = "incremento_subito"

        if evidencia:
            alertas.append(crear_alerta(etiqueta, regla, evidencia, len(alertas) + 1))

    return {
        "status": "success",
        "alertas": alertas,
        "alertas_evaluadas": len(reglas),
        "alertas_activas": len(alertas),
    }
