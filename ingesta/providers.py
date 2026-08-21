"""Provider registry and credential validation.

Every data source Episcopio can talk to is declared here once, together with
the credential fields it needs and a *live* validator that proves the supplied
credential actually works before the pipeline tries to use it.

Design rules:

* Endpoints are hard-coded constants — a user-supplied value never determines
  which host we call, so there is no SSRF surface.
* Credentials go in headers (or an auth tuple) wherever the upstream API allows
  it, so they do not end up in proxy/access logs as query strings.
* Nothing in this module ever logs a raw credential; use :func:`mask` instead.
* Every request has an explicit timeout — an unbounded call would pin a worker.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

VALIDATION_TIMEOUT = 10
USER_AGENT = "episcopio/1.1 (+https://github.com/PedroRgz/Episcopio)"

OFICIAL = "oficial"
SOCIAL = "social"


def mask(value: Optional[str]) -> str:
    """Render a credential safely for logs and UI.

    Short values are fully redacted so a 6-character token is not effectively
    disclosed by showing its first and last characters.
    """
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return f"{value[:3]}{'•' * 6}{value[-3:]}"


@dataclass(frozen=True)
class CredentialField:
    """One input the user has to provide for a provider."""
    name: str
    label: str
    placeholder: str = ""
    required: bool = True
    secret: bool = True


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of checking one provider's credentials."""
    ok: bool
    status: str  # "ok" | "invalid" | "unreachable" | "missing"
    message: str

    @property
    def usable(self) -> bool:
        return self.ok


@dataclass(frozen=True)
class Provider:
    """A data source Episcopio can ingest from."""
    id: str
    label: str
    kind: str
    description: str
    doc_url: str
    fields: Tuple[CredentialField, ...] = field(default_factory=tuple)
    validator: Optional[Callable[[Dict[str, str]], ValidationResult]] = None

    @property
    def needs_credentials(self) -> bool:
        return bool(self.fields)

    def missing_fields(self, creds: Dict[str, str]) -> List[str]:
        """Names of required fields the user has not filled in."""
        return [f.name for f in self.fields if f.required and not (creds.get(f.name) or "").strip()]

    def validate(self, creds: Dict[str, str]) -> ValidationResult:
        """Check the supplied credentials against the live upstream API."""
        if not self.needs_credentials:
            return ValidationResult(True, "ok", "Fuente pública, no requiere credenciales.")

        missing = self.missing_fields(creds)
        if missing:
            labels = [f.label for f in self.fields if f.name in missing]
            return ValidationResult(False, "missing", "Falta: " + ", ".join(labels))

        if self.validator is None:
            return ValidationResult(True, "ok", "Credenciales registradas.")

        try:
            return self.validator(creds)
        except requests.Timeout:
            return ValidationResult(False, "unreachable", "Tiempo de espera agotado al contactar la API.")
        except requests.RequestException as exc:
            # Never interpolate the credential dict into the message.
            logger.warning("Validación de %s falló: %s", self.id, type(exc).__name__)
            return ValidationResult(False, "unreachable", "No fue posible contactar la API.")


def _classify(response: requests.Response, provider_label: str) -> ValidationResult:
    """Turn an HTTP status into a user-facing validation result."""
    if response.status_code in (200, 201, 204):
        return ValidationResult(True, "ok", f"Conectado a {provider_label}.")
    if response.status_code in (401, 403):
        return ValidationResult(False, "invalid", "Credenciales rechazadas por la API.")
    if response.status_code == 429:
        return ValidationResult(False, "unreachable", "Límite de peticiones alcanzado; intente más tarde.")
    return ValidationResult(
        False, "unreachable", f"La API respondió con estado {response.status_code}."
    )


# --------------------------------------------------------------------------
# Validators
# --------------------------------------------------------------------------

def _validate_inegi(creds: Dict[str, str]) -> ValidationResult:
    token = creds["token"].strip()
    # INEGI only accepts the token as a path segment; requests quotes it for us.
    url = (
        "https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/"
        f"INDICATOR/1002000001/es/0700/false/BISE/2.0/{requests.utils.quote(token, safe='')}"
    )
    r = requests.get(
        url,
        params={"type": "json"},
        timeout=VALIDATION_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    return _classify(r, "INEGI")


def _validate_twitter(creds: Dict[str, str]) -> ValidationResult:
    r = requests.get(
        "https://api.twitter.com/2/tweets/search/recent",
        params={"query": "salud lang:es", "max_results": 10},
        headers={
            "Authorization": f"Bearer {creds['bearer_token'].strip()}",
            "User-Agent": USER_AGENT,
        },
        timeout=VALIDATION_TIMEOUT,
    )
    return _classify(r, "X/Twitter")


def _validate_reddit(creds: Dict[str, str]) -> ValidationResult:
    r = requests.post(
        "https://www.reddit.com/api/v1/access_token",
        data={"grant_type": "client_credentials"},
        auth=(creds["client_id"].strip(), creds["client_secret"].strip()),
        headers={"User-Agent": creds.get("user_agent") or USER_AGENT},
        timeout=VALIDATION_TIMEOUT,
    )
    if r.status_code == 200 and "access_token" not in r.text:
        return ValidationResult(False, "invalid", "Reddit no devolvió un token de acceso.")
    return _classify(r, "Reddit")


def _validate_newsapi(creds: Dict[str, str]) -> ValidationResult:
    # NewsAPI accepts the key as a header, which keeps it out of access logs.
    r = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={"country": "mx", "pageSize": 1},
        headers={"X-Api-Key": creds["api_key"].strip(), "User-Agent": USER_AGENT},
        timeout=VALIDATION_TIMEOUT,
    )
    return _classify(r, "NewsAPI")


