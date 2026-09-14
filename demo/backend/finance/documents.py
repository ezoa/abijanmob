"""Génération des documents financiers : facture/reçu client + souche conducteur.

Conventions de numérotation du module (documentées dans docs/module-financier.md) :
- billet (existant)      : ABJ-XXXXXX
- paiement               : PAY-XXXXXXXX
- transaction comptable  : TRX-XXXXXXXX
- facture / reçu client  : FAC-AAAA-NNNNNN
- souche conducteur      : STB-AAAA-NNNNNN
- clôture de journée     : CLR-AAAA-NNNNNN
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from . import tax_engine
from .documents_numbering import (  # noqa: F401 (réexporté pour les tests)
    format_closure_number,
    format_document_number,
    format_stub_number,
)
from .fees import compute_fees
from .fne import get_certification_provider
from .models import CURRENCY, CustomerDocument, DriverStub, TaxLine, TransactionRecord

VERIFY_PAYLOAD_PREFIX = "ABJMOB|VERIF"


def new_transaction_id() -> str:
    return f"TRX-{uuid.uuid4().hex[:8].upper()}"


def new_payment_id() -> str:
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


def new_verification_token() -> str:
    return secrets.token_hex(8)


def verify_payload(document_number: str, token: str) -> str:
    """Contenu du QR de vérification AbidjanMob (PAS un QR FNE)."""
    return f"{VERIFY_PAYLOAD_PREFIX}|{document_number}|{token}"


@dataclass
class PaymentContext:
    """Contexte complet d'un paiement confirmé, prêt à générer la transaction."""

    ticket_id: str
    line_name: str
    mode: str
    gross: int
    provider_key: str
    provider_label: str
    driver_id: str
    driver_name: str
    ts: datetime
    line_id: str | None = None
    stop_id: str | None = None
    origin_name: str | None = None
    destination_name: str | None = None
    commune: str | None = None
    vehicle_category: str | None = None
    settlement_status: str = "pending"
    # Identifiants déterministes (seed du jour de démo / backfill) :
    payment_id: str = field(default_factory=new_payment_id)
    transaction_id: str = field(default_factory=new_transaction_id)


def build_payment_context(
    *,
    ticket: dict,
    ts: datetime,
    provider_key: str,
    driver: dict,
    line: dict | None,
    stop: dict | None,
    dest_stop: dict | None,
    line_id: str | None,
    stop_id: str | None,
    provider_label: str,
) -> PaymentContext:
    """Assemble le contexte depuis un ticket + les objets du corpus réseau.

    Résolution du contexte fiscal : la commune est celle de l'arrêt d'embarquement
    (stop_id) ; à défaut, celle du premier arrêt de la ligne ; sinon aucune (les
    règles communales ne s'appliquent pas). La catégorie de véhicule est le mode.
    """
    if ts.tzinfo is None:  # datetime naïf (heure locale) → aware
        ts = ts.astimezone()
    origin_name = stop["name"] if stop else None
    commune = stop["commune"] if stop else None
    destination_name = dest_stop["name"] if dest_stop else None
    if line is not None:
        first, last = line["stops"][0], line["stops"][-1]
        if origin_name is None:
            origin_name = first["name"]
        if commune is None:
            commune = first["commune"]
        if destination_name is None:
            destination_name = last["name"]
    return PaymentContext(
        ticket_id=ticket["ticket_id"],
        line_name=ticket["line_name"],
        mode=ticket["mode"],
        gross=int(ticket["fare"]),
        provider_key=provider_key,
        provider_label=provider_label,
        driver_id=driver["id"],
        driver_name=driver["name"],
        ts=ts,
        line_id=line_id,
        stop_id=stop_id,
        origin_name=origin_name,
        destination_name=destination_name,
        commune=commune,
        vehicle_category=ticket["mode"],
    )


