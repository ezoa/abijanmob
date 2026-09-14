"""Analytics décideurs — écriture best-effort dans PostgreSQL (stack docker).

Principe : l'application ne dépend JAMAIS de la base — sans DATABASE_URL (mode
local demo.sh) ou si PostgreSQL est indisponible, elle fonctionne sans analytics
et sans erreur. Voir seed_analytics.py pour l'initialisation des données.
"""

from __future__ import annotations

import os
from datetime import datetime

import psycopg
from routing_engine import MODES

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS ridership_events (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL,
        line_id TEXT NOT NULL,
        line_name TEXT NOT NULL,
        mode TEXT NOT NULL,
        formal BOOLEAN NOT NULL,
        stop_id TEXT NOT NULL,
        stop_name TEXT NOT NULL,
        commune TEXT NOT NULL,
        direction SMALLINT NOT NULL,
        boarded INTEGER NOT NULL,
        alighted INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL,
        ticket_id TEXT NOT NULL,
        line_name TEXT NOT NULL,
        mode TEXT NOT NULL,
        fare INTEGER NOT NULL,
        provider TEXT NOT NULL,
        driver_id TEXT
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_ridership_ts ON ridership_events (ts)",
    "CREATE INDEX IF NOT EXISTS idx_ridership_line ON ridership_events (line_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_ts ON payments (ts)",
]


def db_url() -> str | None:
    return os.environ.get("DATABASE_URL")


def record_payment(ticket: dict, dt: datetime, line: dict | None, stop: dict | None) -> bool:
    """Écrit un paiement (+ la montée associée) en base. Ne lève jamais d'erreur."""
    url = db_url()
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                for stmt in DDL_STATEMENTS:
                    cur.execute(stmt)
                cur.execute(
                    "INSERT INTO payments (ts, ticket_id, line_name, mode, fare, provider, driver_id)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        dt,
                        ticket["ticket_id"],
                        ticket["line_name"],
                        ticket["mode"],
                        ticket["fare"],
                        ticket["provider"],
                        ticket["driver_id"],
                    ),
                )
                if line and stop:
                    cur.execute(
                        "INSERT INTO ridership_events"
                        " (ts, line_id, line_name, mode, formal, stop_id, stop_name, commune,"
                        " direction, boarded, alighted)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, 0)",
                        (
                            dt,
                            line["id"],
                            line["name"],
                            line["mode"],
                            MODES[line["mode"]]["formal"],
                            stop["id"],
                            stop["name"],
                            stop["commune"],
                            0,
                        ),
                    )
            conn.commit()
        return True
    except Exception:  # noqa: BLE001 — l'analytics ne doit jamais casser la démo
        return False
