"""Modèles de données du module financier (partagés par tous les stores).

Montants en francs CFA (XOF, entiers — pas de subdivision). Toutes les dates/heures
sont stockées en UTC-aware pour rester cohérent entre PostgreSQL (timestamptz) et
le store mémoire (mode local / tests).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

CURRENCY = "XOF"

# Types de documents clients (cahier des charges).
DOCUMENT_TYPES = ("transport_ticket", "receipt", "invoice", "credit_note")
# Statuts du paiement (évolution de la table payments).
PAYMENT_STATUSES = ("pending", "paid", "failed", "cancelled", "refunded")
# Statuts de reversement d'une souche conducteur.
SETTLEMENT_STATUSES = ("pending", "settled")
# Nature d'un calcul fiscal.
TAX_CALCULATION_KINDS = (
    "customer_collected_tax",  # taxe collectée auprès du client (figure sur la facture)
    "operator_tax",  # taxe à la charge de l'exploitant (figure sur la souche)
    "estimated_provision",  # provision estimative (taxe jour/mois/année répartie)
)
# Statuts FNE/RNE possibles d'un document.
FNE_STATUSES = (
    "not_applicable",
    "not_certified_demo",  # statut du prototype : jamais « certified »
    "pending",
    "certified",
    "rejected",
)

# Catégories de dépenses conducteur (cahier des charges).
EXPENSE_CATEGORIES = (
    "fuel",
    "maintenance",
    "repair",
    "tires",
    "insurance",
    "technical_inspection",
    "parking",
    "station_fee",
    "toll",
    "washing",
    "union_fee",
    "tax",
    "other",
)

# Libellés français des catégories (interface).
EXPENSE_CATEGORY_LABELS = {
    "fuel": "Carburant",
    "maintenance": "Entretien",
    "repair": "Réparation",
    "tires": "Pneus",
    "insurance": "Assurance",
    "technical_inspection": "Visite technique",
    "parking": "Stationnement",
    "station_fee": "Frais de gare",
    "toll": "Péage",
    "washing": "Lavage",
    "union_fee": "Cotisation syndicale",
    "tax": "Taxe",
    "other": "Autre",
}

# Opérateurs mobile money du prototype (doublon volontaire de main.PROVIDERS :
# le module financier reste autonome par rapport au module de paiement).
MOBILE_MONEY_PROVIDERS = {
    "wave": "Wave",
    "orange": "Orange Money",
    "mtn": "MTN MoMo",
    "moov": "Moov Money",
}
PROVIDER_LABEL_TO_KEY = {label: key for key, label in MOBILE_MONEY_PROVIDERS.items()}


@dataclass
class TaxLine:
    """Ligne de calcul fiscal attachée à un paiement (table tax_calculations)."""

    payment_id: str
    tax_rule_id: int
    code: str
    label: str
    calculation_base: int
    calculated_amount: int
    calculation_kind: str
    created_at: datetime


@dataclass
class CustomerDocument:
    """Facture / reçu client (table customer_documents)."""

    document_number: str
    document_type: str
    payment_id: str
    ticket_id: str
    transaction_id: str
    issuer_name: str
    issuer_identifier: str
    customer_name: str
    customer_phone_masked: str | None
    line_name: str
    origin_name: str | None
    destination_name: str | None
    commune: str | None  # commune d'embarquement (analytics « recettes par commune »)
    gross_amount: int
    tax_amount: int
    net_amount: int
    currency: str
    payment_provider: str
    fne_status: str
    fne_reference: str | None
    verification_token: str
    created_at: datetime
    cancelled_at: datetime | None = None
    id: int | None = None


@dataclass
class DriverStub:
    """Souche numérique conducteur (table driver_stubs).

    `provider` (colonne additionnelle) porte l'opérateur mobile money : le filtre
    « par opérateur » est exigé par le cahier des charges.
    """

    stub_number: str
    payment_id: str
    transaction_id: str
    ticket_id: str
    driver_id: str
    line_name: str
    provider: str
    gross_amount: int
    payment_fee: int
    platform_fee: int
    tax_provision: int
    net_amount: int
    settlement_status: str
    created_at: datetime
    id: int | None = None


@dataclass
class DriverExpense:
    """Dépense saisie par un conducteur (table driver_expenses)."""

    driver_id: str
    expense_date: date
    category: str
    amount: int
    currency: str
    description: str = ""
    receipt_reference: str | None = None
    created_at: datetime | None = None
    id: int | None = None


@dataclass
class DailyClosure:
    """Clôture de journée d'un conducteur (table daily_closures)."""

    driver_id: str
    closure_number: str
    closure_date: date
    gross_revenue: int
    fees: int  # frais de paiement + commissions plateforme
    tax_provisions: int
    expenses: int
    estimated_net_income: int
    payment_count: int
    created_at: datetime
    # Détail (non stocké, restitué par l'API) :
    payment_fees: int = 0
    commissions: int = 0
    id: int | None = None


@dataclass
class TransactionRecord:
    """Tout ce qu'un paiement confirmé génère — insertion atomique dans le store.

    Chaîne : paiement → transaction comptable → document client + souche conducteur
    + calculs fiscaux (+ enrichissement de la ligne `payments` en mode PostgreSQL).
    """

    transaction_id: str
    payment_id: str
    ticket_id: str
    document: CustomerDocument
    stub: DriverStub
    taxes: list[TaxLine] = field(default_factory=list)
    # Enrichissement de la ligne payments existante (PostgreSQL uniquement) :
    payment_status: str = "paid"
    gross_amount: int = 0
    currency: str = CURRENCY
    provider_key: str | None = None
    line_id: str | None = None
    stop_id: str | None = None
    driver_id: str = ""
    line_name: str = ""
    mode: str = ""
    fare: int = 0
    provider: str = ""
    ts: datetime | None = None
    document_id: int | None = None
    stub_id: int | None = None
