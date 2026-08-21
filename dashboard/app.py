"""Episcopio Dashboard — Dash/Plotly application.

The interaction model is "paste your keys and it runs":

1. On first load the browser is issued an opaque session id (and *only* that —
   credentials never leave the server once submitted).
2. The connect panel lists every provider from the registry. Saving stores the
   keys in the server-side vault and immediately starts a pipeline run.
3. A poller shows live per-source progress and swaps the charts over to the
   session's own data the moment the run produces any.

Until a run succeeds the dashboard renders bundled sample data, clearly badged,
so the app is explorable with no credentials at all.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import dash
import plotly.graph_objs as go
from dash import ALL, Input, Output, State, dcc, html, no_update

from dashboard.services.api_client import api_client
from ingesta.providers import PROVIDERS

logger = logging.getLogger(__name__)

ENTIDADES = [
    {"label": "Nacional", "value": "00"},
    {"label": "Yucatán", "value": "31"},
    {"label": "Quintana Roo", "value": "23"},
    {"label": "Campeche", "value": "04"},
    {"label": "Ciudad de México", "value": "09"},
    {"label": "Nuevo León", "value": "19"},
]

MORBILIDADES = [
    {"label": "COVID-19", "value": "1"},
    {"label": "Dengue", "value": "2"},
    {"label": "Influenza", "value": "3"},
]

# Plotly styling that reads correctly in both light and dark themes: the paper
# is transparent so the card background shows through, and the grid is a
# low-alpha neutral rather than a fixed grey.
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="-apple-system, BlinkMacSystemFont, Segoe UI, Inter, sans-serif", size=12, color="#8b93a1"),
    margin=dict(l=48, r=24, t=16, b=40),
    hovermode="x unified",
    xaxis=dict(gridcolor="rgba(128,128,128,0.14)", zeroline=False, showline=False),
    yaxis=dict(gridcolor="rgba(128,128,128,0.14)", zeroline=False, showline=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

ACCENT = "#1f6feb"
POSITIVE = "#0f7b52"
DANGER = "#b4232b"

STATUS_BADGE = {
    "ok": ("ep-badge ep-badge--live", "Conectado"),
    "success": ("ep-badge ep-badge--live", "Listo"),
    "running": ("ep-badge ep-badge--running", "En progreso"),
    "pending": ("ep-badge ep-badge--neutral", "En espera"),
    "skipped": ("ep-badge ep-badge--neutral", "Omitido"),
    "partial": ("ep-badge ep-badge--sample", "Parcial"),
    "error": ("ep-badge ep-badge--error", "Error"),
    "unreachable": ("ep-badge ep-badge--error", "Sin conexión"),
    "idle": ("ep-badge ep-badge--neutral", "Sin ejecutar"),
}

TERMINAL_RUN_STATES = {"success", "partial", "error"}


# ---------------------------------------------------------------------------
# Presentation helpers
# ---------------------------------------------------------------------------

def _fmt_int(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _delta_node(value: Any, label: str = "vs. periodo anterior") -> html.Span:
    """Render a percentage change with direction-appropriate colour.

    For epidemiological counts a rise is bad news, so "up" is styled with the
    danger colour rather than the usual green-for-growth convention.
    """
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return html.Span("Sin comparativo", className="ep-kpi-delta ep-kpi-delta--flat")

    if pct > 0:
        cls, arrow = "ep-kpi-delta ep-kpi-delta--up", "▲"
    elif pct < 0:
        cls, arrow = "ep-kpi-delta ep-kpi-delta--down", "▼"
    else:
        cls, arrow = "ep-kpi-delta ep-kpi-delta--flat", "■"
    return html.Span(f"{arrow} {abs(pct):g}% {label}", className=cls)


def _badge(status: str) -> html.Span:
    cls, text = STATUS_BADGE.get(status, STATUS_BADGE["idle"])
    dot_cls = "ep-dot ep-dot--pulse" if status == "running" else "ep-dot"
    return html.Span([html.Span(className=dot_cls), text], className=cls)


def _kpi_card(label: str, value: Any, delta: Any) -> html.Div:
    return html.Div(
        [
            html.Span(label, className="ep-kpi-label"),
            html.Span(_fmt_int(value), className="ep-kpi-value"),
            _delta_node(delta),
        ],
        className="ep-card ep-kpi",
    )


def _empty_figure(message: str) -> go.Figure:
    """A chart placeholder that says *why* it is empty."""
    fig = go.Figure()
    fig.update_layout(
        **{**CHART_LAYOUT, "xaxis": dict(visible=False), "yaxis": dict(visible=False)},
        annotations=[
            dict(
                text=message,
                showarrow=False,
                xref="paper",
                yref="paper",
                x=0.5,
                y=0.5,
                font=dict(size=13, color="#8b93a1"),
            )
        ],
        height=280,
    )
    return fig


# ---------------------------------------------------------------------------
# Layout fragments
# ---------------------------------------------------------------------------

def _provider_block(provider) -> html.Div:
    """One provider's credential inputs inside the connect panel."""
    fields = [
        html.Div(
            [
                html.Label(
                    field.label + ("" if field.required else " (opcional)"),
                    className="ep-label",
                    htmlFor=f"cred-{provider.id}-{field.name}",
                ),
                dcc.Input(
                    id={"type": "cred-input", "provider": provider.id, "field": field.name},
                    type="password" if field.secret else "text",
                    placeholder=field.placeholder,
                    className="ep-input",
                    autoComplete="off",
                    persistence=False,
                    debounce=True,
                ),
            ],
            className="ep-field",
        )
        for field in provider.fields
    ]

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(provider.label, className="ep-provider-name"),
                            html.Div(provider.description, className="ep-provider-desc"),
                        ]
                    ),
                    html.A("Documentación ↗", href=provider.doc_url, target="_blank", rel="noopener noreferrer",
                           className="ep-hint"),
                ],
                className="ep-provider-head",
            ),
            html.Div(fields, className="ep-provider-fields"),
        ],
        className="ep-provider",
    )


