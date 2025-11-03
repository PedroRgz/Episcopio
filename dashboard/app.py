"""Episcopio Dashboard - Modern, Responsive Dash/Plotly application."""
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

from services.api_client import api_client

# Initialize Dash app with responsive meta tags
app = dash.Dash(
    __name__,
    title="Episcopio - Monitoreo Epidemiológico",
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ]
)

# Custom color scheme
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#27ae60',
    'warning': '#f39c12',
    'danger': '#e74c3c',
    'info': '#3498db',
    'light': '#ecf0f1',
    'dark': '#2c3e50',
    'text': '#7f8c8d'
}

# App layout with modern design
app.layout = html.Div(
    style={
        'maxWidth': '1400px',
        'margin': '0 auto',
        'padding': '20px',
        'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    },
    children=[
        # Data stores
        dcc.Store(id='api-keys-store', data={}),
        dcc.Store(id='use-sample-data-store', data=True),
        
        # API Keys Modal
        html.Div(
            id="api-keys-modal",
            style={'display': 'block'},
            children=[
                html.Div(
                    style={
                        'position': 'fixed',
                        'top': '0',
                        'left': '0',
                        'width': '100%',
                        'height': '100%',
                        'backgroundColor': 'rgba(0,0,0,0.6)',
                        'backdropFilter': 'blur(5px)',
                        'display': 'flex',
                        'justifyContent': 'center',
                        'alignItems': 'center',
                        'zIndex': '1000',
                        'padding': '20px'
                    },
                    children=[
                        html.Div(
                            style={
                                'backgroundColor': 'white',
                                'borderRadius': '20px',
                                'padding': '40px',
                                'maxWidth': '600px',
                                'width': '100%',
                                'maxHeight': '90vh',
                                'overflowY': 'auto',
                                'boxShadow': '0 20px 60px rgba(0, 0, 0, 0.3)'
                            },
                            children=[
                                html.H2("⚙️ Configuración de API Keys", 
                                       style={'color': COLORS['dark'], 'marginBottom': '10px', 'fontSize': '1.8rem'}),
                                html.P(
                                    "Ingrese sus API keys para acceder a datos en tiempo real. "
                                    "Si prefiere explorar con datos de muestra, haga clic en 'Usar Datos de Muestra'.",
                                    style={'color': COLORS['text'], 'marginBottom': '20px', 'lineHeight': '1.6'}
                                ),
                                html.Div(
                                    style={
                                        'background': 'linear-gradient(135deg, #fff3cd 0%, #ffe8a1 100%)',
                                        'borderLeft': '4px solid ' + COLORS['warning'],
                                        'padding': '15px',
                                        'borderRadius': '8px',
                                        'marginBottom': '25px'
                                    },
                                    children=[
                                        html.P([
                                            html.Strong("⚠️ Advertencia de Seguridad: ", style={'color': COLORS['warning']}),
                                            "Las API keys se almacenan temporalmente en memoria durante esta sesión. "
                                            "Para uso en producción, implemente un sistema de gestión de secretos apropiado."
                                        ], style={'color': COLORS['text'], 'margin': '0', 'fontSize': '0.85rem'})
                                    ]
                                ),
                                
                                # API Key Inputs
                                *[html.Div([
                                    html.Label(label + ":", style={'fontWeight': '600', 'marginBottom': '8px', 'display': 'block', 'color': COLORS['dark']}),
                                    dcc.Input(
                                        id=input_id,
                                        type="password",
                                        placeholder=f"Ingrese su {label.lower()}",
                                        style={
                                            'width': '100%',
                                            'padding': '12px',
                                            'border': '2px solid #e0e0e0',
                                            'borderRadius': '10px',
                                            'fontSize': '0.95rem',
                                            'marginBottom': '20px'
                                        }
                                    )
                                ]) for label, input_id in [
                                    ("INEGI Token", "api-key-inegi"),
                                    ("Twitter Bearer Token", "api-key-twitter"),
                                    ("Facebook Access Token", "api-key-facebook"),
                                    ("Reddit Client ID", "api-key-reddit"),
                                    ("NewsAPI Key", "api-key-newsapi")
                                ]],
                                
                                # Modal actions
                                html.Div(
                                    style={'display': 'flex', 'gap': '10px', 'justifyContent': 'flex-end', 'marginTop': '30px'},
                                    children=[
                                        html.Button(
                                            "Guardar y Usar APIs",
                                            id="save-api-keys",
                                            n_clicks=0,
                                            style={
                                                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                                                'color': 'white',
                                                'border': 'none',
                                                'padding': '12px 25px',
                                                'borderRadius': '10px',
                                                'cursor': 'pointer',
                                                'fontWeight': '600',
                                                'fontSize': '0.95rem'
                                            }
                                        ),
                                        html.Button(
                                            "Usar Datos de Muestra",
                                            id="cancel-api-keys",
                                            n_clicks=0,
                                            style={
                                                'backgroundColor': '#95a5a6',
                                                'color': 'white',
                                                'border': 'none',
                                                'padding': '12px 25px',
                                                'borderRadius': '10px',
                                                'cursor': 'pointer',
                                                'fontWeight': '600',
                                                'fontSize': '0.95rem'
                                            }
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                )
            ]
        ),
        
        # Header
        html.Div(
            style={
                'background': 'white',
                'borderRadius': '15px',
                'padding': '25px',
                'marginBottom': '25px',
                'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)',
                'display': 'flex',
                'justifyContent': 'space-between',
                'alignItems': 'center',
                'flexWrap': 'wrap',
                'gap': '15px'
            },
            children=[
                html.Div([
                    html.H1(
                        "🏥 Episcopio",
                        style={
                            'color': COLORS['dark'],
                            'fontSize': '2.5rem',
                            'fontWeight': '700',
                            'margin': '0',
                            'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                            'WebkitBackgroundClip': 'text',
                            'WebkitTextFillColor': 'transparent',
                            'backgroundClip': 'text'
                        }
                    ),
                    html.P(
                        "Tomando el pulso epidemiológico de México",
                        style={'color': COLORS['text'], 'margin': '5px 0 0 0', 'fontSize': '1rem'}
                    )
                ]),
                html.Div(
                    style={'display': 'flex', 'gap': '10px', 'alignItems': 'center', 'flexWrap': 'wrap'},
                    children=[
                        html.Div(
                            id="data-mode-indicator",
                            children="🎭 Modo: Datos de Muestra",
                            style={
                                'backgroundColor': COLORS['warning'],
                                'color': 'white',
                                'padding': '10px 20px',
                                'borderRadius': '25px',
                                'fontSize': '0.9rem',
                                'fontWeight': '600',
                                'boxShadow': '0 4px 15px rgba(243, 156, 18, 0.3)'
                            }
                        ),
                        html.Button(
                            "⚙️ Configurar APIs",
                            id="open-api-modal",
                            n_clicks=0,
                            style={
                                'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                                'color': 'white',
                                'border': 'none',
                                'padding': '10px 20px',
                                'borderRadius': '25px',
                                'cursor': 'pointer',
                                'fontWeight': '600',
                                'fontSize': '0.9rem',
                                'boxShadow': f'0 4px 15px rgba(102, 126, 234, 0.3)'
                            }
                        )
                    ]
                )
            ]
        ),
        
        # Filters Section
        html.Div(
            style={
                'background': 'white',
                'borderRadius': '15px',
                'padding': '25px',
                'marginBottom': '25px',
                'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)'
            },
            children=[
                html.H3("🔍 Filtros", style={'color': COLORS['dark'], 'fontSize': '1.3rem', 'fontWeight': '600', 'marginTop': '0'}),
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))', 'gap': '20px', 'marginBottom': '20px'},
                    children=[
                        html.Div([
                            html.Label("Entidad Federativa:", style={'fontWeight': '600', 'marginBottom': '8px', 'display': 'block', 'color': COLORS['dark']}),
                            dcc.Dropdown(
                                id="entidad-dropdown",
                                options=[
                                    {"label": "🌴 Yucatán", "value": "31"},
                                    {"label": "🏖️ Quintana Roo", "value": "23"},
                                    {"label": "🌊 Campeche", "value": "04"},
                                    {"label": "🏙️ Ciudad de México", "value": "09"},
                                    {"label": "🏔️ Nuevo León", "value": "19"}
                                ],
                                value="31",
                                style={'borderRadius': '10px'}
                            )
                        ]),
                        html.Div([
                            html.Label("Morbilidad:", style={'fontWeight': '600', 'marginBottom': '8px', 'display': 'block', 'color': COLORS['dark']}),
                            dcc.Dropdown(
                                id="morbilidad-dropdown",
                                options=[
                                    {"label": "🦠 COVID-19", "value": "1"},
                                    {"label": "🦟 Dengue", "value": "2"},
                                    {"label": "🤧 Influenza", "value": "3"}
                                ],
                                value="1",
                                style={'borderRadius': '10px'}
                            )
                        ])
                    ]
                ),
                html.Button(
                    "🔄 Actualizar Dashboard",
                    id="update-button",
                    n_clicks=0,
                    style={
                        'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                        'color': 'white',
                        'border': 'none',
                        'padding': '12px 30px',
                        'borderRadius': '10px',
                        'cursor': 'pointer',
                        'fontWeight': '600',
                        'fontSize': '1rem',
                        'width': '100%',
                        'boxShadow': '0 4px 15px rgba(102, 126, 234, 0.3)'
                    }
                )
            ]
        ),
        
        # KPI Cards
        html.Div(
            id="kpi-cards",
            style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(280px, 1fr))', 'gap': '20px', 'marginBottom': '25px'}
        ),
        
        # Charts Section
        html.Div([
            html.Div(
                style={
                    'background': 'white',
                    'borderRadius': '15px',
                    'padding': '30px',
                    'marginBottom': '25px',
                    'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)'
                },
                children=[
                    html.H3("📈 Serie Temporal - Casos Confirmados", 
                           style={'color': COLORS['dark'], 'fontSize': '1.3rem', 'fontWeight': '600', 'marginTop': '0'}),
                    dcc.Graph(id="timeseries-chart", config={'displayModeBar': True, 'displaylogo': False})
                ]
            ),
            html.Div(
                style={
                    'background': 'white',
                    'borderRadius': '15px',
                    'padding': '30px',
                    'marginBottom': '25px',
                    'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)'
                },
                children=[
                    html.H3("💬 Análisis de Sentimiento en Redes Sociales", 
                           style={'color': COLORS['dark'], 'fontSize': '1.3rem', 'fontWeight': '600', 'marginTop': '0'}),
                    dcc.Graph(id="sentiment-chart", config={'displayModeBar': True, 'displaylogo': False})
                ]
            ),
            html.Div(
                style={
                    'background': 'white',
                    'borderRadius': '15px',
                    'padding': '30px',
                    'marginBottom': '25px',
                    'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)'
                },
                children=[
                    html.H3("⚠️ Alertas Activas", 
                           style={'color': COLORS['dark'], 'fontSize': '1.3rem', 'fontWeight': '600', 'marginTop': '0'}),
                    html.Div(id="alerts-container")
                ]
            )
        ]),
        
        # Footer
        html.Div(
            style={
                'background': 'white',
                'borderRadius': '15px',
                'padding': '20px',
                'textAlign': 'center',
                'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)',
                'marginTop': '30px'
            },
            children=[
                html.P(
                    "© 2025 Episcopio - Monitoreo Epidemiológico | Datos actualizados cada 6 horas",
                    style={'color': COLORS['text'], 'margin': '0', 'fontSize': '0.9rem'}
                ),
                html.P(
                    "📓 Explora los procesos ETL en el Jupyter Notebook incluido",
                    style={'color': COLORS['text'], 'margin': '10px 0 0 0', 'fontSize': '0.85rem', 'fontStyle': 'italic'}
                )
            ]
        )
    ]
)


# Callbacks
@app.callback(
    Output("api-keys-modal", "style"),
    [Input("save-api-keys", "n_clicks"),
     Input("cancel-api-keys", "n_clicks"),
     Input("open-api-modal", "n_clicks")],
    [State("api-keys-modal", "style")]
)
def toggle_modal(save_clicks, cancel_clicks, open_clicks, current_style):
    """Toggle modal visibility."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return {"display": "block"}
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "open-api-modal":
        return {"display": "block"}
    elif button_id in ["save-api-keys", "cancel-api-keys"]:
        return {"display": "none"}
    
    return current_style or {"display": "block"}


@app.callback(
    [Output("api-keys-store", "data"),
     Output("use-sample-data-store", "data")],
    [Input("save-api-keys", "n_clicks"),
     Input("cancel-api-keys", "n_clicks")],
    [State("api-key-inegi", "value"),
     State("api-key-twitter", "value"),
     State("api-key-facebook", "value"),
     State("api-key-reddit", "value"),
     State("api-key-newsapi", "value")]
)
def save_api_keys(save_clicks, cancel_clicks, inegi, twitter, facebook, reddit, newsapi):
    """Save API keys for INEGI, Twitter, Facebook, Reddit, and NewsAPI, and determine data mode."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return {}, True
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "cancel-api-keys":
        api_client.set_sample_mode(True)
        return {}, True
    
    if button_id == "save-api-keys":
        keys = {name: value for name, value in [
            ("inegi", inegi),
            ("twitter", twitter),
            ("facebook", facebook),
            ("reddit", reddit),
            ("newsapi", newsapi)
        ] if value}
        
        api_client.set_api_keys(keys)
        use_sample = len(keys) == 0
        api_client.set_sample_mode(use_sample)
        
        return keys, use_sample
    
    return {}, True


@app.callback(
    Output("data-mode-indicator", "children"),
    [Input("use-sample-data-store", "data"),
     Input("api-keys-store", "data")]
)
def update_data_mode_indicator(use_sample, api_keys):
    """Update the data mode indicator."""
    if use_sample:
        return "🎭 Modo: Datos de Muestra"
    else:
        platforms = list(api_keys.keys()) if api_keys else []
        if platforms:
            return f"✅ Modo: Datos Reales ({', '.join(platforms)})"
        return "🎭 Modo: Datos de Muestra"


@app.callback(
    Output("kpi-cards", "children"),
    [Input("update-button", "n_clicks")],
    [State("entidad-dropdown", "value"),
     State("morbilidad-dropdown", "value")]
)
def update_kpis(n_clicks, entidad, morbilidad):
    """Update KPI cards."""
    try:
        data = api_client.get_kpis({"entidad": entidad, "morbilidad_id": int(morbilidad)})
        kpis = data.get("kpis", [{}])[0]
        
        cards = []
        kpi_configs = [
            ("casos_totales", "📊 Casos Totales", COLORS['info'], "↑ 8%"),
            ("casos_activos", "🔴 Casos Activos", COLORS['warning'], "↑ 12%"),
            ("defunciones_totales", "💔 Defunciones", COLORS['danger'], "↑ 3%")
        ]
        
        for key, title, color, change in kpi_configs:
            value = kpis.get(key, 0)
            cards.append(
                html.Div(
                    style={
                        'background': 'white',
                        'borderRadius': '15px',
                        'padding': '25px',
                        'boxShadow': '0 10px 30px rgba(0, 0, 0, 0.1)',
                        'position': 'relative',
                        'overflow': 'hidden'
                    },
                    children=[
                        html.Div(style={
                            'position': 'absolute',
                            'top': '0',
                            'left': '0',
                            'right': '0',
                            'height': '4px',
                            'background': f'linear-gradient(90deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)'
                        }),
                        html.H4(title, style={'color': COLORS['text'], 'fontSize': '0.95rem', 'fontWeight': '600', 'margin': '0 0 10px 0', 'textTransform': 'uppercase'}),
                        html.H2(f"{value:,}", style={
                            'fontSize': '2.5rem',
                            'fontWeight': '700',
                            'margin': '10px 0',
                            'background': f'linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["secondary"]} 100%)',
                            'WebkitBackgroundClip': 'text',
                            'WebkitTextFillColor': 'transparent',
                            'backgroundClip': 'text'
                        }),
                        html.P(change + " vs semana anterior", style={'color': COLORS['success'] if '↑' not in change else COLORS['danger'], 'fontSize': '0.85rem', 'fontWeight': '600', 'margin': '5px 0 0 0'})
                    ]
                )
            )
        
        return cards
    except Exception as e:
        return [html.Div(f"Error al cargar KPIs: {str(e)}")]


@app.callback(
    Output("timeseries-chart", "figure"),
    [Input("update-button", "n_clicks")],
    [State("entidad-dropdown", "value")]
)
def update_timeseries(n_clicks, entidad):
    """Update time series chart."""
    try:
        data = api_client.get_timeseries(entidad=entidad)
        serie_oficial = data.get("serie_oficial", [])
        
        df = pd.DataFrame(serie_oficial)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=df["casos"],
            mode="lines+markers",
            name="Casos confirmados",
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=6, color=COLORS['primary'])
        ))
        
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Número de Casos",
            hovermode="x unified",
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", size=12, color=COLORS['dark']),
            margin=dict(l=50, r=50, t=20, b=50),
            xaxis=dict(showgrid=True, gridcolor='#e0e0e0'),
            yaxis=dict(showgrid=True, gridcolor='#e0e0e0')
        )
        
        return fig
    except Exception as e:
        return go.Figure()


