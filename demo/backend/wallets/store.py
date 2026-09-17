"""Persistance du module portefeuilles : deux implémentations derrière la même
interface (mémoire pour le mode local et les tests, PostgreSQL pour docker).
Toutes les écritures sont idempotentes ou atomiques (débit tout ou rien)."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

import psycopg
from analytics import db_url

from .models import COMPTE_DEMO, PROVIDERS, SOLDES_INITIAUX, WalletError

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS wallets (
        account_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        balance INTEGER NOT NULL CHECK (balance >= 0),
        PRIMARY KEY (account_id, provider)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id BIGSERIAL PRIMARY KEY,
        ts TIMESTAMPTZ NOT NULL,
        account_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        amount INTEGER NOT NULL,
        balance_after INTEGER NOT NULL,
        ticket_id TEXT,
        line_name TEXT,
        kind TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_wallet_tx_account_ts ON wallet_transactions (account_id, ts)",
]

_TX_COLUMNS = " (ts, account_id, provider, amount, balance_after, ticket_id, line_name, kind)"


class MemoryWalletStore:
    """Store en mémoire : mode local sans PostgreSQL et tests pytest."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._balances: dict[str, int] = {}
        self._transactions: list[dict] = []
        self._next_id = 1
        self._seeded = False

    def _init_si_vide(self) -> None:
        if not self._balances:
            self._balances = dict(SOLDES_INITIAUX)

    def ensure_ready(self) -> None:
        with self._lock:
            self._init_si_vide()

    def balances(self) -> dict[str, int]:
        with self._lock:
            self._init_si_vide()
            return dict(self._balances)

    def history_seeded(self) -> bool:
        return self._seeded

    def insert_history(self, lignes: list[dict]) -> None:
        with self._lock:
            for ligne in lignes:
                self._transactions.append({**ligne, "id": self._next_id, "account_id": COMPTE_DEMO})
                self._next_id += 1
            self._seeded = True

    def debit(self, ticket_id: str, line_name: str, splits: list[dict]) -> list[dict]:
        with self._lock:
            self._init_si_vide()
            # Vérification d'abord, application ensuite : débit tout ou rien.
            for s in splits:
                dispo = self._balances.get(s["provider"], 0)
                if s["amount"] > dispo:
                    raise WalletError(
                        f"Solde insuffisant sur {PROVIDERS[s['provider']]}"
                        f" (disponible : {dispo} F)"
                    )
            detail = []
            now = datetime.now(timezone.utc)
            for s in splits:
                self._balances[s["provider"]] -= s["amount"]
                apres = self._balances[s["provider"]]
                self._transactions.append(
                    {
                        "id": self._next_id,
                        "ts": now,
                        "account_id": COMPTE_DEMO,
                        "provider": s["provider"],
                        "amount": s["amount"],
                        "balance_after": apres,
                        "ticket_id": ticket_id,
                        "line_name": line_name,
                        "kind": "payment",
                    }
                )
                self._next_id += 1
                detail.append(
                    {"provider": s["provider"], "amount": s["amount"], "balance_after": apres}
                )
            return detail

    def reset(self) -> dict[str, int]:
        with self._lock:
            self._balances = dict(SOLDES_INITIAUX)
            return dict(self._balances)

    def topup(self, provider: str, amount: int) -> dict[str, int]:
        with self._lock:
            self._init_si_vide()
            self._balances[provider] = self._balances.get(provider, 0) + amount
            self._transactions.append(
                {
                    "id": self._next_id,
                    "ts": datetime.now(timezone.utc),
                    "account_id": COMPTE_DEMO,
                    "provider": provider,
                    "amount": amount,
                    "balance_after": self._balances[provider],
                    "ticket_id": None,
                    "line_name": None,
                    "kind": "topup",
                }
            )
            self._next_id += 1
            return dict(self._balances)

    def transactions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            tri = sorted(self._transactions, key=lambda t: t["ts"], reverse=True)
            return [{**t, "ts": t["ts"].isoformat()} for t in tri[:limit]]