def _connect_panel() -> html.Div:
    credentialed = [p for p in PROVIDERS if p.needs_credentials]
    public = [p for p in PROVIDERS if not p.needs_credentials]

    return html.Div(
        html.Div(
            [
                html.Div(
                    [
                        html.Div("Conecta tus fuentes", className="ep-modal-title"),
                        html.P(
                            "Ingresa las llaves de las plataformas que quieras monitorear. "
                            "Al guardar, Episcopio valida cada credencial y ejecuta la ingesta "
                            "automáticamente. Puedes explorar con datos de muestra sin conectar nada.",
                            className="ep-modal-lede",
                        ),
                    ],
                    className="ep-modal-head",
                ),
                html.Div(
                    [
                        html.Span("🔒"),
                        html.Span(
                            [
                                html.Strong("Tus llaves no salen del servidor. "),
                                "Se guardan solo en memoria, ligadas a esta sesión, y se borran "
                                "al expirar o al cerrar sesión. El navegador únicamente conserva "
                                "un identificador de sesión, nunca las credenciales.",
                            ]
                        ),
                    ],
                    className="ep-note",
                    style={"marginBottom": "16px"},
                ),
                html.Div(
                    [
                        html.Span("Fuentes públicas activas sin credenciales: "),
                        html.Strong(", ".join(p.label for p in public) or "ninguna"),
                    ],
                    className="ep-hint",
                    style={"marginBottom": "8px"},
                ),
                html.Div([_provider_block(p) for p in credentialed]),
                html.Div(
                    [
                        html.Button("Explorar con datos de muestra", id="cancel-keys",
                                    n_clicks=0, className="ep-btn ep-btn--ghost"),
                        html.Button("Guardar y ejecutar", id="save-keys",
                                    n_clicks=0, className="ep-btn ep-btn--primary"),
                    ],
                    className="ep-modal-foot",
                ),
            ],
            className="ep-modal",
        ),
        id="connect-backdrop",
        className="ep-modal-backdrop",
    )


