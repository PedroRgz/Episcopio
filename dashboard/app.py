"""Episcopio Dashboard - Dash/Plotly application."""
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
from datetime import datetime, timedelta
import pandas as pd

from services.api_client import api_client

# Initialize Dash app
app = dash.Dash(
    __name__,
    title="Episcopio - Monitoreo Epidemiológico",
    suppress_callback_exceptions=True
)

# App layout
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Episcopio", style={"color": "#2c3e50", "margin": "0"}),
        html.P(
            "Tomando el pulso epidemiológico de México",
            style={"color": "#7f8c8d", "margin": "5px 0"}
        )
    ], style={
        "backgroundColor": "#ecf0f1",
        "padding": "20px",
        "borderBottom": "3px solid #3498db"
    }),
    
    # Main content
    html.Div([
        # Filters section
        html.Div([
            html.H3("Filtros"),
            html.Div([
                html.Label("Entidad Federativa:"),
                dcc.Dropdown(
                    id="entidad-dropdown",
                    options=[
                        {"label": "Yucatán", "value": "31"},
                        {"label": "Quintana Roo", "value": "23"},
                        {"label": "Campeche", "value": "04"},
                        {"label": "Ciudad de México", "value": "09"},
                        {"label": "Nuevo León", "value": "19"}
                    ],
                    value="31",
                    style={"width": "100%", "marginBottom": "10px"}
                )
            ]),
            html.Div([
                html.Label("Morbilidad:"),
                dcc.Dropdown(
                    id="morbilidad-dropdown",
                    options=[
                        {"label": "COVID-19", "value": "1"},
                        {"label": "Dengue", "value": "2"},
                        {"label": "Influenza", "value": "3"}
                    ],
                    value="1",
                    style={"width": "100%", "marginBottom": "10px"}
                )
            ]),
            html.Button(
                "Actualizar",
                id="update-button",
                n_clicks=0,
                style={
                    "backgroundColor": "#3498db",
                    "color": "white",
                    "border": "none",
                    "padding": "10px 20px",
                    "borderRadius": "5px",
                    "cursor": "pointer",
                    "width": "100%"
                }
            )
        ], style={
            "padding": "20px",
            "backgroundColor": "#f8f9fa",
            "borderRadius": "5px",
            "marginBottom": "20px"
        }),
        
        # KPI Cards
        html.Div(id="kpi-cards", children=[
            html.Div([
                html.Div([
                    html.H4("Casos Totales", style={"color": "#7f8c8d"}),
                    html.H2("12,500", style={"color": "#3498db", "margin": "10px 0"}),
                    html.P("↑ 8% vs semana anterior", style={"color": "#27ae60", "fontSize": "12px"})
                ], style={
                    "backgroundColor": "white",
                    "padding": "20px",
                    "borderRadius": "5px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "flex": "1",
                    "margin": "0 10px"
                }),
                html.Div([
                    html.H4("Casos Activos", style={"color": "#7f8c8d"}),
                    html.H2("450", style={"color": "#e67e22", "margin": "10px 0"}),
                    html.P("↑ 12% vs semana anterior", style={"color": "#e74c3c", "fontSize": "12px"})
                ], style={
                    "backgroundColor": "white",
                    "padding": "20px",
                    "borderRadius": "5px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "flex": "1",
                    "margin": "0 10px"
                }),
                html.Div([
                    html.H4("Defunciones", style={"color": "#7f8c8d"}),
                    html.H2("350", style={"color": "#e74c3c", "margin": "10px 0"}),
                    html.P("↑ 3% vs semana anterior", style={"color": "#e74c3c", "fontSize": "12px"})
                ], style={
                    "backgroundColor": "white",
                    "padding": "20px",
                    "borderRadius": "5px",
                    "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "flex": "1",
                    "margin": "0 10px"
                })
            ], style={"display": "flex", "marginBottom": "20px"})
        ]),
        
        # Charts section
        html.Div([
            # Time series chart
            html.Div([
                html.H3("Serie Temporal - Casos Confirmados"),
                dcc.Graph(id="timeseries-chart")
            ], style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "5px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                "marginBottom": "20px"
            }),
            
            # Sentiment chart
            html.Div([
                html.H3("Análisis de Sentimiento en Redes Sociales"),
                dcc.Graph(id="sentiment-chart")
            ], style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "5px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
                "marginBottom": "20px"
            }),
            
            # Alerts section
            html.Div([
                html.H3("Alertas Activas"),
                html.Div(id="alerts-container")
            ], style={
                "backgroundColor": "white",
                "padding": "20px",
                "borderRadius": "5px",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)"
            })
        ])
    ], style={"padding": "20px", "maxWidth": "1200px", "margin": "0 auto"}),
    
    # Footer
    html.Div([
        html.P(
            "© 2025 Episcopio - Monitoreo Epidemiológico | Datos actualizados cada 6 horas",
            style={"textAlign": "center", "color": "#7f8c8d", "margin": "0"}
        )
    ], style={
        "backgroundColor": "#ecf0f1",
        "padding": "15px",
        "marginTop": "30px"
    })
])


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
            line=dict(color="#3498db", width=3)
        ))
        
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Casos",
            hovermode="x unified",
            plot_bgcolor="#f8f9fa",
            margin=dict(l=40, r=40, t=10, b=40)
        )
        
        return fig
    except Exception as e:
        # Return empty figure on error
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
            marker_color="#2ecc71",
            yaxis="y"
        ))
        
        fig.add_trace(go.Scatter(
            x=df["fecha"],
            y=df["sentimiento"],
            name="Sentimiento",
            line=dict(color="#e74c3c", width=3),
            yaxis="y2"
        ))
        
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis=dict(title="Menciones", side="left"),
            yaxis2=dict(
                title="Sentimiento",
                overlaying="y",
                side="right",
                range=[-1, 1]
            ),
            hovermode="x unified",
            plot_bgcolor="#f8f9fa",
            margin=dict(l=40, r=40, t=10, b=40)
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
            return html.P("No hay alertas activas", style={"color": "#27ae60"})
        
        alerts_divs = []
        for alerta in alertas:
            alert_div = html.Div([
                html.H4(
                    f"⚠️ {alerta.get('tipo', 'Alerta').replace('_', ' ').title()}",
                    style={"color": "#e67e22", "margin": "0 0 10px 0"}
                ),
                html.P(
                    f"Regla: {alerta.get('regla', 'N/A')} | Estado: {alerta.get('estado', 'N/A')}",
                    style={"margin": "5px 0", "fontSize": "14px"}
                ),
                html.P(
                    f"Creada: {alerta.get('created_at', 'N/A')}",
                    style={"color": "#7f8c8d", "fontSize": "12px", "margin": "5px 0"}
                )
            ], style={
                "padding": "15px",
                "backgroundColor": "#fff3cd",
                "borderLeft": "4px solid #e67e22",
                "borderRadius": "3px",
                "marginBottom": "10px"
            })
            alerts_divs.append(alert_div)
        
        return alerts_divs
    except Exception as e:
        return html.P("Error al cargar alertas", style={"color": "#e74c3c"})


if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=8050)
