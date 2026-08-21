"""Tests for normalization, KPIs and alert rules."""
from analytics.alertas import evaluar_alertas, evaluar_regla_incremento, evaluar_regla_social
from analytics.kpis import calcular_kpis, serie_por_fecha
from etl.normaliza import (
    estandarizar_fecha,
    normalizar_cve_ent,
    normalizar_dge,
    normalizar_menciones,
)


# -- normalization ---------------------------------------------------------

def test_estandarizar_fecha_handles_common_formats():
    assert estandarizar_fecha("2025-01-15") == "2025-01-15"
    assert estandarizar_fecha("15/01/2025") == "2025-01-15"
    assert estandarizar_fecha("15-01-2025") == "2025-01-15"
    assert estandarizar_fecha("2025-01-15T10:00:00Z") == "2025-01-15"
    assert estandarizar_fecha("") == ""


def test_normalizar_dge_drops_impossible_rows():
    result = normalizar_dge([
        {"fecha": "2025-01-01", "cve_ent": "31", "casos": 10, "defunciones": 1},
        {"fecha": "no-es-fecha", "cve_ent": "31", "casos": 5, "defunciones": 0},
        # Deaths exceeding cases is impossible and must not enter the series.
        {"fecha": "2025-01-02", "cve_ent": "31", "casos": 1, "defunciones": 9},
    ])
    assert result["filas_normalizadas"] == 1
    assert result["filas_descartadas"] == 2


def test_normalizar_dge_tolerates_garbage_input():
    result = normalizar_dge([None, "texto", 42, {}])
    assert result["filas_normalizadas"] == 0


def test_normalizar_cve_ent_pads_to_two_digits():
    assert normalizar_cve_ent("9") == "09"
    assert normalizar_cve_ent("31") == "31"
    assert normalizar_cve_ent("ENT-9") == "09"


def test_normalizar_menciones_aggregates_per_day():
    result = normalizar_menciones([
        {"fecha": "2025-01-01", "fuente": "twitter", "sentimiento": -0.4},
        {"fecha": "2025-01-01", "fuente": "reddit", "sentimiento": -0.2},
        {"fecha": "2025-01-02", "fuente": "twitter", "sentimiento": 0.5},
    ])
    serie = result["menciones"]
    assert [p["fecha"] for p in serie] == ["2025-01-01", "2025-01-02"]
    assert serie[0]["conteo"] == 2
    assert serie[0]["sentimiento"] == -0.3
    assert result["por_fuente"] == {"twitter": 2, "reddit": 1}


def test_normalizar_menciones_clamps_out_of_range_sentiment():
    result = normalizar_menciones([{"fecha": "2025-01-01", "sentimiento": 42}])
    assert result["menciones"][0]["sentimiento"] == 1.0


# -- KPIs ------------------------------------------------------------------

def test_calcular_kpis_on_empty_series_returns_full_shape():
    kpis = calcular_kpis([])
    assert kpis["casos_totales"] == 0
    assert "variacion_casos" in kpis


def test_calcular_kpis_totals_and_entity_filter():
    serie = [
        {"fecha": "2025-01-01", "cve_ent": "31", "casos": 10, "defunciones": 1},
        {"fecha": "2025-01-02", "cve_ent": "31", "casos": 20, "defunciones": 2},
        {"fecha": "2025-01-02", "cve_ent": "09", "casos": 5, "defunciones": 0},
    ]
    assert calcular_kpis(serie)["casos_totales"] == 35
    assert calcular_kpis(serie, "31")["casos_totales"] == 30
    assert calcular_kpis(serie, "09")["defunciones"] == 0


def test_pct_change_from_zero_baseline_does_not_divide_by_zero():
    serie = [
        {"fecha": "2025-01-01", "cve_ent": "31", "casos": 0, "defunciones": 0},
        {"fecha": "2025-01-12", "cve_ent": "31", "casos": 50, "defunciones": 0},
    ]
    assert calcular_kpis(serie, "31")["variacion_casos"] == 100.0


def test_serie_por_fecha_collapses_entities():
    serie = [
        {"fecha": "2025-01-01", "cve_ent": "31", "casos": 10, "defunciones": 1},
        {"fecha": "2025-01-01", "cve_ent": "09", "casos": 5, "defunciones": 0},
    ]
    collapsed = serie_por_fecha(serie)
    assert collapsed == [{"fecha": "2025-01-01", "casos": 15, "defunciones": 1}]


# -- alerts ----------------------------------------------------------------

def test_incremento_rule_fires_on_a_spike():
    datos = [{"fecha": f"2025-01-{d:02d}", "casos": 10} for d in range(1, 15)]
    datos.append({"fecha": "2025-01-15", "casos": 90})
    evidencia = evaluar_regla_incremento(
        {"serie": "casos", "ventana_ref": 14, "umbral_delta": 0.2, "min_casos": 5}, datos
    )
    assert evidencia is not None
    assert evidencia["delta_porcentaje"] > 20


def test_incremento_rule_ignores_flat_series():
    datos = [{"fecha": f"2025-01-{d:02d}", "casos": 10} for d in range(1, 16)]
    assert evaluar_regla_incremento({"serie": "casos", "umbral_delta": 0.2, "min_casos": 5}, datos) is None


def test_incremento_rule_needs_enough_history():
    assert evaluar_regla_incremento({"serie": "casos"}, [{"fecha": "2025-01-01", "casos": 100}]) is None


def test_social_rule_requires_both_spike_and_negativity():
    # Varied baseline: a perfectly flat series has zero variance and is
    # deliberately never alertable (covered separately below).
    volumes = [8, 12, 9, 11, 10, 13, 9, 10, 12]
    base = [
        {"fecha": f"2025-01-{d:02d}", "conteo": v, "sentimiento": -0.5}
        for d, v in enumerate(volumes, start=1)
    ]

    spike_negative = base + [{"fecha": "2025-01-10", "conteo": 200, "sentimiento": -0.6}]
    assert evaluar_regla_social({"zscore": 2.0, "sentimiento_max": -0.2}, spike_negative) is not None

    # Same volume spike, but positive sentiment: must not fire.
    spike_positive = base + [{"fecha": "2025-01-10", "conteo": 200, "sentimiento": 0.6}]
    assert evaluar_regla_social({"zscore": 2.0, "sentimiento_max": -0.2}, spike_positive) is None


def test_social_rule_handles_zero_variance():
    flat = [{"fecha": f"2025-01-{d:02d}", "conteo": 10, "sentimiento": -0.5} for d in range(1, 10)]
    assert evaluar_regla_social({"zscore": 2.0, "sentimiento_max": -0.2}, flat) is None


def test_evaluar_alertas_on_empty_input_is_safe():
    result = evaluar_alertas([], [])
    assert result["alertas"] == []
    assert result["alertas_evaluadas"] >= 1
