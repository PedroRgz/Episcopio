"""ETL normalization functions."""
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List
import logging
import re

logger = logging.getLogger(__name__)


def normalizar_dge(rows: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """Normalize raw official rows into Episcopio's canonical shape.

    Args:
        rows: Raw records as returned by an official connector. Records that
            cannot be normalized (bad dates, deaths exceeding cases) are
            dropped and counted rather than silently corrupting the series.

    Returns:
        ``{"filas_normalizadas": int, "filas_descartadas": int, "serie": [...]}``
        where each series entry is ``{fecha, cve_ent, casos, defunciones, semana_iso}``.
    """
    rows = rows or []
    serie: List[Dict[str, Any]] = []
    descartadas = 0

    for row in rows:
        if not isinstance(row, dict):
            descartadas += 1
            continue

        fecha = estandarizar_fecha(str(row.get("fecha") or row.get("FECHA") or ""))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
            descartadas += 1
            continue

        casos = _as_int(row.get("casos", row.get("CASOS")))
        defunciones = _as_int(row.get("defunciones", row.get("DEFUNCIONES")))
        if not validar_casos_defunciones(casos, defunciones):
            descartadas += 1
            continue

        serie.append(
            {
                "fecha": fecha,
                "cve_ent": normalizar_cve_ent(row.get("cve_ent", row.get("ENTIDAD_RES", "0"))),
                "casos": casos,
                "defunciones": defunciones,
                "semana_iso": calcular_semana_iso(fecha),
            }
        )

    serie.sort(key=lambda r: (r["fecha"], r["cve_ent"]))
    return {
        "filas_normalizadas": len(serie),
        "filas_descartadas": descartadas,
        "serie": serie,
    }


def _as_int(value: Any) -> int:
    """Coerce a raw field to a non-negative int, defaulting to 0."""
    try:
        return max(0, int(float(value)))
    except (TypeError, ValueError):
        return 0


def normalizar_menciones(menciones: List[Dict[str, Any]] | None) -> Dict[str, Any]:
    """Aggregate raw social mentions into a daily count/sentiment series.

    Args:
        menciones: Records shaped by the social connectors, each with
            ``fecha``, ``texto``, ``fuente`` and ``sentimiento``.

    Returns:
        ``{"menciones": [{"fecha", "conteo", "sentimiento"}], "por_fuente": {...}}``
        sorted by date, with sentiment averaged per day.
    """
    menciones = menciones or []
    por_dia: Dict[str, List[float]] = defaultdict(list)
    por_fuente: Dict[str, int] = defaultdict(int)

    for m in menciones:
        if not isinstance(m, dict):
            continue
        fecha = estandarizar_fecha(str(m.get("fecha", "")))
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
            continue
        try:
            sentimiento = float(m.get("sentimiento", 0.0))
        except (TypeError, ValueError):
            sentimiento = 0.0
        # Clamp so a malformed upstream value cannot skew the chart's axis.
        por_dia[fecha].append(max(-1.0, min(1.0, sentimiento)))
        por_fuente[str(m.get("fuente", "desconocida"))] += 1

    serie = [
        {
            "fecha": fecha,
            "conteo": len(valores),
            "sentimiento": round(sum(valores) / len(valores), 3),
        }
        for fecha, valores in sorted(por_dia.items())
    ]
    return {"menciones": serie, "por_fuente": dict(por_fuente)}


def estandarizar_fecha(fecha: str) -> str:
    """
    Standardize date to ISO-8601 format.
    
    Args:
        fecha: Date in various formats
    
    Returns:
        Date in YYYY-MM-DD format
    """
    fecha = (fecha or "").strip()
    if not fecha:
        return ""

    # Already ISO (possibly with a time component we can drop).
    if re.match(r"\d{4}-\d{2}-\d{2}", fecha):
        return fecha[:10]

    # DD/MM/YYYY, the dominant format in Mexican official exports.
    if "/" in fecha:
        parts = fecha.split("/")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            dia, mes, anio = parts
            if len(anio) == 4:
                return f"{anio}-{mes.zfill(2)}-{dia.zfill(2)}"

    for pattern in ("%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(fecha, pattern).strftime("%Y-%m-%d")
        except ValueError:
            continue

    return fecha


def normalizar_cve_ent(cve: str) -> str:
    """
    Normalize entity code to INEGI 2-digit format.
    
    Args:
        cve: Entity code in various formats
    
    Returns:
        2-digit entity code
    """
    # Remove non-numeric characters
    cve_num = ''.join(filter(str.isdigit, str(cve)))
    
    # Pad with zeros if needed
    return cve_num.zfill(2)[:2]


def normalizar_cve_mun(cve_ent: str, cve_mun: str) -> str:
    """
    Normalize municipality code to INEGI 5-digit format.
    
    Args:
        cve_ent: Entity code (2 digits)
        cve_mun: Municipality code (3 digits)
    
    Returns:
        5-digit municipality code (entity + municipality)
    """
    # Ensure entity code is 2 digits
    cve_ent = normalizar_cve_ent(cve_ent)
    
    # Extract numeric part of municipality code
    cve_mun_num = ''.join(filter(str.isdigit, str(cve_mun)))
    
    # Pad with zeros if needed
    cve_mun_padded = cve_mun_num.zfill(3)[:3]
    
    return cve_ent + cve_mun_padded


def normalizar_nombre_morbilidad(nombre: str) -> str:
    """
    Normalize morbidity name to standard catalog.
    
    Args:
        nombre: Morbidity name in various formats
    
    Returns:
        Standardized morbidity name
    """
    # TODO: Implement mapping to catalog
    # Use fuzzy matching for similar names
    
    # Basic cleaning
    nombre_limpio = nombre.strip().lower()
    
    # Map common variations
    mappings = {
        "covid": "COVID-19",
        "coronavirus": "COVID-19",
        "sars-cov-2": "COVID-19",
        "dengue clasico": "Dengue",
        "dengue hemorragico": "Dengue hemorrágico",
        "gripe": "Influenza",
        "flu": "Influenza"
    }
    
    for key, value in mappings.items():
        if key in nombre_limpio:
            return value
    
    # Return title case if no mapping found
    return nombre.strip().title()


def calcular_semana_iso(fecha: str) -> int:
    """
    Calculate ISO week number from date.
    
    Args:
        fecha: Date in YYYY-MM-DD format
    
    Returns:
        ISO week number (1-53)
    """
    try:
        return datetime.fromisoformat(fecha).isocalendar()[1]
    except (TypeError, ValueError):
        # An unparseable date has no meaningful week; the caller filters these
        # out before they reach the series.
        return 1


def validar_casos_defunciones(casos: int, defunciones: int) -> bool:
    """
    Validate that cases and deaths are non-negative and logical.
    
    Args:
        casos: Number of cases
        defunciones: Number of deaths
    
    Returns:
        True if valid, False otherwise
    """
    # Basic validation
    if casos < 0 or defunciones < 0:
        return False
    
    # Deaths should not exceed cases
    if defunciones > casos:
        return False
    
    return True


if __name__ == "__main__":
    # Test functions
    print("=== Test de normalización ===")
    
    # Test date normalization
    print(f"Fecha 15/01/2025 -> {estandarizar_fecha('15/01/2025')}")
    print(f"Fecha 2025-01-15 -> {estandarizar_fecha('2025-01-15')}")
    
    # Test entity code normalization
    print(f"Entidad '9' -> {normalizar_cve_ent('9')}")
    print(f"Entidad '31' -> {normalizar_cve_ent('31')}")
    
    # Test morbidity normalization
    print(f"Morbilidad 'covid' -> {normalizar_nombre_morbilidad('covid')}")
    print(f"Morbilidad 'Dengue clasico' -> {normalizar_nombre_morbilidad('Dengue clasico')}")
    
    # Test ISO week calculation
    print(f"Semana ISO de 2025-01-15 -> {calcular_semana_iso('2025-01-15')}")