@app.callback(
    Output("sentiment-chart", "figure"),
    [Input("update-button", "n_clicks")],
    [State("entidad-dropdown", "value")]
)
def update_sentiment(n_clicks, entidad):
    """Update sentiment chart."""
    try:
        data = api_client.get_timeseries(entidad=entidad)
        menciones = data.get("serie_social", {}).get("menciones", [])
        
        df = pd.DataFrame(menciones)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df["fecha"],
            y=df["conteo"],
            name="Menciones",
            marker_color=COLORS['success'],
            yaxis="y"
        ))
        
        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=df["sentimiento"],
            name="Sentimiento",
            line=dict(color=COLORS['danger'], width=3),
            yaxis="y2"
        ))
        
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis=dict(title="Menciones", side="left", showgrid=True, gridcolor='#e0e0e0'),
            yaxis2=dict(
                title="Sentimiento",
                overlaying="y",
                side="right",
                range=[-1, 1],
                showgrid=False
            ),
            hovermode="x unified",
            plot_bgcolor='#f8f9fa',
            paper_bgcolor='white',
            font=dict(family="'Segoe UI', Tahoma, Geneva, Verdana, sans-serif", size=12, color=COLORS['dark']),
            margin=dict(l=50, r=50, t=20, b=50)
        )
        
        return fig
    except Exception as e:
        return go.Figure()


