"""Persistance du module financier — deux implémentations derrière la même interface.

- `PostgresFinanceStore` (stack docker, DATABASE_URL présent) : tables dédiées +
  évolution IDEMPOTENTE de `payments` (CREATE TABLE IF NOT EXISTS /
  ADD COLUMN IF NOT EXISTS) — la table existante (~151 k lignes seedées) continue
  de fonctionner ; les colonnes NOT NULL sont ajoutées avec des DEFAULT sûrs.
- `MemoryFinanceStore` (mode local demo.sh sans base, et tests pytest) : mêmes
  opérations sur des listes en mémoire.

Le moteur (tax_engine, documents) est pur : testable sans aucune base.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row

from .models import CustomerDocument, DailyClosure, DriverExpense, DriverStub

CONNECT_TIMEOUT = 3

# --------------------------------------------------------------------------- DDL

DDL_STATEMENTS = [
    # --- évolution de la table payments (existante, ne pas casser) ---
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS transaction_id TEXT",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'paid'",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS gross_amount INTEGER",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'XOF'",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS provider_key TEXT",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS line_id TEXT",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS stop_id TEXT",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ",
    # --- documents clients ---
    """
    CREATE TABLE IF NOT EXISTS customer_documents (
        id BIGSERIAL PRIMARY KEY,
        document_number TEXT NOT NULL,
        document_type TEXT NOT NULL,
        payment_id TEXT NOT NULL,
        ticket_id TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        issuer_name TEXT NOT NULL,
        issuer_identifier TEXT NOT NULL,
        customer_name TEXT NOT NULL,
        customer_phone_masked TEXT,
        line_name TEXT NOT NULL,
        origin_name TEXT,
        destination_name TEXT,
        commune TEXT,
        gross_amount INTEGER NOT NULL,
        tax_amount INTEGER NOT NULL,
        net_amount INTEGER NOT NULL,
        currency TEXT NOT NULL DEFAULT 'XOF',
        payment_provider TEXT NOT NULL,
        fne_status TEXT NOT NULL DEFAULT 'not_certified_demo',
        fne_reference TEXT,
        verification_token TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL,
        cancelled_at TIMESTAMPTZ
    )
    """,
    # --- souches conducteur ---
    """
    CREATE TABLE IF NOT EXISTS driver_stubs (
        id BIGSERIAL PRIMARY KEY,
        stub_number TEXT NOT NULL,
        payment_id TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        ticket_id TEXT NOT NULL,
        driver_id TEXT NOT NULL,
        line_name TEXT NOT NULL,
        provider TEXT NOT NULL,
        gross_amount INTEGER NOT NULL,
        payment_fee INTEGER NOT NULL,
        platform_fee INTEGER NOT NULL,
        tax_provision INTEGER NOT NULL,
        net_amount INTEGER NOT NULL,
        settlement_status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    # --- dépenses conducteur ---
    """
    CREATE TABLE IF NOT EXISTS driver_expenses (
        id BIGSERIAL PRIMARY KEY,
        driver_id TEXT NOT NULL,
        expense_date DATE NOT NULL,
        category TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        amount INTEGER NOT NULL,
        currency TEXT NOT NULL DEFAULT 'XOF',
        receipt_reference TEXT,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    # --- moteur fiscal (règles configurables et versionnées) ---
    """
    CREATE TABLE IF NOT EXISTS tax_rules (
        id BIGSERIAL PRIMARY KEY,
        code TEXT NOT NULL,
        label TEXT NOT NULL,
        authority_type TEXT NOT NULL,
        authority_name TEXT NOT NULL,
        commune TEXT,
        vehicle_category TEXT,
        operator_regime TEXT,
        calculation_type TEXT NOT NULL,
        tax_target TEXT NOT NULL DEFAULT 'operator',
        rate NUMERIC(6,3) NOT NULL DEFAULT 0,
        fixed_amount INTEGER NOT NULL DEFAULT 0,
        frequency TEXT NOT NULL,
        effective_from DATE,
        effective_to DATE,
        legal_reference TEXT,
        is_official BOOLEAN NOT NULL DEFAULT FALSE,
        enabled BOOLEAN NOT NULL DEFAULT TRUE
    )
    """,
    # --- calculs fiscaux par paiement ---
    """
    CREATE TABLE IF NOT EXISTS tax_calculations (
        id BIGSERIAL PRIMARY KEY,
        payment_id TEXT NOT NULL,
        tax_rule_id BIGINT NOT NULL,
        calculation_base INTEGER NOT NULL,
        calculated_amount INTEGER NOT NULL,
        calculation_kind TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    # --- clôtures journalières ---
    """
    CREATE TABLE IF NOT EXISTS daily_closures (
        id BIGSERIAL PRIMARY KEY,
        driver_id TEXT NOT NULL,
        closure_number TEXT NOT NULL,
        closure_date DATE NOT NULL,
        gross_revenue INTEGER NOT NULL,
        fees INTEGER NOT NULL,
        tax_provisions INTEGER NOT NULL,
        expenses INTEGER NOT NULL,
        estimated_net_income INTEGER NOT NULL,
        payment_count INTEGER NOT NULL,
        created_at TIMESTAMPTZ NOT NULL
    )
    """,
    # --- séquences de numérotation ---
    """
    CREATE TABLE IF NOT EXISTS finance_sequences (
        name TEXT PRIMARY KEY,
        value BIGINT NOT NULL DEFAULT 0
    )
    """,
    # --- index ---
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_documents_number"
    " ON customer_documents (document_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_customer_documents_payment"
    " ON customer_documents (payment_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_stubs_number ON driver_stubs (stub_number)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_driver_stubs_payment ON driver_stubs (payment_id)",
    "CREATE INDEX IF NOT EXISTS idx_driver_stubs_driver_date"
    " ON driver_stubs (driver_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_driver_expenses_driver ON driver_expenses (driver_id)",
    "CREATE INDEX IF NOT EXISTS idx_tax_calculations_payment ON tax_calculations (payment_id)",
    "CREATE INDEX IF NOT EXISTS idx_tax_calculations_rule ON tax_calculations (tax_rule_id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_daily_closures_driver_date"
    " ON daily_closures (driver_id, closure_date)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_tax_rules_code ON tax_rules (code)",
    "CREATE INDEX IF NOT EXISTS idx_payments_transaction ON payments (transaction_id)",
]

# Déduplication des ticket_id seedés (le seed historique tirait 6 caractères hexa
# aléatoires → ~695 doublons sur 151 k lignes par paradoxe des anniversaires).
# On renomme les doublons en hexa de l'id de ligne, complété à 8 caractères —
# longueur DISJOINTE de l'espace aléatoire à 6 caractères (aucune collision
# possible), unique par construction — AVANT de poser la contrainte d'unicité
# exigée par le cahier des charges. Aucune autre donnée n'est modifiée.
DEDUP_TICKETS_SQL = """
UPDATE payments SET ticket_id = 'ABJ-' || lpad(to_hex(payments.id), 8, '0')
WHERE id IN (
    SELECT id FROM (
        SELECT id, row_number() OVER (PARTITION BY ticket_id ORDER BY id) AS rn
        FROM payments
    ) t WHERE t.rn > 1
)
"""

# Contrainte d'unicité sur l'identifiant métier (cahier des charges).
UNIQUE_TICKET_INDEX_SQL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_ticket_id ON payments (ticket_id)"
)

