"""Façade du module financier — best-effort, JAMAIS bloquante pour un paiement.

Comme analytics.py : si PostgreSQL est disponible (DATABASE_URL), les données
financières y sont persistées ; sinon (mode local demo.sh) ou en cas d'indisponibilité,
elles vivent en mémoire — la démo continue de fonctionner sans erreur.
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime, time, timedelta, timezone

from . import documents, tax_engine
from .documents import PaymentContext
from .documents_numbering import format_closure_number
from .models import (
    PROVIDER_LABEL_TO_KEY,
    DailyClosure,
    DriverExpense,
)
from .store import MemoryFinanceStore, PostgresFinanceStore

log = logging.getLogger("abidjanmob.finance")

BACKFILL_DAYS = 7
BACKFILL_LIMIT = 2500  # plafond de lignes backfillées au premier démarrage (durée de démarrage)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FinanceService:
    """Orchestration : frais, taxes, documents, souches, résumés, clôtures."""

    def __init__(self, primary: MemoryFinanceStore | PostgresFinanceStore) -> None:
        self.primary = primary
        self.fallback = MemoryFinanceStore()
        self._rules_seeded = False

    # ------------------------------------------------------------ infrastructure

    def _stores(self) -> list:
        """Store principal, puis repli mémoire (une seule passe réussie suffit)."""
        return [self.primary, self.fallback]

    def _seed_rules_if_needed(self, store) -> None:
        rules = store.list_tax_rules()
        if not rules:
            store.upsert_tax_rules(tax_engine.demo_rules())
            rules = store.list_tax_rules()
        return rules

    def _active_rules(self, store) -> list[tax_engine.TaxRule]:
        rows = self._seed_rules_if_needed(store)
        return [tax_engine.parse_rule_row(r) for r in rows]

    # ------------------------------------------------------------- démarrage

    def on_startup(
        self,
        demo_day_contexts: list[PaymentContext] | None = None,
        backfill_days: int = BACKFILL_DAYS,
        backfill_limit: int = BACKFILL_LIMIT,
    ) -> None:
        """Initialisation au démarrage de l'API (idempotente)."""
        # 1. Règles de démonstration dans le store principal ET le repli mémoire
        #    (le repli doit pouvoir calculer des taxes si PostgreSQL tombe).
        for store in self._stores():
            try:
                self._seed_rules_if_needed(store)
            except Exception:  # noqa: BLE001 — jamais bloquant
                log.exception("finance: initialisation des règles fiscales impossible (%s)", store)

        # 2. Backfill des documents/souches récents (PostgreSQL uniquement) — AVANT
        #    le seed du jour : son garde-fou est « aucun document existant ».
        if isinstance(self.primary, PostgresFinanceStore):
            try:
                self._backfill(backfill_days, backfill_limit)
            except Exception:  # noqa: BLE001
                log.exception("finance: backfill impossible")

        # 3. Transactions du jour de démonstration (recettes seedées du conducteur)
        if demo_day_contexts:
            try:
                self._seed_demo_day(demo_day_contexts)
            except Exception:  # noqa: BLE001
                log.exception("finance: seed du jour de démonstration impossible")

    def _seed_demo_day(self, ctxs: list[PaymentContext]) -> None:
        """Recettes de démonstration du conducteur → transactions complètes.

        Idempotent par date : si les documents du jour de démo existent déjà
        (redémarrage de l'API le même jour), on ne rejoute rien.
        """
        for store in self._stores():
            try:
                marker = store.get_document_by_payment(ctxs[0].payment_id)
                if marker is not None:
                    return
                rules = self._active_rules(store)
                txs = documents.build_transactions(ctxs, rules, store.allocate_numbers)
                store.insert_transactions(txs)
                log.info(
                    "finance: %d transactions de démonstration seedées (%s)",
                    len(txs),
                    ctxs[0].ts.date(),
                )
                return
            except Exception:  # noqa: BLE001
                log.exception("finance: seed jour démo — essai sur le store suivant")
        log.warning("finance: seed du jour de démonstration ignoré (aucun store disponible)")

    def _backfill(self, days: int, limit: int) -> None:
        """Backfill documents + souches des paiements seedés récents (une seule fois).

        Le seed historique (151 k paiements) n'a pas de documents associés : on
        matérialise les 7 derniers jours AVANT aujourd'hui pour que les tableaux
        de bord aient de la matière. One-shot : sauté si des documents existent déjà.
        """
        store = self.primary
        if store.count_documents() > 0:
            log.info("finance: backfill sauté (documents déjà présents)")
            return
        rows = store.payments_for_backfill(days, limit)
        if not rows:
            log.info("finance: backfill — aucun paiement éligible")
            return
        ctxs = [self._backfill_context(row) for row in rows]
        rules = self._active_rules(store)
        txs = documents.build_transactions(ctxs, rules, store.allocate_numbers)
        store.insert_transactions(txs)
        log.info(
            "finance: backfill de %d paiements → %d documents + %d souches",
            len(rows),
            len(txs),
            len(txs),
        )

    def _backfill_context(self, row: dict) -> PaymentContext:
        """Contexte d'un paiement seedé → transaction (lignes résolues par nom)."""
        from routing_engine import get_network  # import local : corpus du prototype

        net = get_network()
        line = next((ln for ln in net.lines.values() if ln["name"] == row["line_name"]), None)
        driver = net.drivers.get(row["driver_id"], {})
        origin = destination = commune = None
        if line is not None:
            first = net.stops[line["stops"][0]]
            last = net.stops[line["stops"][-1]]
            origin, destination, commune = first["name"], last["name"], first["commune"]
        return PaymentContext(
            ticket_id=row["ticket_id"],
            line_name=row["line_name"],
            mode=row["mode"],
            gross=int(row["fare"]),
            provider_key=PROVIDER_LABEL_TO_KEY.get(row["provider"], "wave"),
            provider_label=row["provider"],
            driver_id=row["driver_id"],
            driver_name=driver.get("name", row["driver_id"]),
            ts=row["ts"],
            line_id=line["id"] if line else None,
            origin_name=origin,
            destination_name=destination,
            commune=commune,
            vehicle_category=row["mode"],
            settlement_status="settled",  # jours passés : déjà reversés
            payment_id=f"PAY-BK{row['id']}",
            transaction_id=f"TRX-BK{row['id']}",
        )

    # ------------------------------------------------------------- paiements

    def process_payment(self, ctx: PaymentContext) -> dict | None:
        """Paiement confirmé → transaction comptable complète. Ne lève jamais.

        Retourne les informations financières à fusionner dans la réponse du
        paiement (document_id, verification_token, net conducteur, …) ou None.
        """
        for store in self._stores():
            try:
                rules = self._active_rules(store)
                txs = documents.build_transactions([ctx], rules, store.allocate_numbers)
                store.insert_transactions(txs)
                return self._tx_response(txs[0])
            except Exception:  # noqa: BLE001 — le paiement ne doit jamais échouer
                log.exception("finance: traitement du paiement %s — store suivant", ctx.ticket_id)
        log.error("finance: aucun store disponible pour %s (paiement non bloqué)", ctx.ticket_id)
        return None

    def _tx_response(self, tx) -> dict:
        doc, stub = tx.document, tx.stub
        return {
            "transaction_id": tx.transaction_id,
            "payment_id": tx.payment_id,
            "document_id": doc.id,
            "document_number": doc.document_number,
            "verification_token": doc.verification_token,
            "verify_payload": documents.verify_payload(doc.document_number, doc.verification_token),
            "stub_number": stub.stub_number,
            "financial": {
                "currency": stub_currency(stub),
                "gross_amount": stub.gross_amount,
                "payment_fee": stub.payment_fee,
                "platform_fee": stub.platform_fee,
                "tax_provision": stub.tax_provision,
                "net_amount": stub.net_amount,
            },
        }

    # ------------------------------------------------------------- documents

    def get_document(self, document_id: int) -> dict | None:
        for store in self._stores():
            try:
                doc = store.get_document(document_id)
                if doc is not None:
                    lines = store.tax_lines_for_payments([doc["payment_id"]])
                    doc = dict(doc)
                    doc["tax_lines"] = lines.get(doc["payment_id"], [])
                    doc["verify_payload"] = documents.verify_payload(
                        doc["document_number"], doc["verification_token"]
                    )
                    doc["fne_message"] = fne_message(doc["fne_status"])
                    return doc
            except Exception:  # noqa: BLE001
                log.exception("finance: lecture document %s — store suivant", document_id)
        return None

    def verify_document(self, document_id: int, token: str) -> dict | None:
        doc = self.get_document(document_id)
        if doc is None:
            return None
        return {
            "valid": doc["verification_token"] == token,
            "document_id": doc["id"],
            "document_number": doc["document_number"],
            "document_type": doc["document_type"],
            "ticket_id": doc["ticket_id"],
            "line_name": doc["line_name"],
            "gross_amount": doc["gross_amount"],
            "currency": doc["currency"],
            "issuer_name": doc["issuer_name"],
            "fne_status": doc["fne_status"],
            "created_at": doc["created_at"],
            "checked_at": _utcnow(),
        }

    # ------------------------------------------------------------- souches

    def list_stubs(
        self,
        driver_id: str,
        d_from: date | None = None,
        d_to: date | None = None,
        line: str | None = None,
        provider: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict], dict] | None:
        for store in self._stores():
            try:
                return store.list_stubs(driver_id, d_from, d_to, line, provider, status)
            except Exception:  # noqa: BLE001
                log.exception("finance: liste souches — store suivant")
        return None

    def get_stub_detail(self, driver_id: str, stub_id: int) -> dict | None:
        for store in self._stores():
            try:
                stub = store.get_stub(driver_id, stub_id)
                if stub is not None:
                    stub = dict(stub)
                    lines = store.tax_lines_for_payments([stub["payment_id"]])
                    stub["taxes"] = lines.get(stub["payment_id"], [])
                    return stub
            except Exception:  # noqa: BLE001
                log.exception("finance: détail souche — store suivant")
        return None

    # ------------------------------------------------------------- résumés

    def financial_summary(self, driver_id: str) -> dict | None:
        today = _utcnow().date()
        # Bilans périodiques : 7 jours glissants, mois et trimestre en cours.
        bornes = {
            "week": today - timedelta(days=6),
            "month": today.replace(day=1),
            "quarter": today.replace(month=(today.month - 1) // 3 * 3 + 1, day=1),
        }
        for store in self._stores():
            try:
                day = store.stubs_range_aggregate(driver_id, today, today)
                day_exp = store.expenses_total(driver_id, today, today)
                pending = store.stubs_pending_total(driver_id)
                periodes: dict[str, dict] = {}
                for nom, d_from in bornes.items():
                    agg = store.stubs_range_aggregate(driver_id, d_from, today)
                    exp = store.expenses_total(driver_id, d_from, today)
                    periodes[nom] = {
                        "from": d_from.isoformat(),
                        "to": today.isoformat(),
                        "gross_revenue": agg["gross_amount"],
                        "payment_count": agg["count"],
                        "payment_fees": agg["payment_fee"],
                        "commissions": agg["platform_fee"],
                        "tax_provisions": agg["tax_provision"],
                        "expenses": exp,
                        "estimated_net_income": (
                            agg["gross_amount"]
                            - agg["payment_fee"]
                            - agg["platform_fee"]
                            - agg["tax_provision"]
                            - exp
                        ),
                    }
                return {
                    "driver_id": driver_id,
                    "currency": "XOF",
                    "today": {
                        "date": today.isoformat(),
                        "gross_revenue": day["gross_amount"],
                        "payment_count": day["count"],
                        "trips": day["count"],  # 1 paiement = 1 course (prototype)
                        "payment_fees": day["payment_fee"],
                        "commissions": day["platform_fee"],
                        "tax_provisions": day["tax_provision"],
                        "expenses": day_exp,
                        "estimated_net_income": (
                            day["gross_amount"]
                            - day["payment_fee"]
                            - day["platform_fee"]
                            - day["tax_provision"]
                            - day_exp
                        ),
                        "net_amount": day["net_amount"],
                        "net_to_remit": pending["net_amount"],
                    },
                    **periodes,
                    "pending_settlement": pending,
                    "disclaimer": tax_engine.TAX_DISCLAIMER,
                }
            except Exception:  # noqa: BLE001
                log.exception("finance: résumé financier — store suivant")
        return None

    def tax_summary(self, driver_id: str, d_from: date, d_to: date) -> dict | None:
        for store in self._stores():
            try:
                rows = store.tax_summary(driver_id, d_from, d_to)
                rules = {r["id"]: r for r in store.list_tax_rules()}
                total_operator = 0
                total_provision = 0
                out_rows = []
                for row in rows:
                    rule = rules.get(row["tax_rule_id"], {})
                    out_rows.append(
                        {
                            "code": row["code"],
                            "label": row["label"],
                            "authority_type": row["authority_type"],
                            "authority_name": row["authority_name"],
                            "calculation_type": row["calculation_type"],
                            "is_official": row["is_official"],
                            "enabled": row["enabled"],
                            "count": row["count"],
                            "amount": row["amount"],
                            "rate": rule.get("rate", 0),
                            "fixed_amount": rule.get("fixed_amount", 0),
                        }
                    )
                    if row["calculation_type"] in ("fixed_daily", "fixed_monthly", "fixed_annual"):
                        total_provision += row["amount"]
                    else:
                        total_operator += row["amount"]
                return {
                    "driver_id": driver_id,
                    "period": {"from": d_from.isoformat(), "to": d_to.isoformat()},
                    "rules": out_rows,
                    "totals": {
                        "operator_taxes": total_operator,
                        "estimated_provisions": total_provision,
                        "all": total_operator + total_provision,
                    },
                    "disclaimer": tax_engine.TAX_DISCLAIMER,
                }
            except Exception:  # noqa: BLE001
                log.exception("finance: synthèse fiscale — store suivant")
        return None

    def list_tax_rules(self) -> list[dict] | None:
        for store in self._stores():
            try:
                self._seed_rules_if_needed(store)
                return store.list_tax_rules()
            except Exception:  # noqa: BLE001
                log.exception("finance: liste règles fiscales — store suivant")
        return None

    # ------------------------------------------------------------- dépenses

    def add_expense(self, exp: DriverExpense) -> dict | None:
        for store in self._stores():
            try:
                return store.add_expense(exp)
            except Exception:  # noqa: BLE001
                log.exception("finance: ajout dépense — store suivant")
        return None

    def list_expenses(
        self,
        driver_id: str,
        category: str | None = None,
        d_from: date | None = None,
        d_to: date | None = None,
    ) -> list[dict] | None:
        for store in self._stores():
            try:
                return store.list_expenses(driver_id, category, d_from, d_to)
            except Exception:  # noqa: BLE001
                log.exception("finance: liste dépenses — store suivant")
        return None

    def delete_expense(self, driver_id: str, expense_id: int) -> bool | None:
        for store in self._stores():
            try:
                return store.delete_expense(driver_id, expense_id)
            except Exception:  # noqa: BLE001
                log.exception("finance: suppression dépense — store suivant")
        return None

    # ------------------------------------------------------------- clôtures

    def close_day(self, driver_id: str, closure_date: date) -> tuple[dict, bool] | None:
        """Clôture idempotente : une seconde clôture le même jour ne crée rien."""
        for store in self._stores():
            try:
                existing = store.get_closure(driver_id, closure_date)
                if existing is not None:
                    return existing, False
                agg = store.stubs_range_aggregate(driver_id, closure_date, closure_date)
                expenses = store.expenses_total(driver_id, closure_date, closure_date)
                seq = store.allocate_numbers("CLR", closure_date.year, 1)
                fees = agg["payment_fee"] + agg["platform_fee"]
                closure = DailyClosure(
                    driver_id=driver_id,
                    closure_number=format_closure_number(closure_date.year, seq),
                    closure_date=closure_date,
                    gross_revenue=agg["gross_amount"],
                    fees=fees,
                    tax_provisions=agg["tax_provision"],
                    expenses=expenses,
                    estimated_net_income=(
                        agg["gross_amount"] - fees - agg["tax_provision"] - expenses
                    ),
                    payment_count=agg["count"],
                    created_at=_utcnow(),
                    payment_fees=agg["payment_fee"],
                    commissions=agg["platform_fee"],
                )
                return store.insert_closure(closure)
            except Exception:  # noqa: BLE001
                log.exception("finance: clôture — store suivant")
        return None

    def list_closures(self, driver_id: str) -> list[dict] | None:
        for store in self._stores():
            try:
                return store.list_closures(driver_id)
            except Exception:  # noqa: BLE001
                log.exception("finance: liste clôtures — store suivant")
        return None


def stub_currency(stub) -> str:
    return getattr(stub, "currency", None) or "XOF"


def fne_message(status: str) -> str:
    """Mention affichée sur le document selon son statut de certification."""
    if status == "not_certified_demo":
        return "Certification FNE non activée dans le prototype"
    return ""


# ------------------------------------------------------------------ singleton

_SERVICE: FinanceService | None = None


def get_service() -> FinanceService:
    global _SERVICE
    if _SERVICE is None:
        url = os.environ.get("DATABASE_URL")
        if url:
            primary = PostgresFinanceStore(url)
        else:
            primary = MemoryFinanceStore()
        _SERVICE = FinanceService(primary)
    return _SERVICE


def configure_for_tests() -> FinanceService:
    """Force le store mémoire (tests pytest — aucune base requise)."""
    global _SERVICE
    _SERVICE = FinanceService(MemoryFinanceStore())
    return _SERVICE


def demo_day_contexts(
    driver: dict, driver_line: dict, seed_receipts: list[tuple], providers: dict
) -> list[PaymentContext]:
    """Recettes de démonstration du conducteur → contextes de transaction.

    Identifiants déterministes (PAY-SEED-AAAAMMJJ-nn) → idempotence par jour.
    Le contexte fiscal (commune du premier arrêt de la ligne, origine/destination)
    est résolu depuis la ligne du conducteur, comme pour les paiements live.
    """
    from routing_engine import get_network  # import local : corpus du prototype

    net = get_network()
    stops = [net.stops[sid] for sid in driver_line["stops"]]
    origin, destination = stops[0], stops[-1]
    today = _utcnow().date()
    ctxs = []
    for i, (time_hm, fare, provider_key) in enumerate(seed_receipts, start=1):
        hh, mm = (int(x) for x in time_hm.split(":"))
        ts = datetime.combine(today, time(hh, mm), tzinfo=timezone.utc)
        ctxs.append(
            PaymentContext(
                ticket_id=f"ABJ-SED{today.strftime('%y%m%d')}{i:02d}",
                line_name=driver_line["name"],
                mode=driver_line["mode"],
                gross=int(fare),
                provider_key=provider_key,
                provider_label=providers[provider_key],
                driver_id=driver["id"],
                driver_name=driver["name"],
                ts=ts,
                line_id=driver_line["id"],
                origin_name=origin["name"],
                destination_name=destination["name"],
                commune=origin["commune"],
                vehicle_category=driver_line["mode"],
                settlement_status="pending",
                payment_id=f"PAY-SEED-{today.strftime('%Y%m%d')}-{i:02d}",
                transaction_id=f"TRX-SEED-{today.strftime('%Y%m%d')}-{i:02d}",
            )
        )
    return ctxs