@app.callback(
    Output("alerts-container", "children"),
    [Input("update-button", "n_clicks")]
)
def update_alerts(n_clicks):
    """Update alerts list."""
    try:
        data = api_client.get_alerts()
        alertas = data.get("alertas", [])
        
        if not alertas:
            return html.Div(
                "✅ No hay alertas activas en este momento",
                style={'color': COLORS['success'], 'fontSize': '1rem', 'padding': '20px', 'textAlign': 'center'}
            )
        
        alerts_divs = []
        for alerta in alertas:
            alert_div = html.Div(
                style={
                    'background': 'linear-gradient(135deg, #fff3cd 0%, #ffe8a1 100%)',
                    'borderLeft': f'5px solid {COLORS["warning"]}',
                    'borderRadius': '10px',
                    'padding': '20px',
                    'marginBottom': '15px'
                },
                children=[
                    html.H4(
                        f"⚠️ {alerta.get('tipo', 'Alerta').replace('_', ' ').title()}",
                        style={'color': COLORS['warning'], 'fontSize': '1.1rem', 'fontWeight': '600', 'margin': '0 0 10px 0'}
                    ),
                    html.P(
                        f"Regla: {alerta.get('regla', 'N/A')} | Estado: {alerta.get('estado', 'N/A')}",
                        style={'color': COLORS['text'], 'margin': '5px 0', 'fontSize': '0.9rem'}
                    ),
                    html.P(
                        f"Creada: {alerta.get('created_at', 'N/A')}",
                        style={'color': COLORS['text'], 'fontSize': '0.85rem', 'margin': '5px 0'}
                    )
                ]
            )
            alerts_divs.append(alert_div)
        
        return alerts_divs
    except Exception as e:
        return html.Div(
            "❌ Error al cargar alertas",
            style={'color': COLORS['danger'], 'fontSize': '1rem', 'padding': '20px', 'textAlign': 'center'}
        )


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