STUBS_PAGE_LIMIT = 500

EMPTY_AGG = {
    "count": 0,
    "gross_amount": 0,
    "payment_fee": 0,
    "platform_fee": 0,
    "tax_provision": 0,
    "net_amount": 0,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _doc_row(doc: CustomerDocument, doc_id: int) -> dict:
    return {
        "id": doc_id,
        "document_number": doc.document_number,
        "document_type": doc.document_type,
        "payment_id": doc.payment_id,
        "ticket_id": doc.ticket_id,
        "transaction_id": doc.transaction_id,
        "issuer_name": doc.issuer_name,
        "issuer_identifier": doc.issuer_identifier,
        "customer_name": doc.customer_name,
        "customer_phone_masked": doc.customer_phone_masked,
        "line_name": doc.line_name,
        "origin_name": doc.origin_name,
        "destination_name": doc.destination_name,
        "commune": doc.commune,
        "gross_amount": doc.gross_amount,
        "tax_amount": doc.tax_amount,
        "net_amount": doc.net_amount,
        "currency": doc.currency,
        "payment_provider": doc.payment_provider,
        "fne_status": doc.fne_status,
        "fne_reference": doc.fne_reference,
        "verification_token": doc.verification_token,
        "created_at": doc.created_at,
        "cancelled_at": doc.cancelled_at,
    }


def _stub_row(stub: DriverStub, stub_id: int) -> dict:
    return {
        "id": stub_id,
        "stub_number": stub.stub_number,
        "payment_id": stub.payment_id,
        "transaction_id": stub.transaction_id,
        "ticket_id": stub.ticket_id,
        "driver_id": stub.driver_id,
        "line_name": stub.line_name,
        "provider": stub.provider,
        "gross_amount": stub.gross_amount,
        "payment_fee": stub.payment_fee,
        "platform_fee": stub.platform_fee,
        "tax_provision": stub.tax_provision,
        "net_amount": stub.net_amount,
        "settlement_status": stub.settlement_status,
        "created_at": stub.created_at,
    }


# ---------------------------------------------------------------- store mémoire


class MemoryFinanceStore:
    """Store en mémoire — mode local sans PostgreSQL et tests pytest."""

    def __init__(self) -> None:
        self.documents: list[dict] = []
        self.stubs: list[dict] = []
        self.tax_lines: list[dict] = []
        self.expenses: list[dict] = []
        self.tax_rules: list[dict] = []
        self.closures: list[dict] = []
        self._seqs: dict[str, int] = {}
        self._ids = {"doc": 0, "stub": 0, "tax": 0, "exp": 0, "closure": 0, "rule": 0}

    # -- infrastructure -----------------------------------------------------
    def ensure_ready(self) -> None:  # aucune DDL en mémoire
        return None

    def healthy(self) -> bool:
        return True

    def allocate_numbers(self, kind: str, year: int, count: int) -> int:
        name = f"{kind}-{year}"
        self._seqs[name] = self._seqs.get(name, 0) + count
        return self._seqs[name] - count + 1

    def _next_id(self, key: str) -> int:
        self._ids[key] += 1
        return self._ids[key]

    # -- transactions --------------------------------------------------------
    def insert_transactions(self, txs: list) -> None:
        for tx in txs:
            tx.document.id = self._next_id("doc")
            tx.document_id = tx.document.id
            self.documents.append(_doc_row(tx.document, tx.document.id))
            tx.stub.id = self._next_id("stub")
            tx.stub_id = tx.stub.id
            self.stubs.append(_stub_row(tx.stub, tx.stub.id))
            for line in tx.taxes:
                row = dict(line.__dict__)
                row["id"] = self._next_id("tax")
                self.tax_lines.append(row)

    # -- documents -----------------------------------------------------------
    def get_document(self, document_id: int) -> dict | None:
        for d in self.documents:
            if d["id"] == document_id:
                return dict(d)
        return None

    def get_document_by_payment(self, payment_id: str) -> dict | None:
        for d in self.documents:
            if d["payment_id"] == payment_id:
                return dict(d)
        return None

    def count_documents(self) -> int:
        return len(self.documents)

    # -- souches ---------------------------------------------------------------
    def _stub_matches(self, s: dict, driver_id, d_from, d_to, line, provider, status) -> bool:
        if s["driver_id"] != driver_id:
            return False
        d = s["created_at"].date()
        if d_from and d < d_from:
            return False
        if d_to and d > d_to:
            return False
        if line and s["line_name"] != line:
            return False
        if provider and s["provider"] != provider:
            return False
        if status and s["settlement_status"] != status:
            return False
        return True

    def list_stubs(
        self, driver_id, d_from=None, d_to=None, line=None, provider=None, status=None
    ) -> tuple[list[dict], dict]:
        rows = [
            dict(s)
            for s in self.stubs
            if self._stub_matches(s, driver_id, d_from, d_to, line, provider, status)
        ]
        rows.sort(key=lambda s: s["created_at"], reverse=True)
        totals = {
            k: sum(s[k] for s in rows)
            for k in ("gross_amount", "payment_fee", "platform_fee", "tax_provision", "net_amount")
        }
        totals["count"] = len(rows)
        return rows[:STUBS_PAGE_LIMIT], totals

    def get_stub(self, driver_id: str, stub_id: int) -> dict | None:
        for s in self.stubs:
            if s["id"] == stub_id and s["driver_id"] == driver_id:
                return dict(s)
        return None

    def stubs_range_aggregate(self, driver_id: str, d_from: date, d_to: date) -> dict:
        rows = [
            s
            for s in self.stubs
            if self._stub_matches(s, driver_id, d_from, d_to, None, None, None)
        ]
        agg = {
            "count": len(rows),
            "gross_amount": sum(s["gross_amount"] for s in rows),
            "payment_fee": sum(s["payment_fee"] for s in rows),
            "platform_fee": sum(s["platform_fee"] for s in rows),
            "tax_provision": sum(s["tax_provision"] for s in rows),
            "net_amount": sum(s["net_amount"] for s in rows),
        }
        return agg

    def stubs_pending_total(self, driver_id: str) -> dict:
        rows = [
            s
            for s in self.stubs
            if s["driver_id"] == driver_id and s["settlement_status"] == "pending"
        ]
        return {"count": len(rows), "net_amount": sum(s["net_amount"] for s in rows)}

    # -- lignes fiscales -------------------------------------------------------
    def tax_lines_for_payments(self, payment_ids: list[str]) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {pid: [] for pid in payment_ids}
        for t in self.tax_lines:
            if t["payment_id"] in out:
                out[t["payment_id"]].append(dict(t))
        return out

    def tax_summary(self, driver_id: str, d_from: date, d_to: date) -> list[dict]:
        driver_payments = {s["payment_id"]: s for s in self.stubs if s["driver_id"] == driver_id}
        rules = {r["id"]: r for r in self.tax_rules}
        grouped: dict[int, dict] = {}
        for t in self.tax_lines:
            stub = driver_payments.get(t["payment_id"])
            if stub is None:
                continue
            if not (d_from <= t["created_at"].date() <= d_to):
                continue
            rule = rules.get(t["tax_rule_id"], {})
            g = grouped.setdefault(
                t["tax_rule_id"],
                {
                    "tax_rule_id": t["tax_rule_id"],
                    "code": rule.get("code", "?"),
                    "label": rule.get("label", "?"),
                    "authority_type": rule.get("authority_type", "?"),
                    "authority_name": rule.get("authority_name", "?"),
                    "calculation_type": rule.get("calculation_type", "?"),
                    "is_official": rule.get("is_official", False),
                    "enabled": rule.get("enabled", True),
                    "amount": 0,
                    "count": 0,
                },
            )
            g["amount"] += t["calculated_amount"]
            g["count"] += 1
        return sorted(grouped.values(), key=lambda g: -g["amount"])

    # -- dépenses ---------------------------------------------------------------
    def add_expense(self, exp: DriverExpense) -> dict:
        exp.id = self._next_id("exp")
        exp.created_at = exp.created_at or _utcnow()
        row = dict(exp.__dict__)
        self.expenses.append(row)
        return dict(row)

    def list_expenses(self, driver_id, category=None, d_from=None, d_to=None) -> list[dict]:
        rows = []
        for e in self.expenses:
            if e["driver_id"] != driver_id:
                continue
            if category and e["category"] != category:
                continue
            if d_from and e["expense_date"] < d_from:
                continue
            if d_to and e["expense_date"] > d_to:
                continue
            rows.append(dict(e))
        rows.sort(key=lambda e: (e["expense_date"], e["id"]), reverse=True)
        return rows

    def delete_expense(self, driver_id: str, expense_id: int) -> bool:
        for i, e in enumerate(self.expenses):
            if e["id"] == expense_id and e["driver_id"] == driver_id:
                del self.expenses[i]
                return True
        return False

    def expenses_total(self, driver_id: str, d_from: date, d_to: date) -> int:
        return sum(e["amount"] for e in self.list_expenses(driver_id, None, d_from, d_to))

    # -- règles fiscales ----------------------------------------------------------
    def upsert_tax_rules(self, rules: list[dict]) -> None:
        by_code = {r["code"]: r for r in self.tax_rules}
        for r in rules:
            row = dict(r)
            existing = by_code.get(r["code"])
            if existing:
                row["id"] = existing["id"]
                self.tax_rules[self.tax_rules.index(existing)] = row
            else:
                row["id"] = self._next_id("rule")
                self.tax_rules.append(row)
                by_code[r["code"]] = row

    def list_tax_rules(self) -> list[dict]:
        return sorted((dict(r) for r in self.tax_rules), key=lambda r: r["code"])

    # -- clôtures -------------------------------------------------------------------
    def get_closure(self, driver_id: str, closure_date: date) -> dict | None:
        for c in self.closures:
            if c["driver_id"] == driver_id and c["closure_date"] == closure_date:
                return dict(c)
        return None

    def insert_closure(self, closure: DailyClosure) -> tuple[dict, bool]:
        existing = self.get_closure(closure.driver_id, closure.closure_date)
        if existing is not None:  # pas de double clôture
            return existing, False
        closure.id = self._next_id("closure")
        row = dict(closure.__dict__)
        self.closures.append(row)
        return dict(row), True

    def list_closures(self, driver_id: str, limit: int = 30) -> list[dict]:
        rows = [dict(c) for c in self.closures if c["driver_id"] == driver_id]
        rows.sort(key=lambda c: c["closure_date"], reverse=True)
        return rows[:limit]

    # -- backfill (mémoire : aucun historique) --------------------------------------
    def payments_for_backfill(self, days: int, limit: int) -> list[dict]:
        return []


# ---------------------------------------------------------------- store PostgreSQL


class PostgresFinanceStore:
    """Store PostgreSQL — tables du module financier + enrichissement de payments."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._ready = False

    def _connect(self):
        return psycopg.connect(self.url, connect_timeout=CONNECT_TIMEOUT, row_factory=dict_row)

    # -- infrastructure ---------------------------------------------------------
    def ensure_ready(self) -> None:
        """DDL idempotente + déduplication ticket_id + index unique (une fois)."""
        if self._ready:
            return
        with self._connect() as conn:
            with conn.cursor() as cur:
                for stmt in DDL_STATEMENTS:
                    cur.execute(stmt)
                cur.execute(DEDUP_TICKETS_SQL)
                cur.execute(UNIQUE_TICKET_INDEX_SQL)
            conn.commit()
        self._ready = True

    def healthy(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return True
        except Exception:  # noqa: BLE001 — sonde de santé, jamais bloquante
            return False

    def allocate_numbers(self, kind: str, year: int, count: int) -> int:
        name = f"{kind}-{year}"
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO finance_sequences (name, value) VALUES (%s, %s)"
                    " ON CONFLICT (name) DO UPDATE SET value = finance_sequences.value + EXCLUDED.value"
                    " RETURNING value",
                    (name, count),
                )
                value = cur.fetchone()["value"]
            conn.commit()
        return int(value) - count + 1

    # -- transactions ------------------------------------------------------------
    def insert_transactions(self, txs: list) -> None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                for tx in txs:
                    cur.execute(
                        "INSERT INTO customer_documents (document_number, document_type,"
                        " payment_id, ticket_id, transaction_id, issuer_name, issuer_identifier,"
                        " customer_name, customer_phone_masked, line_name, origin_name,"
                        " destination_name, commune, gross_amount, tax_amount, net_amount,"
                        " currency, payment_provider, fne_status, fne_reference,"
                        " verification_token, created_at)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        " RETURNING id",
                        (
                            tx.document.document_number,
                            tx.document.document_type,
                            tx.document.payment_id,
                            tx.document.ticket_id,
                            tx.document.transaction_id,
                            tx.document.issuer_name,
                            tx.document.issuer_identifier,
                            tx.document.customer_name,
                            tx.document.customer_phone_masked,
                            tx.document.line_name,
                            tx.document.origin_name,
                            tx.document.destination_name,
                            tx.document.commune,
                            tx.document.gross_amount,
                            tx.document.tax_amount,
                            tx.document.net_amount,
                            tx.document.currency,
                            tx.document.payment_provider,
                            tx.document.fne_status,
                            tx.document.fne_reference,
                            tx.document.verification_token,
                            tx.document.created_at,
                        ),
                    )
                    tx.document.id = cur.fetchone()["id"]
                    tx.document_id = tx.document.id
                    cur.execute(
                        "INSERT INTO driver_stubs (stub_number, payment_id, transaction_id,"
                        " ticket_id, driver_id, line_name, provider, gross_amount, payment_fee,"
                        " platform_fee, tax_provision, net_amount, settlement_status, created_at)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                        (
                            tx.stub.stub_number,
                            tx.stub.payment_id,
                            tx.stub.transaction_id,
                            tx.stub.ticket_id,
                            tx.stub.driver_id,
                            tx.stub.line_name,
                            tx.stub.provider,
                            tx.stub.gross_amount,
                            tx.stub.payment_fee,
                            tx.stub.platform_fee,
                            tx.stub.tax_provision,
                            tx.stub.net_amount,
                            tx.stub.settlement_status,
                            tx.stub.created_at,
                        ),
                    )
                    tx.stub.id = cur.fetchone()["id"]
                    tx.stub_id = tx.stub.id
                    for line in tx.taxes:
                        cur.execute(
                            "INSERT INTO tax_calculations (payment_id, tax_rule_id,"
                            " calculation_base, calculated_amount, calculation_kind, created_at)"
                            " VALUES (%s,%s,%s,%s,%s,%s)",
                            (
                                line.payment_id,
                                line.tax_rule_id,
                                line.calculation_base,
                                line.calculated_amount,
                                line.calculation_kind,
                                line.created_at,
                            ),
                        )
                    # Enrichissement de la ligne payments existante (best-effort,
                    # même transaction) — jamais d'insertion : la ligne a déjà été
                    # écrite par analytics.record_payment ou par le seed.
                    cur.execute(
                        "UPDATE payments SET transaction_id=%s, status=%s, gross_amount=%s,"
                        " currency=%s, provider_key=%s, line_id=%s, stop_id=%s, created_at=%s,"
                        " updated_at=now() WHERE ticket_id=%s",
                        (
                            tx.transaction_id,
                            tx.payment_status,
                            tx.gross_amount,
                            tx.currency,
                            tx.provider_key,
                            tx.line_id,
                            tx.stop_id,
                            tx.ts,
                            tx.ticket_id,
                        ),
                    )
            conn.commit()

    # -- documents ------------------------------------------------------------------
    def get_document(self, document_id: int) -> dict | None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM customer_documents WHERE id = %s", (document_id,))
                row = cur.fetchone()
        return row

    def get_document_by_payment(self, payment_id: str) -> dict | None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM customer_documents WHERE payment_id = %s", (payment_id,))
                row = cur.fetchone()
        return row

    def count_documents(self) -> int:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) AS n FROM customer_documents")
                return cur.fetchone()["n"]

    # -- souches -----------------------------------------------------------------------
    # NB : CAST(... AS ...) explicites indispensables — psycopg envoie None sans
    # type et PostgreSQL ne peut pas inférer `%(x)s IS NULL` seul (AmbiguousParameter).
    _STUB_WHERE = (
        " driver_id = %(driver_id)s"
        " AND (CAST(%(d_from)s AS date) IS NULL"
        " OR (created_at AT TIME ZONE 'UTC')::date >= %(d_from)s)"
        " AND (CAST(%(d_to)s AS date) IS NULL"
        " OR (created_at AT TIME ZONE 'UTC')::date <= %(d_to)s)"
        " AND (CAST(%(line)s AS text) IS NULL OR line_name = %(line)s)"
        " AND (CAST(%(provider)s AS text) IS NULL OR provider = %(provider)s)"
        " AND (CAST(%(status)s AS text) IS NULL OR settlement_status = %(status)s)"
    )

    def list_stubs(
        self, driver_id, d_from=None, d_to=None, line=None, provider=None, status=None
    ) -> tuple[list[dict], dict]:
        self.ensure_ready()
        params = {
            "driver_id": driver_id,
            "d_from": d_from,
            "d_to": d_to,
            "line": line,
            "provider": provider,
            "status": status,
        }
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM driver_stubs WHERE" + self._STUB_WHERE,
                    params,
                )
                rows = cur.fetchall()
                cur.execute(
                    "SELECT count(*) AS count, coalesce(sum(gross_amount),0) AS gross_amount,"
                    " coalesce(sum(payment_fee),0) AS payment_fee,"
                    " coalesce(sum(platform_fee),0) AS platform_fee,"
                    " coalesce(sum(tax_provision),0) AS tax_provision,"
                    " coalesce(sum(net_amount),0) AS net_amount"
                    " FROM driver_stubs WHERE" + self._STUB_WHERE,
                    params,
                )
                totals = cur.fetchone()
        rows.sort(key=lambda s: s["created_at"], reverse=True)
        return rows[:STUBS_PAGE_LIMIT], totals

    def get_stub(self, driver_id: str, stub_id: int) -> dict | None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM driver_stubs WHERE id = %s AND driver_id = %s",
                    (stub_id, driver_id),
                )
                row = cur.fetchone()
        return row

    def stubs_range_aggregate(self, driver_id: str, d_from: date, d_to: date) -> dict:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) AS count, coalesce(sum(gross_amount),0) AS gross_amount,"
                    " coalesce(sum(payment_fee),0) AS payment_fee,"
                    " coalesce(sum(platform_fee),0) AS platform_fee,"
                    " coalesce(sum(tax_provision),0) AS tax_provision,"
                    " coalesce(sum(net_amount),0) AS net_amount"
                    " FROM driver_stubs WHERE driver_id = %s"
                    " AND (created_at AT TIME ZONE 'UTC')::date BETWEEN %s AND %s",
                    (driver_id, d_from, d_to),
                )
                return cur.fetchone()

    def stubs_pending_total(self, driver_id: str) -> dict:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) AS count, coalesce(sum(net_amount),0) AS net_amount"
                    " FROM driver_stubs WHERE driver_id = %s AND settlement_status = 'pending'",
                    (driver_id,),
                )
                return cur.fetchone()

    # -- lignes fiscales -----------------------------------------------------------------
    def tax_lines_for_payments(self, payment_ids: list[str]) -> dict[str, list[dict]]:
        if not payment_ids:
            return {}
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT tc.payment_id, tc.calculation_kind, tc.calculation_base,"
                    " tc.calculated_amount, tc.created_at, r.code, r.label, r.is_official"
                    " FROM tax_calculations tc JOIN tax_rules r ON r.id = tc.tax_rule_id"
                    " WHERE tc.payment_id = ANY(%s)",
                    (payment_ids,),
                )
                rows = cur.fetchall()
        out: dict[str, list[dict]] = {pid: [] for pid in payment_ids}
        for row in rows:
            out.setdefault(row["payment_id"], []).append(row)
        return out

    def tax_summary(self, driver_id: str, d_from: date, d_to: date) -> list[dict]:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT r.id AS tax_rule_id, r.code, r.label, r.authority_type,"
                    " r.authority_name, r.calculation_type, r.is_official, r.enabled,"
                    " count(*) AS count, sum(tc.calculated_amount) AS amount"
                    " FROM tax_calculations tc"
                    " JOIN tax_rules r ON r.id = tc.tax_rule_id"
                    " JOIN driver_stubs s ON s.payment_id = tc.payment_id"
                    " WHERE s.driver_id = %s"
                    " AND (tc.created_at AT TIME ZONE 'UTC')::date BETWEEN %s AND %s"
                    " GROUP BY r.id, r.code, r.label, r.authority_type, r.authority_name,"
                    " r.calculation_type, r.is_official, r.enabled"
                    " ORDER BY amount DESC",
                    (driver_id, d_from, d_to),
                )
                rows = cur.fetchall()
        return rows

    # -- dépenses ---------------------------------------------------------------------------
    def add_expense(self, exp: DriverExpense) -> dict:
        self.ensure_ready()
        created = exp.created_at or _utcnow()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO driver_expenses (driver_id, expense_date, category,"
                    " description, amount, currency, receipt_reference, created_at)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                    (
                        exp.driver_id,
                        exp.expense_date,
                        exp.category,
                        exp.description,
                        exp.amount,
                        exp.currency,
                        exp.receipt_reference,
                        created,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return row

    def list_expenses(self, driver_id, category=None, d_from=None, d_to=None) -> list[dict]:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM driver_expenses WHERE driver_id = %s"
                    " AND (CAST(%s AS text) IS NULL OR category = %s)"
                    " AND (CAST(%s AS date) IS NULL OR expense_date >= %s)"
                    " AND (CAST(%s AS date) IS NULL OR expense_date <= %s)"
                    " ORDER BY expense_date DESC, id DESC",
                    (driver_id, category, category, d_from, d_from, d_to, d_to),
                )
                return cur.fetchall()

    def delete_expense(self, driver_id: str, expense_id: int) -> bool:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM driver_expenses WHERE id = %s AND driver_id = %s",
                    (expense_id, driver_id),
                )
                deleted = cur.rowcount
            conn.commit()
        return deleted > 0

    def expenses_total(self, driver_id: str, d_from: date, d_to: date) -> int:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT coalesce(sum(amount),0) AS total FROM driver_expenses"
                    " WHERE driver_id = %s AND expense_date BETWEEN %s AND %s",
                    (driver_id, d_from, d_to),
                )
                return cur.fetchone()["total"]

    # -- règles fiscales ------------------------------------------------------------------------
    def upsert_tax_rules(self, rules: list[dict]) -> None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                for r in rules:
                    cur.execute(
                        "INSERT INTO tax_rules (code, label, authority_type, authority_name,"
                        " commune, vehicle_category, operator_regime, calculation_type,"
                        " tax_target, rate, fixed_amount, frequency, effective_from,"
                        " effective_to, legal_reference, is_official, enabled)"
                        " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                        " ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label,"
                        " authority_type = EXCLUDED.authority_type,"
                        " authority_name = EXCLUDED.authority_name, commune = EXCLUDED.commune,"
                        " vehicle_category = EXCLUDED.vehicle_category,"
                        " operator_regime = EXCLUDED.operator_regime,"
                        " calculation_type = EXCLUDED.calculation_type,"
                        " tax_target = EXCLUDED.tax_target, rate = EXCLUDED.rate,"
                        " fixed_amount = EXCLUDED.fixed_amount, frequency = EXCLUDED.frequency,"
                        " effective_from = EXCLUDED.effective_from,"
                        " effective_to = EXCLUDED.effective_to,"
                        " legal_reference = EXCLUDED.legal_reference,"
                        " is_official = EXCLUDED.is_official, enabled = EXCLUDED.enabled",
                        (
                            r["code"],
                            r["label"],
                            r["authority_type"],
                            r["authority_name"],
                            r["commune"],
                            r["vehicle_category"],
                            r["operator_regime"],
                            r["calculation_type"],
                            r["tax_target"],
                            r["rate"],
                            r["fixed_amount"],
                            r["frequency"],
                            r["effective_from"],
                            r["effective_to"],
                            r["legal_reference"],
                            r["is_official"],
                            r["enabled"],
                        ),
                    )
            conn.commit()

    def list_tax_rules(self) -> list[dict]:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM tax_rules ORDER BY code")
                return cur.fetchall()

    # -- clôtures -----------------------------------------------------------------------------------
    def get_closure(self, driver_id: str, closure_date: date) -> dict | None:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM daily_closures WHERE driver_id = %s AND closure_date = %s",
                    (driver_id, closure_date),
                )
                return cur.fetchone()

    def insert_closure(self, closure: DailyClosure) -> tuple[dict, bool]:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO daily_closures (driver_id, closure_number, closure_date,"
                    " gross_revenue, fees, tax_provisions, expenses, estimated_net_income,"
                    " payment_count, created_at)"
                    " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                    " ON CONFLICT (driver_id, closure_date) DO NOTHING"
                    " RETURNING *",
                    (
                        closure.driver_id,
                        closure.closure_number,
                        closure.closure_date,
                        closure.gross_revenue,
                        closure.fees,
                        closure.tax_provisions,
                        closure.expenses,
                        closure.estimated_net_income,
                        closure.payment_count,
                        closure.created_at,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        if row is not None:
            return row, True
        return self.get_closure(closure.driver_id, closure.closure_date), False

    def list_closures(self, driver_id: str, limit: int = 30) -> list[dict]:
        self.ensure_ready()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM daily_closures WHERE driver_id = %s"
                    " ORDER BY closure_date DESC LIMIT %s",
                    (driver_id, limit),
                )
                return cur.fetchall()

    # -- backfill ----------------------------------------------------------------------------------------
    def payments_for_backfill(self, days: int, limit: int) -> list[dict]:
        """Paiements seedés des `days` derniers jours AVANT aujourd'hui (avec conducteur).

        Les documents/souches du jour même ne sont PAS backfillés : le dashboard
        conducteur du jour repose sur les recettes de démonstration + paiements live.
        """
        self.ensure_ready()
        today = datetime.now(timezone.utc).date()
        d_to = today - timedelta(days=1)
        d_from = today - timedelta(days=days)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, ts, ticket_id, line_name, mode, fare, provider, driver_id"
                    " FROM payments"
                    " WHERE driver_id IS NOT NULL"
                    " AND (ts AT TIME ZONE 'UTC')::date BETWEEN %s AND %s"
                    " ORDER BY ts DESC LIMIT %s",
                    (d_from, d_to, limit),
                )
                return cur.fetchall()
