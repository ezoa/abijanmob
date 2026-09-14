"""Initialise la base analytics : 14 jours de fréquentation + paiements simulés.

Idempotent : ne génère rien si des événements existent déjà. Données SYNTHÉTIQUES
(pics d'heure de pointe, semaine/week-end) destinées aux tableaux de bord décideurs
(Metabase) — sans aucune donnée personnelle.

Exécution (service docker db-init) :
  DATABASE_URL=postgresql://abidjanmob:abidjanmob@db:5432/abidjanmob python seed_analytics.py
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import psycopg

SEED = 42
DAYS = 14
OPEN_HOUR, CLOSE_HOUR = 6, 21  # heures de service
DETOUR = 1.15
SPEED = {"sotra": 20.0, "bateau": 14.0, "gbaka": 18.0, "woro": 24.0}
FORMAL = {"sotra": True, "bateau": True, "gbaka": False, "woro": False}
BASE_BOARD = {"sotra": 18, "bateau": 8, "gbaka": 6, "woro": 4}
ADOPTION = {"sotra": 0.22, "bateau": 0.18, "gbaka": 0.10, "woro": 0.08}
PROVIDERS = [("Wave", 0.45), ("Orange Money", 0.35), ("MTN MoMo", 0.12), ("Moov Money", 0.08)]

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


def corpus_path() -> Path:
    p = Path(os.environ.get("CORPUS_PATH", ""))
    if str(p) and p.exists():
        return p
    return Path(__file__).resolve().parents[2] / "data" / "corpus" / "network.json"


def haversine_m(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def demand(hour: int, weekday: bool) -> float:
    """Courbe de demande : double pic en semaine, journée plate le week-end."""
    if not weekday:
        return 0.5 if 10 <= hour <= 19 else 0.35
    if hour in (7, 8):
        return 2.6
    if hour in (17, 18):
        return 2.2
    if hour in (6, 9, 16, 19):
        return 1.35
    return 0.9


def pick_provider() -> str:
    r = random.random()
    acc = 0.0
    for name, p in PROVIDERS:
        acc += p
        if r <= acc:
            return name
    return "Wave"


def connect(url: str):
    for attempt in range(30):
        try:
            return psycopg.connect(url, connect_timeout=3)
        except Exception:  # noqa: BLE001 — attend le démarrage de PostgreSQL
            time.sleep(2)
    raise SystemExit("PostgreSQL inaccessible après 60 s")


def main() -> None:
    random.seed(SEED)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL non défini")

    data = json.loads(corpus_path().read_text(encoding="utf-8"))
    stops = {s["id"]: s for s in data["stops"]}
    drivers_by_line = {d["line_id"]: d["id"] for d in data["drivers"]}

    conn = connect(url)
    with conn.cursor() as cur:
        for stmt in DDL_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
        cur.execute("SELECT count(*) FROM ridership_events")
        if cur.fetchone()[0] > 0:
            print("Base déjà initialisée — rien à faire.", flush=True)
            return

        end = datetime(2026, 9, 14, CLOSE_HOUR, 0)
        events = []
        payments = []

        for ln in data["lines"]:
            n = len(ln["stops"])
            speed = SPEED[ln["mode"]]
            cum = [0.0]
            for a, b in zip(ln["stops"], ln["stops"][1:]):
                d = haversine_m(stops[a], stops[b]) * DETOUR
                cum.append(cum[-1] + d / 1000.0 / speed * 60.0)
            total_ride = cum[-1]
            headway = ln["headway_min"]

            for day_offset in range(DAYS):
                day = (end - timedelta(days=DAYS - day_offset)).date()
                weekday = day.weekday() < 5
                for direction in (0, 1):
                    t = random.uniform(0, headway)
                    while t < (CLOSE_HOUR - OPEN_HOUR) * 60:
                        for k in range(n):
                            stop = stops[ln["stops"][k]]
                            pos = k / (n - 1) if n > 1 else 0.0
                            pos_dir = pos if direction == 0 else 1.0 - pos
                            arr_min = t + (cum[k] if direction == 0 else total_ride - cum[k])
                            ts = datetime(day.year, day.month, day.day, OPEN_HOUR) + timedelta(
                                minutes=arr_min
                            )
                            dem = demand(ts.hour, weekday)
                            base = BASE_BOARD[ln["mode"]]
                            # montées côté résidentiel du parcours, descentes côté pôle d'emploi
                            boarded = round(
                                base * dem * (1.7 - 1.2 * pos_dir) * random.uniform(0.7, 1.3)
                            )
                            alighted = round(
                                base * dem * (0.3 + 1.3 * pos_dir) * 0.8 * random.uniform(0.6, 1.4)
                            )
                            boarded = max(0, boarded)
                            alighted = max(0, alighted)
                            if boarded == 0 and alighted == 0:
                                continue
                            events.append(
                                (
                                    ts,
                                    ln["id"],
                                    ln["name"],
                                    ln["mode"],
                                    FORMAL[ln["mode"]],
                                    stop["id"],
                                    stop["name"],
                                    stop["commune"],
                                    direction,
                                    boarded,
                                    alighted,
                                )
                            )
                            n_pay = min(
                                boarded,
                                round(boarded * ADOPTION[ln["mode"]] * random.uniform(0.5, 1.5)),
                            )
                            for _ in range(max(0, n_pay)):
                                # Numéro SÉQUENTIEL (pas aléatoire) : l'index unique
                                # uq_payments_ticket_id posé par le module financier
                                # (finance/store.py) exclut tout doublon de ticket_id.
                                payments.append(
                                    (
                                        ts,
                                        f"ABJ-{len(payments) + 1:06X}",
                                        ln["name"],
                                        ln["mode"],
                                        ln["fare"],
                                        pick_provider(),
                                        drivers_by_line.get(ln["id"]),
                                    )
                                )
                        t += headway

        with cur.copy(
            "COPY ridership_events (ts, line_id, line_name, mode, formal, stop_id, stop_name,"
            " commune, direction, boarded, alighted) FROM STDIN"
        ) as cp:
            for row in events:
                cp.write_row(row)
        with cur.copy(
            "COPY payments (ts, ticket_id, line_name, mode, fare, provider, driver_id) FROM STDIN"
        ) as cp:
            for row in payments:
                cp.write_row(row)
    conn.commit()
    print(
        f"Base initialisée : {len(events)} événements de fréquentation,"
        f" {len(payments)} paiements ({DAYS} jours).",
        flush=True,
    )
    sys.stdout.flush()


if __name__ == "__main__":
    main()