def _header() -> html.Div:
    return html.Header(
        html.Div(
            [
                html.Div(
                    [
                        html.Div("E", className="ep-mark"),
                        html.Div(
                            [
                                html.Span("Episcopio", className="ep-brand-name"),
                                html.Span("Pulso epidemiológico de México", className="ep-brand-tagline"),
                            ],
                            className="ep-brand-text",
                        ),
                    ],
                    className="ep-brand",
                ),
                html.Div(
                    [
                        html.Div(_badge("idle"), id="data-mode-badge"),
                        html.Button("Ejecutar ahora", id="run-now", n_clicks=0, className="ep-btn"),
                        html.Button("Fuentes", id="open-connect", n_clicks=0,
                                    className="ep-btn ep-btn--primary"),
                    ],
                    className="ep-header-actions",
                ),
            ],
            className="ep-header-inner",
        ),
        className="ep-header",
    )


def _filters() -> html.Div:
    return html.Div(
        [
            html.Div(
                [
                    html.Label("Entidad federativa", className="ep-label", htmlFor="entidad-dropdown"),
                    dcc.Dropdown(id="entidad-dropdown", options=ENTIDADES, value="31", clearable=False),
                ],
                className="ep-field",
            ),
            html.Div(
                [
                    html.Label("Morbilidad", className="ep-label", htmlFor="morbilidad-dropdown"),
                    dcc.Dropdown(id="morbilidad-dropdown", options=MORBILIDADES, value="1", clearable=False),
                ],
                className="ep-field",
            ),
            html.Div(
                html.Button("Actualizar vista", id="update-button", n_clicks=0,
                            className="ep-btn ep-btn--block"),
                className="ep-field",
            ),
        ],
        className="ep-card ep-filters",
    )


