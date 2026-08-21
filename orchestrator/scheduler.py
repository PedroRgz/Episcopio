"""Scheduler for unattended (server-credential) runs.

The dashboard's "paste your keys" flow is session-scoped and interactive. This
scheduler covers the other half: a deployment that holds its own credentials in
the environment and should keep ingesting on a timer with nobody watching.

It reuses the same pipeline as the dashboard, so both paths share one
implementation of ingest → normalise → analyse.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone

import schedule

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.loader import load_config  # noqa: E402
from core.runs import ERROR, PARTIAL  # noqa: E402
from core.vault import vault  # noqa: E402
from orchestrator.pipeline import execute_run, plan_steps  # noqa: E402
from core.runs import run_registry  # noqa: E402

logging.basicConfig(
    level=os.getenv("EP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("scheduler")

INGEST_INTERVAL_HOURS = int(os.getenv("EP_INGEST_INTERVAL_HOURS", "6"))


# Server-held credentials, mapped from the Secrets object onto provider ids.
def _server_credentials(secrets) -> dict:
    """Collect the credentials this deployment holds in its own environment."""
    mapping = {
        "inegi": {"token": secrets.apis_inegi_token},
        "twitter": {"bearer_token": secrets.apis_twitter_bearer_token},
        "reddit": {
            "client_id": secrets.apis_reddit_client_id,
            "client_secret": secrets.apis_reddit_client_secret,
            "user_agent": secrets.apis_reddit_user_agent,
        },
        "newsapi": {"api_key": secrets.apis_newsapi_key},
        "facebook": {"access_token": secrets.apis_facebook_access_token},
        "instagram": {"access_token": secrets.apis_instagram_access_token},
    }
    return {
        provider: {k: v for k, v in creds.items() if v}
        for provider, creds in mapping.items()
        # Reddit needs both halves; a lone client_id is not a usable credential.
        if any(creds.get(k) for k in creds if k != "user_agent")
    }


def job_pipeline() -> None:
    """Run one full pipeline pass using the deployment's own credentials."""
    logger.info("Iniciando ejecución programada")

    _, _, secrets, _, _ = load_config()
    session_id = vault.create_session()
    try:
        for provider_id, creds in _server_credentials(secrets).items():
            vault.set_credentials(session_id, provider_id, creds)

        connected = vault.connected_providers(session_id)
        logger.info("Fuentes con credenciales: %s", connected or "solo públicas")

        run = run_registry.create(session_id, plan_steps(connected))
        execute_run(session_id, run)

        level = logging.ERROR if run.status == ERROR else (
            logging.WARNING if run.status == PARTIAL else logging.INFO
        )
        logger.log(level, "Ejecución %s: %s", run.status, run.summary)
        for step in run.steps:
            logger.info("  %-14s %-12s %s", step.key, step.status, step.message)
    finally:
        # Credentials live no longer than the run that needed them.
        vault.destroy(session_id)


def main() -> None:
    """Main scheduler loop."""
    logger.info("Episcopio scheduler iniciado (%s)", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    logger.info("Intervalo de ingesta: cada %d horas", INGEST_INTERVAL_HOURS)

    schedule.every(INGEST_INTERVAL_HOURS).hours.do(job_pipeline)

    job_pipeline()  # run once at startup

    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler detenido por el usuario")


if __name__ == "__main__":
    main()