def build_transactions(
    ctxs: list[PaymentContext],
    rules: list[tax_engine.TaxRule],
    allocate,
    certification_provider=None,
) -> list[TransactionRecord]:
    """Génère les transactions pour un lot de paiements.

    `allocate(kind, count)` fournit le premier numéro d'une séquence (le store
    garantit l'unicité). Les numéros sont alloués par année, en une fois par lot.
    """
    provider = certification_provider or get_certification_provider()
    years = sorted({ctx.ts.year for ctx in ctxs})
    doc_seq: dict[int, int] = {}
    stub_seq: dict[int, int] = {}
    for year in years:
        n = sum(1 for c in ctxs if c.ts.year == year)
        doc_seq[year] = allocate("FAC", year, n)
        stub_seq[year] = allocate("STB", year, n)

    out: list[TransactionRecord] = []
    for ctx in ctxs:
        taxes = tax_engine.applicable_taxes(
            rules,
            on_date=ctx.ts.date(),
            gross_amount=ctx.gross,
            commune=ctx.commune,
            vehicle_category=ctx.vehicle_category,
        )
        tax_lines = [
            TaxLine(
                payment_id=ctx.payment_id,
                tax_rule_id=rule.id,
                code=rule.code,
                label=rule.label,
                calculation_base=ctx.gross,
                calculated_amount=amount,
                calculation_kind=kind,
                created_at=ctx.ts,
            )
            for rule, amount, kind in taxes
        ]
        customer_tax = sum(
            t.calculated_amount for t in tax_lines if t.calculation_kind == "customer_collected_tax"
        )
        tax_provision = sum(
            t.calculated_amount
            for t in tax_lines
            if tax_engine.is_driver_burden(t.calculation_kind)
        )
        payment_fee, platform_fee = compute_fees(ctx.gross)
        net_amount = ctx.gross - payment_fee - platform_fee - tax_provision

        doc_number = format_document_number(ctx.ts.year, doc_seq[ctx.ts.year])
        doc_seq[ctx.ts.year] += 1
        stub_number = format_stub_number(ctx.ts.year, stub_seq[ctx.ts.year])
        stub_seq[ctx.ts.year] += 1

        certification = provider.certify({"ticket_id": ctx.ticket_id, "line_name": ctx.line_name})
        document = CustomerDocument(
            document_number=doc_number,
            document_type="receipt",
            payment_id=ctx.payment_id,
            ticket_id=ctx.ticket_id,
            transaction_id=ctx.transaction_id,
            issuer_name=ctx.driver_name,
            issuer_identifier=ctx.driver_id,
            customer_name="Usager AbidjanMob (démo)",
            customer_phone_masked=None,  # pas de PII dans le prototype
            line_name=ctx.line_name,
            origin_name=ctx.origin_name,
            destination_name=ctx.destination_name,
            commune=ctx.commune,
            gross_amount=ctx.gross,
            tax_amount=customer_tax,
            net_amount=ctx.gross - customer_tax,
            currency=CURRENCY,
            payment_provider=ctx.provider_label,
            fne_status=certification["status"],
            fne_reference=certification["reference"],
            verification_token=new_verification_token(),
            created_at=ctx.ts,
        )
        stub = DriverStub(
            stub_number=stub_number,
            payment_id=ctx.payment_id,
            transaction_id=ctx.transaction_id,
            ticket_id=ctx.ticket_id,
            driver_id=ctx.driver_id,
            line_name=ctx.line_name,
            provider=ctx.provider_label,
            gross_amount=ctx.gross,
            payment_fee=payment_fee,
            platform_fee=platform_fee,
            tax_provision=tax_provision,
            net_amount=net_amount,
            settlement_status=ctx.settlement_status,
            created_at=ctx.ts,
        )
        out.append(
            TransactionRecord(
                transaction_id=ctx.transaction_id,
                payment_id=ctx.payment_id,
                ticket_id=ctx.ticket_id,
                document=document,
                stub=stub,
                taxes=tax_lines,
                gross_amount=ctx.gross,
                provider_key=ctx.provider_key,
                line_id=ctx.line_id,
                stop_id=ctx.stop_id,
                driver_id=ctx.driver_id,
                line_name=ctx.line_name,
                mode=ctx.mode,
                fare=ctx.gross,
                provider=ctx.provider_label,
                ts=ctx.ts,
            )
        )
    return out
