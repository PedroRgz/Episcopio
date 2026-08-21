"""KPI calculation module.

KPIs are computed from a normalized official series (the output of
:func:`etl.normaliza.normalizar_dge`), so the same code path serves the API,
the dashboard and the scheduler.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# A case is counted as "active" while it falls inside this trailing window.
ACTIVE_WINDOW_DAYS = 14
# Window used for the "vs. previous period" deltas shown on the KPI cards.
COMPARISON_WINDOW_DAYS = 7


def _pct_change(current: float, previous: float) -> float:
    """Percentage change, with a defined answer when the baseline is zero.

    A jump from 0 to something is reported as +100% rather than as a division
    error or a misleading 0%.
    """
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _to_date(fecha: str) -> Optional[datetime]:
    try:
        return datetime.strptime(fecha[:10], "%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def calcular_kpis(
    serie: List[Dict[str, Any]], cve_ent: Optional[str] = None
) -> Dict[str, Any]:
    """Compute headline KPIs from a normalized official series.

    Args:
        serie: Records with ``fecha``, ``cve_ent``, ``casos`` and ``defunciones``.
        cve_ent: Restrict the calculation to one entity; ``None`` means national.

    Returns:
        Totals, active cases and week-over-week deltas. Every field is present
        even for an empty series, so callers never need a null check.
    """
    if cve_ent:
        serie = [r for r in serie if r.get("cve_ent") == cve_ent]

    empty = {
        "cve_ent": cve_ent or "00",
        "casos_totales": 0,
        "casos_activos": 0,
        "defunciones": 0,
        "variacion_casos": 0.0,
        "variacion_activos": 0.0,
        "variacion_defunciones": 0.0,
        "fecha_actualizacion": None,
        "puntos": 0,
    }
    if not serie:
        return empty

    dated = [(d, r) for r in serie if (d := _to_date(str(r.get("fecha", ""))))]
    if not dated:
        return empty

    latest = max(d for d, _ in dated)
    active_cutoff = latest.toordinal() - ACTIVE_WINDOW_DAYS
    current_cutoff = latest.toordinal() - COMPARISON_WINDOW_DAYS
    previous_cutoff = latest.toordinal() - (COMPARISON_WINDOW_DAYS * 2)

    casos_totales = defunciones_totales = casos_activos = 0
    casos_actual = casos_previo = 0
    defunciones_actual = defunciones_previo = 0
    activos_previos = 0

    for d, row in dated:
        casos = int(row.get("casos", 0) or 0)
        muertes = int(row.get("defunciones", 0) or 0)
        ordinal = d.toordinal()

        casos_totales += casos
        defunciones_totales += muertes

        if ordinal > active_cutoff:
            casos_activos += casos
        elif ordinal > active_cutoff - ACTIVE_WINDOW_DAYS:
            activos_previos += casos

        if ordinal > current_cutoff:
            casos_actual += casos
            defunciones_actual += muertes
        elif ordinal > previous_cutoff:
            casos_previo += casos
            defunciones_previo += muertes

    return {
        "cve_ent": cve_ent or "00",
        "casos_totales": casos_totales,
        "casos_activos": casos_activos,
        "defunciones": defunciones_totales,
        "variacion_casos": _pct_change(casos_actual, casos_previo),
        "variacion_activos": _pct_change(casos_activos, activos_previos),
        "variacion_defunciones": _pct_change(defunciones_actual, defunciones_previo),
        "fecha_actualizacion": latest.strftime("%Y-%m-%d"),
        "puntos": len(dated),
    }


def calcular_kpis_entidad(
    serie: List[Dict[str, Any]], cve_ent: str, fecha_ini: str = "", fecha_fin: str = ""
) -> Dict[str, Any]:
    """KPIs for one entity, optionally restricted to a date range."""
    filtered = serie
    if fecha_ini:
        filtered = [r for r in filtered if str(r.get("fecha", "")) >= fecha_ini]
    if fecha_fin:
        filtered = [r for r in filtered if str(r.get("fecha", "")) <= fecha_fin]
    return calcular_kpis(filtered, cve_ent)


def serie_por_fecha(serie: List[Dict[str, Any]], cve_ent: Optional[str] = None) -> List[Dict[str, Any]]:
    """Collapse a per-entity series into one national/entity daily series."""
    if cve_ent:
        serie = [r for r in serie if r.get("cve_ent") == cve_ent]

    por_fecha: Dict[str, Dict[str, int]] = defaultdict(lambda: {"casos": 0, "defunciones": 0})
    for row in serie:
        fecha = str(row.get("fecha", ""))[:10]
        if not fecha:
            continue
        por_fecha[fecha]["casos"] += int(row.get("casos", 0) or 0)
        por_fecha[fecha]["defunciones"] += int(row.get("defunciones", 0) or 0)

    return [
        {"fecha": fecha, "casos": v["casos"], "defunciones": v["defunciones"]}
        for fecha, v in sorted(por_fecha.items())
    ]


def recalcular_kpis(serie: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Recalculate KPIs for every entity present in the series."""
    serie = serie or []
    entidades = sorted({str(r.get("cve_ent", "00")) for r in serie})
    kpis = {ent: calcular_kpis(serie, ent) for ent in entidades}
    kpis["00"] = calcular_kpis(serie)  # national aggregate
    return {
        "status": "success",
        "kpis_updated": len(kpis),
        "kpis": kpis,
        "calculado_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