def _build_layout() -> html.Div:
    return html.Div(
        [
            dcc.Location(id="url"),
            # Only an opaque session id lives in the browser — never a credential.
            dcc.Store(id="session-store", storage_type="session"),
            dcc.Store(id="run-store", data={}),
            dcc.Store(id="data-version", data=0),
            dcc.Interval(id="run-poll", interval=1500, disabled=True),
            _connect_panel(),
            _header(),
            html.Main(
                [
                    html.Section(
                        [
                            html.Div(
                                [
                                    html.Span("Estado de la ingesta", className="ep-section-title"),
                                    html.Span("", id="run-summary", className="ep-card-sub"),
                                ],
                                className="ep-section-head",
                            ),
                            html.Div(id="run-panel", className="ep-card"),
                        ],
                        className="ep-section",
                    ),
                    html.Section(_filters(), className="ep-section"),
                    html.Section(
                        html.Div(id="kpi-cards", className="ep-kpi-grid"),
                        className="ep-section",
                    ),
                    html.Section(
                        [
                            html.Div(
                                html.Span("Series", className="ep-section-title"),
                                className="ep-section-head",
                            ),
                            html.Div(
                                [
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H2("Casos confirmados"),
                                                    html.Span("Serie oficial diaria", className="ep-card-sub"),
                                                ],
                                                className="ep-card-head",
                                            ),
                                            dcc.Graph(
                                                id="timeseries-chart",
                                                config={"displaylogo": False, "responsive": True},
                                            ),
                                        ],
                                        className="ep-card",
                                    ),
                                    html.Div(
                                        [
                                            html.Div(
                                                [
                                                    html.H2("Señal social"),
                                                    html.Span("Menciones y sentimiento", className="ep-card-sub"),
                                                ],
                                                className="ep-card-head",
                                            ),
                                            dcc.Graph(
                                                id="sentiment-chart",
                                                config={"displaylogo": False, "responsive": True},
                                            ),
                                        ],
                                        className="ep-card",
                                    ),
                                ],
                                className="ep-chart-grid",
                            ),
                        ],
                        className="ep-section",
                    ),
                    html.Section(
                        [
                            html.Div(
                                html.Span("Alertas activas", className="ep-section-title"),
                                className="ep-section-head",
                            ),
                            html.Div(id="alerts-container", className="ep-card"),
                        ],
                        className="ep-section",
                    ),
                ],
                className="ep-main",
            ),
            html.Footer(
                [
                    html.P("Episcopio · Monitoreo epidemiológico de México"),
                    html.Div(
                        [
                            html.A("Documentación", href="https://github.com/PedroRgz/Episcopio",
                                   target="_blank", rel="noopener noreferrer"),
                            html.A("API", href="/api/v1/status"),
                        ],
                        className="ep-footer-links",
                    ),
                ],
                className="ep-footer",
            ),
        ],
        className="ep-shell",
    )


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def build_dashboard_app(requests_pathname_prefix: str = "/") -> dash.Dash:
    """Build and configure the Dash application.

    Args:
        requests_pathname_prefix: URL prefix the browser uses to reach Dash.

    Returns:
        A configured :class:`dash.Dash` instance.
    """
    app = dash.Dash(
        __name__,
        title="Episcopio · Monitoreo epidemiológico",
        update_title=None,
        suppress_callback_exceptions=True,
        requests_pathname_prefix=requests_pathname_prefix,
        meta_tags=[
            {"name": "viewport", "content": "width=device-width, initial-scale=1"},
            {"name": "color-scheme", "content": "light dark"},
            {
                "name": "description",
                "content": "Monitoreo epidemiológico de México: KPIs oficiales, señal social y alertas.",
            },
        ],
    )

    app.layout = _build_layout()

    # -- session bootstrap ------------------------------------------------

    @app.callback(
        Output("session-store", "data"),
        Input("url", "pathname"),
        State("session-store", "data"),
    )
    def init_session(_pathname, current):
        """Issue (or revive) this browser's session id on load."""
        session_id = api_client.ensure_session(current)
        return session_id if session_id != current else no_update

    # -- connect panel ----------------------------------------------------

    @app.callback(
        Output("connect-backdrop", "style"),
        Input("open-connect", "n_clicks"),
        Input("cancel-keys", "n_clicks"),
        Input("save-keys", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_connect(_open, _cancel, _save):
        trigger = dash.callback_context.triggered_id
        if trigger == "open-connect":
            return {"display": "flex"}
        return {"display": "none"}

    # -- save credentials and auto-run ------------------------------------

    @app.callback(
        Output("run-store", "data"),
        Output("run-poll", "disabled"),
        Input("save-keys", "n_clicks"),
        Input("run-now", "n_clicks"),
        State({"type": "cred-input", "provider": ALL, "field": ALL}, "value"),
        State({"type": "cred-input", "provider": ALL, "field": ALL}, "id"),
        State("session-store", "data"),
        prevent_initial_call=True,
    )
    def save_and_run(_save_clicks, _run_clicks, values, ids, session_id):
        """Persist credentials server-side, then kick off a run.

        Values arrive from the browser only at this moment; they are handed
        straight to the vault and never echoed back into any component.
        """
        session_id = api_client.ensure_session(session_id)
        if not session_id:
            return {"status": "error", "summary": "No fue posible iniciar la sesión.", "steps": []}, True

        if dash.callback_context.triggered_id == "save-keys":
            grouped: Dict[str, Dict[str, str]] = {}
            for value, ident in zip(values or [], ids or []):
                if not isinstance(ident, dict):
                    continue
                grouped.setdefault(ident["provider"], {})[ident["field"]] = (value or "")
            for provider_id, creds in grouped.items():
                api_client.set_credentials(session_id, provider_id, creds)

        run = api_client.start_pipeline(session_id)
        if run is None:
            return {"status": "error", "summary": "La sesión expiró. Recarga la página.", "steps": []}, True
        return run, False

    # -- poll run progress -------------------------------------------------

    @app.callback(
        Output("run-panel", "children"),
        Output("run-summary", "children"),
        Output("run-poll", "disabled", allow_duplicate=True),
        Output("data-version", "data"),
        Output("data-mode-badge", "children"),
        Input("run-poll", "n_intervals"),
        Input("run-store", "data"),
        Input("session-store", "data"),
        State("data-version", "data"),
        prevent_initial_call="initial_duplicate",
    )
    def poll_run(_ticks, _run_seed, session_id, version):
        """Render live run progress and flip the charts over when data lands."""
        status_payload = api_client.pipeline_status(session_id)
        status = status_payload.get("status", "idle")
        steps: List[Dict[str, Any]] = status_payload.get("steps", [])

        live = api_client.has_live_data(session_id)
        badge_text = api_client.data_source_label(session_id)
        mode_badge = html.Span(
            [html.Span(className="ep-dot"), badge_text],
            className="ep-badge ep-badge--live" if live else "ep-badge ep-badge--sample",
        )

        if status == "idle":
            panel = html.Div(
                [
                    html.P("Aún no se ha ejecutado ninguna ingesta en esta sesión."),
                    html.P(
                        "Conecta al menos una fuente para traer datos en vivo, o continúa "
                        "explorando con los datos de muestra.",
                        className="ep-hint",
                        style={"marginTop": "6px"},
                    ),
                ],
                className="ep-empty",
            )
            return panel, "", True, no_update, mode_badge

        done = sum(1 for s in steps if s.get("status") in {"success", "error", "skipped", "unreachable"})
        pct = int((done / len(steps)) * 100) if steps else 0

        rows = [
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(step.get("label", step.get("key", "")), className="ep-row-title"),
                            html.Span(step.get("message") or "—", className="ep-row-sub"),
                        ],
                        className="ep-row-main",
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"{_fmt_int(step.get('records', 0))} reg.",
                                className="ep-hint",
                                style={"marginRight": "10px"},
                            )
                            if step.get("records")
                            else html.Span(),
                            _badge(step.get("status", "pending")),
                        ],
                        style={"display": "flex", "alignItems": "center"},
                    ),
                ],
                className="ep-row",
            )
            for step in steps
        ]

        panel = html.Div(
            [
                html.Div(
                    html.Div(className="ep-progress-bar", style={"width": f"{pct}%"}),
                    className="ep-progress",
                    style={"marginBottom": "16px"},
                ),
                html.Div(rows, className="ep-list"),
            ]
        )

        finished = status in TERMINAL_RUN_STATES
        summary = html.Span([_badge(status), " ", status_payload.get("summary", "")])
        # Bump the version only once the run settles, so the charts redraw
        # exactly once rather than on every poll tick.
        new_version = (version or 0) + 1 if finished else no_update

        return panel, summary, finished, new_version, mode_badge

    # -- data rendering ----------------------------------------------------

    @app.callback(
        Output("kpi-cards", "children"),
        Input("update-button", "n_clicks"),
        Input("entidad-dropdown", "value"),
        Input("data-version", "data"),
        State("session-store", "data"),
    )
    def render_kpis(_clicks, entidad, _version, session_id):
        kpis = api_client.get_kpis(session_id, entidad or "31")
        return [
            _kpi_card("Casos totales", kpis.get("casos_totales"), kpis.get("variacion_casos")),
            _kpi_card("Casos activos", kpis.get("casos_activos"), kpis.get("variacion_activos")),
            _kpi_card("Defunciones", kpis.get("defunciones"), kpis.get("variacion_defunciones")),
        ]

    @app.callback(
        Output("timeseries-chart", "figure"),
        Input("update-button", "n_clicks"),
        Input("entidad-dropdown", "value"),
        Input("data-version", "data"),
        State("session-store", "data"),
    )
    def update_timeseries(_clicks, entidad, _version, session_id):
        data = api_client.get_timeseries(session_id, entidad or "31")
        serie = data.get("serie_oficial") or []
        if not serie:
            return _empty_figure("Sin datos para el periodo seleccionado.")

        fechas = [p.get("fecha") for p in serie]
        casos = [p.get("casos", 0) for p in serie]
        defunciones = [p.get("defunciones", 0) for p in serie]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=fechas, y=casos, name="Casos", mode="lines",
                line=dict(color=ACCENT, width=2.5, shape="spline", smoothing=0.4),
                fill="tozeroy", fillcolor="rgba(31,111,235,0.10)",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=fechas, y=defunciones, name="Defunciones", mode="lines",
                line=dict(color=DANGER, width=2, dash="dot"),
            )
        )
        fig.update_layout(**CHART_LAYOUT, height=300)
        return fig

    @app.callback(
        Output("sentiment-chart", "figure"),
        Input("update-button", "n_clicks"),
        Input("entidad-dropdown", "value"),
        Input("data-version", "data"),
        State("session-store", "data"),
    )
    def update_sentiment(_clicks, entidad, _version, session_id):
        data = api_client.get_timeseries(session_id, entidad or "31")
        menciones = (data.get("serie_social") or {}).get("menciones") or []
        if not menciones:
            return _empty_figure("Conecta una fuente social para ver esta serie.")

        fechas = [m.get("fecha") for m in menciones]
        conteos = [m.get("conteo", 0) for m in menciones]
        sentimientos = [m.get("sentimiento", 0) for m in menciones]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(x=fechas, y=conteos, name="Menciones",
                   marker_color="rgba(31,111,235,0.45)", marker_line_width=0)
        )
        fig.add_trace(
            go.Scatter(x=fechas, y=sentimientos, name="Sentimiento", yaxis="y2",
                       mode="lines", line=dict(color=POSITIVE, width=2.5))
        )
        layout = dict(CHART_LAYOUT)
        layout["yaxis2"] = dict(
            overlaying="y", side="right", range=[-1, 1], showgrid=False,
            zeroline=True, zerolinecolor="rgba(128,128,128,0.3)",
        )
        fig.update_layout(**layout, height=300, bargap=0.35)
        return fig

    @app.callback(
        Output("alerts-container", "children"),
        Input("update-button", "n_clicks"),
        Input("data-version", "data"),
        State("session-store", "data"),
    )
    def update_alerts(_clicks, _version, session_id):
        alertas = (api_client.get_alerts(session_id) or {}).get("alertas") or []
        if not alertas:
            return html.Div("No hay alertas activas.", className="ep-empty")

        cards = []
        for alerta in alertas:
            tipo = str(alerta.get("tipo", "alerta")).replace("_", " ").capitalize()
            evidencia = alerta.get("evidencia") or {}
            detalle = alerta.get("mensaje") or ", ".join(
                f"{k.replace('_', ' ')}: {v}" for k, v in evidencia.items()
            )
            cards.append(
                html.Div(
                    [
                        html.Span("⚠", style={"color": "var(--warning)", "fontSize": "16px"}),
                        html.Div(
                            [
                                html.Span(alerta.get("nombre") or tipo, className="ep-alert-title"),
                                html.Span(detalle or "Sin detalle disponible.", className="ep-alert-meta"),
                                html.Span(
                                    f"Regla {alerta.get('regla', 'N/D')} · {alerta.get('created_at', '')}",
                                    className="ep-alert-meta",
                                ),
                            ],
                            className="ep-alert-body",
                        ),
                    ],
                    className="ep-alert",
                )
            )
        return cards

    return app


# Module-level instance for standalone execution (`python -m dashboard.app`).
app = build_dashboard_app()
server = app.server


if __name__ == "__main__":
    import os

    # Debug mode enables the Werkzeug interactive debugger, which executes
    # arbitrary code from the browser — it must never default to on, and it
    # binds to loopback so it is not reachable from the network.
    debug = os.getenv("EP_DEBUG", "").lower() in ("1", "true", "yes")
    app.run(debug=debug, host=os.getenv("EP_DASH_HOST", "127.0.0.1"), port=8050)