class PostgresWalletStore:
    """Store PostgreSQL (stack docker) : tables wallets + wallet_transactions."""

    def _connect(self):
        return psycopg.connect(db_url(), connect_timeout=3)

    def ensure_ready(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for stmt in DDL_STATEMENTS:
                    cur.execute(stmt)
                cur.execute("SELECT count(*) FROM wallets WHERE account_id = %s", (COMPTE_DEMO,))
                if cur.fetchone()[0] == 0:
                    cur.executemany(
                        "INSERT INTO wallets (account_id, provider, balance) VALUES (%s, %s, %s)",
                        [(COMPTE_DEMO, p, SOLDES_INITIAUX[p]) for p in SOLDES_INITIAUX],
                    )

    def balances(self) -> dict[str, int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT provider, balance FROM wallets WHERE account_id = %s", (COMPTE_DEMO,)
                )
                out = {r[0]: r[1] for r in cur.fetchall()}
        if not out:
            raise RuntimeError("portefeuilles non initialisés")
        return out

    def history_seeded(self) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM wallet_transactions WHERE kind = 'seed'")
                return cur.fetchone()[0] > 0

    def insert_history(self, lignes: list[dict]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO wallet_transactions" + _TX_COLUMNS + " VALUES"
                    " (%s, %s, %s, %s, %s, %s, %s, 'seed')",
                    [
                        (
                            ligne["ts"],
                            COMPTE_DEMO,
                            ligne["provider"],
                            ligne["amount"],
                            ligne["balance_after"],
                            None,
                            ligne["line_name"],
                        )
                        for ligne in lignes
                    ],
                )

    def debit(self, ticket_id: str, line_name: str, splits: list[dict]) -> list[dict]:
        """Débit atomique : UPDATE ... WHERE balance >= x (tout ou rien), puis
        journalisation dans la même transaction."""
        detail = []
        now = datetime.now(timezone.utc)
        with self._connect() as conn:
            with conn.cursor() as cur:
                for s in splits:
                    cur.execute(
                        "UPDATE wallets SET balance = balance - %s"
                        " WHERE account_id = %s AND provider = %s AND balance >= %s"
                        " RETURNING balance",
                        (s["amount"], COMPTE_DEMO, s["provider"], s["amount"]),
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise WalletError(f"Solde insuffisant sur {PROVIDERS[s['provider']]}")
                    detail.append(
                        {"provider": s["provider"], "amount": s["amount"], "balance_after": row[0]}
                    )
                cur.executemany(
                    "INSERT INTO wallet_transactions" + _TX_COLUMNS + " VALUES"
                    " (%s, %s, %s, %s, %s, %s, %s, 'payment')",
                    [
                        (
                            now,
                            COMPTE_DEMO,
                            d["provider"],
                            d["amount"],
                            d["balance_after"],
                            ticket_id,
                            line_name,
                        )
                        for d in detail
                    ],
                )
        return detail

    def reset(self) -> dict[str, int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                for p, solde in SOLDES_INITIAUX.items():
                    cur.execute(
                        "UPDATE wallets SET balance = %s WHERE account_id = %s AND provider = %s",
                        (solde, COMPTE_DEMO, p),
                    )
        return dict(SOLDES_INITIAUX)

    def topup(self, provider: str, amount: int) -> dict[str, int]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE wallets SET balance = balance + %s"
                    " WHERE account_id = %s AND provider = %s RETURNING balance",
                    (amount, COMPTE_DEMO, provider),
                )
                row = cur.fetchone()
                if row is None:
                    raise WalletError(f"Portefeuille {PROVIDERS[provider]} introuvable")
                cur.execute(
                    "INSERT INTO wallet_transactions" + _TX_COLUMNS + " VALUES"
                    " (%s, %s, %s, %s, %s, %s, %s, 'topup')",
                    (
                        datetime.now(timezone.utc),
                        COMPTE_DEMO,
                        provider,
                        amount,
                        row[0],
                        None,
                        None,
                    ),
                )
        return self.balances()

    def transactions(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, ts, provider, amount, balance_after, ticket_id, line_name, kind"
                    " FROM wallet_transactions WHERE account_id = %s"
                    " ORDER BY ts DESC, id DESC LIMIT %s",
                    (COMPTE_DEMO, limit),
                )
                rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "ts": r[1].isoformat(),
                "provider": r[2],
                "amount": r[3],
                "balance_after": r[4],
                "ticket_id": r[5],
                "line_name": r[6],
                "kind": r[7],
            }
            for r in rows
        ]
