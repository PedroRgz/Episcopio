"""Social and news ingestion connectors.

Each connector takes the credentials the user supplied for that provider and
makes a real call. A connector without credentials reports ``skipped``; it
never fabricates a result.

Mentions are normalised to a common shape so :mod:`etl.normaliza` can build one
social time series regardless of which platforms are connected:

    {"fecha": "YYYY-MM-DD", "texto": str, "fuente": str, "sentimiento": float}
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import requests

from ingesta.base import ConnectorResult
from ingesta.providers import USER_AGENT

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
MAX_ITEMS = 100

# Health terms used to build queries and to score relevance.
KEYWORDS = (
    "covid", "dengue", "influenza", "sarampión", "sarampion", "síntomas", "sintomas",
    "contagio", "brote", "epidemia", "hospital", "enfermedad", "fiebre", "vacuna",
)

# Small lexicon for the MVP sentiment score. Deliberately transparent and
# dependency-free; a trained classifier is the planned upgrade.
NEGATIVE_TERMS = (
    "muerte", "muertes", "muerto", "grave", "colapso", "saturado", "brote", "emergencia",
    "crisis", "aumento", "peor", "riesgo", "contagio", "miedo", "alarma", "fallecidos",
)
POSITIVE_TERMS = (
    "recuperación", "recuperacion", "mejora", "control", "baja", "disminuye", "vacuna",
    "vacunación", "vacunacion", "alta", "estable", "avance", "prevención", "prevencion",
)

_WORD_RE = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


def clasificar_relevancia(texto: str) -> bool:
    """True when a text plausibly concerns epidemiological monitoring."""
    if not texto:
        return False
    texto_lower = texto.lower()
    return any(keyword in texto_lower for keyword in KEYWORDS)


def analizar_sentimiento(texto: str) -> float:
    """Lexicon sentiment score in ``[-1, 1]``.

    Returns 0.0 for text with no scored terms, which reads as "neutral" rather
    than as a missing value.
    """
    if not texto:
        return 0.0
    words = {w.lower() for w in _WORD_RE.findall(texto)}
    lowered = texto.lower()

    negative = sum(1 for t in NEGATIVE_TERMS if t in words or t in lowered)
    positive = sum(1 for t in POSITIVE_TERMS if t in words or t in lowered)
    total = negative + positive
    if total == 0:
        return 0.0
    return round((positive - negative) / total, 3)


def _mention(fecha: str, texto: str, fuente: str) -> Dict[str, Any]:
    return {
        "fecha": fecha[:10],
        "texto": texto,
        "fuente": fuente,
        "sentimiento": analizar_sentimiento(texto),
    }


def _iso_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def _handle_http_error(source: str, exc: Exception) -> ConnectorResult:
    if isinstance(exc, requests.Timeout):
        return ConnectorResult.unreachable(source, "Tiempo de espera agotado.")
    logger.warning("Ingesta %s falló: %s", source, type(exc).__name__)
    return ConnectorResult.unreachable(source, "No fue posible contactar la API.")


def fetch_twitter(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Search recent public posts on X/Twitter for health terms in Mexico."""
    source = "twitter"
    token = (credentials or {}).get("bearer_token", "").strip()
    if not token:
        return ConnectorResult.skipped(source, "Sin bearer token; fuente omitida.")

    query = "(" + " OR ".join(KEYWORDS[:6]) + ") lang:es -is:retweet"
    try:
        r = requests.get(
            "https://api.twitter.com/2/tweets/search/recent",
            params={"query": query, "max_results": MAX_ITEMS, "tweet.fields": "created_at"},
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return _handle_http_error(source, exc)

    if r.status_code in (401, 403):
        return ConnectorResult.error(source, "Bearer token rechazado por la API.")
    if r.status_code == 429:
        return ConnectorResult.unreachable(source, "Límite de peticiones alcanzado.")
    if r.status_code != 200:
        return ConnectorResult.unreachable(source, f"La API respondió con estado {r.status_code}.")

    try:
        payload = r.json()
    except ValueError:
        return ConnectorResult.error(source, "Respuesta no válida de la API.")

    mentions = [
        _mention(t.get("created_at") or _iso_days_ago(0), t.get("text", ""), source)
        for t in payload.get("data", [])
        if clasificar_relevancia(t.get("text", ""))
    ]
    return ConnectorResult.success(source, len(mentions), f"{len(mentions)} menciones relevantes.", mentions)


def fetch_reddit(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Search health-related discussions on Reddit."""
    source = "reddit"
    creds = credentials or {}
    client_id = creds.get("client_id", "").strip()
    client_secret = creds.get("client_secret", "").strip()
    if not client_id or not client_secret:
        return ConnectorResult.skipped(source, "Sin credenciales de Reddit; fuente omitida.")

    agent = creds.get("user_agent") or USER_AGENT
    try:
        auth = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"User-Agent": agent},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return _handle_http_error(source, exc)

    if auth.status_code in (401, 403):
        return ConnectorResult.error(source, "Credenciales de Reddit rechazadas.")
    if auth.status_code != 200:
        return ConnectorResult.unreachable(source, f"Reddit respondió con estado {auth.status_code}.")

    try:
        access_token = auth.json().get("access_token")
    except ValueError:
        access_token = None
    if not access_token:
        return ConnectorResult.error(source, "Reddit no devolvió un token de acceso.")

    try:
        r = requests.get(
            "https://oauth.reddit.com/search",
            params={"q": " OR ".join(KEYWORDS[:5]), "limit": MAX_ITEMS, "sort": "new"},
            headers={"Authorization": f"Bearer {access_token}", "User-Agent": agent},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return _handle_http_error(source, exc)

    if r.status_code != 200:
        return ConnectorResult.unreachable(source, f"Reddit respondió con estado {r.status_code}.")

    try:
        children = r.json().get("data", {}).get("children", [])
    except ValueError:
        return ConnectorResult.error(source, "Respuesta no válida de Reddit.")

    mentions = []
    for child in children:
        data = child.get("data", {})
        texto = f"{data.get('title', '')} {data.get('selftext', '')}".strip()
        if not clasificar_relevancia(texto):
            continue
        created = data.get("created_utc")
        fecha = (
            datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")
            if isinstance(created, (int, float))
            else _iso_days_ago(0)
        )
        mentions.append(_mention(fecha, texto, source))

    return ConnectorResult.success(source, len(mentions), f"{len(mentions)} discusiones relevantes.", mentions)


def fetch_news(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Fetch Mexican health news through NewsAPI."""
    source = "newsapi"
    api_key = (credentials or {}).get("api_key", "").strip()
    if not api_key:
        return ConnectorResult.skipped(source, "Sin API key de NewsAPI; fuente omitida.")

    try:
        r = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": " OR ".join(KEYWORDS[:6]),
                "language": "es",
                "from": _iso_days_ago(14),
                "sortBy": "publishedAt",
                "pageSize": MAX_ITEMS,
            },
            # Header auth keeps the key out of access logs.
            headers={"X-Api-Key": api_key, "User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return _handle_http_error(source, exc)

    if r.status_code in (401, 403):
        return ConnectorResult.error(source, "API key de NewsAPI rechazada.")
    if r.status_code == 429:
        return ConnectorResult.unreachable(source, "Límite de peticiones alcanzado.")
    if r.status_code != 200:
        return ConnectorResult.unreachable(source, f"NewsAPI respondió con estado {r.status_code}.")

    try:
        articles = r.json().get("articles", [])
    except ValueError:
        return ConnectorResult.error(source, "Respuesta no válida de NewsAPI.")

    mentions = []
    for article in articles:
        texto = f"{article.get('title', '')} {article.get('description') or ''}".strip()
        if not clasificar_relevancia(texto):
            continue
        mentions.append(_mention(article.get("publishedAt") or _iso_days_ago(0), texto, source))

    return ConnectorResult.success(source, len(mentions), f"{len(mentions)} notas relevantes.", mentions)


def _fetch_meta_feed(source: str, credentials: Optional[Dict[str, str]], label: str) -> ConnectorResult:
    """Shared Graph API path for Facebook and Instagram."""
    token = (credentials or {}).get("access_token", "").strip()
    if not token:
        return ConnectorResult.skipped(source, f"Sin access token; {label} omitido.")

    try:
        r = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id,name"},
            headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
    except requests.RequestException as exc:
        return _handle_http_error(source, exc)

    if r.status_code in (401, 403):
        return ConnectorResult.error(source, f"Access token de {label} rechazado.")
    if r.status_code != 200:
        return ConnectorResult.unreachable(source, f"{label} respondió con estado {r.status_code}.")

    # Graph API only exposes posts for pages the token is granted on, and the
    # page selection is a product decision that is not settled yet. The
    # connector authenticates and reports honestly instead of inventing data.
    return ConnectorResult(
        source=source,
        ok=False,
        status="skipped",
        message=(
            f"Token de {label} válido. Falta configurar las páginas a monitorear "
            "para habilitar la ingesta de publicaciones."
        ),
    )


def fetch_facebook(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Authenticate against the Graph API for Facebook page monitoring."""
    return _fetch_meta_feed("facebook", credentials, "Facebook")


def fetch_instagram(credentials: Optional[Dict[str, str]] = None) -> ConnectorResult:
    """Authenticate against the Graph API for Instagram account monitoring."""
    return _fetch_meta_feed("instagram", credentials, "Instagram")