def _validate_meta_graph(label: str) -> Callable[[Dict[str, str]], ValidationResult]:
    def _validator(creds: Dict[str, str]) -> ValidationResult:
        r = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"fields": "id"},
            headers={
                "Authorization": f"Bearer {creds['access_token'].strip()}",
                "User-Agent": USER_AGENT,
            },
            timeout=VALIDATION_TIMEOUT,
        )
        return _classify(r, label)

    return _validator


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------

PROVIDERS: Tuple[Provider, ...] = (
    Provider(
        id="dge",
        label="DGE / SINAVE",
        kind=OFICIAL,
        description="Datos abiertos de la Dirección General de Epidemiología.",
        doc_url="https://www.gob.mx/salud/documentos/datos-abiertos-152127",
    ),
    Provider(
        id="conacyt",
        label="CONAHCYT COVID-19",
        kind=OFICIAL,
        description="Tablero público de casos COVID-19.",
        doc_url="https://datos.covid-19.conacyt.mx",
    ),
    Provider(
        id="inegi",
        label="INEGI",
        kind=OFICIAL,
        description="Indicadores demográficos para tasas por 100 mil habitantes.",
        doc_url="https://www.inegi.org.mx/servicios/api_indicadores.html",
        fields=(CredentialField("token", "Token INEGI", "Token del API de indicadores"),),
        validator=_validate_inegi,
    ),
    Provider(
        id="twitter",
        label="X / Twitter",
        kind=SOCIAL,
        description="Menciones públicas de síntomas y brotes.",
        doc_url="https://developer.twitter.com/en/docs/twitter-api",
        fields=(CredentialField("bearer_token", "Bearer token", "Bearer token de la API v2"),),
        validator=_validate_twitter,
    ),
    Provider(
        id="reddit",
        label="Reddit",
        kind=SOCIAL,
        description="Discusiones en comunidades de salud.",
        doc_url="https://www.reddit.com/dev/api",
        fields=(
            CredentialField("client_id", "Client ID", "ID de la app de Reddit"),
            CredentialField("client_secret", "Client secret", "Secreto de la app"),
            CredentialField(
                "user_agent", "User agent", "episcopio/1.1", required=False, secret=False
            ),
        ),
        validator=_validate_reddit,
    ),
    Provider(
        id="newsapi",
        label="NewsAPI",
        kind=SOCIAL,
        description="Notas periodísticas sobre brotes y emergencias sanitarias.",
        doc_url="https://newsapi.org/docs",
        fields=(CredentialField("api_key", "API key", "Clave de NewsAPI"),),
        validator=_validate_newsapi,
    ),
    Provider(
        id="facebook",
        label="Facebook",
        kind=SOCIAL,
        description="Publicaciones públicas de páginas de salud.",
        doc_url="https://developers.facebook.com/docs/graph-api",
        fields=(CredentialField("access_token", "Access token", "Token de Graph API"),),
        validator=_validate_meta_graph("Facebook"),
    ),
    Provider(
        id="instagram",
        label="Instagram",
        kind=SOCIAL,
        description="Publicaciones públicas de cuentas de salud.",
        doc_url="https://developers.facebook.com/docs/instagram-api",
        fields=(CredentialField("access_token", "Access token", "Token de Graph API"),),
        validator=_validate_meta_graph("Instagram"),
    ),
)

PROVIDERS_BY_ID: Dict[str, Provider] = {p.id: p for p in PROVIDERS}


def get_provider(provider_id: str) -> Optional[Provider]:
    """Look up a provider, returning ``None`` for an unknown id.

    Callers must treat ``provider_id`` as untrusted input: it arrives from the
    browser, so an unknown id is a normal outcome, not an error condition.
    """
    return PROVIDERS_BY_ID.get(provider_id)


def public_providers() -> List[Provider]:
    """Providers that work with no credentials at all."""
    return [p for p in PROVIDERS if not p.needs_credentials]


def describe_providers() -> List[Dict[str, object]]:
    """Serialise the registry for the UI/API (never includes credentials)."""
    return [
        {
            "id": p.id,
            "label": p.label,
            "kind": p.kind,
            "description": p.description,
            "doc_url": p.doc_url,
            "needs_credentials": p.needs_credentials,
            "fields": [
                {
                    "name": f.name,
                    "label": f.label,
                    "placeholder": f.placeholder,
                    "required": f.required,
                    "secret": f.secret,
                }
                for f in p.fields
            ],
        }
        for p in PROVIDERS
    ]
