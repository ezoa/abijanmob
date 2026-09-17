"""Moteur fiscal — lecture EXCLUSIVE des règles actives de `tax_rules`.

Aucun taux ivoirien n'est codé en dur dans la logique métier : le calcul lit
uniquement les règles configurées (date d'effet, commune, catégorie de véhicule,
régime, fréquence, type de calcul). Les règles livrées avec le prototype sont des
« Règles de démonstration » (is_official=false), désactivables à volonté.

NB annexe fiscale 2026 : l'ancien prélèvement de 4 % sur les conducteurs de
plateformes n'est PAS réutilisé — les taux ci-dessous sont purement fictifs.

Les taxes de fréquence supérieure à la course (journalière / mensuelle /
annuelle) sont des PROVISIONS ESTIMATIVES réparties par course : elles ne sont
JAMAIS présentées comme des prélèvements légalement exigibles par course.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Hypothèses de répartition des provisions (valeurs de démonstration documentées,
# utilisées uniquement pour ramener une taxe jour/mois/année à une provision par
# course) :
ASSUMED_TRIPS_PER_DAY = 40
ASSUMED_WORK_DAYS_PER_MONTH = 26
ASSUMED_TRIPS_PER_MONTH = ASSUMED_TRIPS_PER_DAY * ASSUMED_WORK_DAYS_PER_MONTH  # 1 040
ASSUMED_TRIPS_PER_YEAR = ASSUMED_TRIPS_PER_MONTH * 12  # 12 480

TAX_DISCLAIMER = (
    "Estimation indicative fondée sur les règles configurées. À confirmer par "
    "l'administration fiscale ou communale compétente."
)


@dataclass
class TaxRule:
    """Règle fiscale versionnée (table tax_rules)."""

    id: int
    code: str
    label: str
    authority_type: str  # communal | state | other
    authority_name: str
    commune: str | None
    vehicle_category: str | None
    operator_regime: str | None
    calculation_type: str  # percentage | fixed_per_trip | fixed_daily | ...
    rate: float  # en pourcentage (calculation_type=percentage)
    fixed_amount: int  # en FCFA (calculation_type=fixed_*)
    frequency: str  # per_trip | daily | monthly | annual
    effective_from: date | None
    effective_to: date | None
    legal_reference: str | None
    is_official: bool
    enabled: bool
    tax_target: str = "operator"  # customer | operator (colonne additionnelle)


def rule_applies(
    rule: TaxRule,
    *,
    on_date: date,
    commune: str | None = None,
    vehicle_category: str | None = None,
    operator_regime: str | None = None,
) -> bool:
    """Une règle s'applique si : activée, dans ses dates d'effet, et ciblée sur
    la commune / catégorie de véhicule / régime de la transaction (NULL = tous)."""
    if not rule.enabled:
        return False
    if rule.effective_from is not None and on_date < rule.effective_from:
        return False
    if rule.effective_to is not None and on_date > rule.effective_to:
        return False
    if rule.commune and rule.commune != commune:
        return False
    if rule.vehicle_category and rule.vehicle_category != vehicle_category:
        return False
    if rule.operator_regime and rule.operator_regime != operator_regime:
        return False
    return True


def compute_tax(rule: TaxRule, gross_amount: int) -> tuple[int, str]:
    """(montant arrondi au franc, nature du calcul) pour une règle applicable.

    - percentage / fixed_per_trip → taxe par course : à la charge du client
      (customer_collected_tax, figure sur la facture) ou de l'exploitant
      (operator_tax, figure sur la souche) selon `tax_target` ;
    - fixed_daily / fixed_monthly / fixed_annual → provision estimative répartie
      sur le nombre de courses supposé (jamais exigible par course).
    """
    if rule.calculation_type == "percentage":
        amount = int(gross_amount * rule.rate / 100.0 + 0.5)
        kind = "customer_collected_tax" if rule.tax_target == "customer" else "operator_tax"
    elif rule.calculation_type == "fixed_per_trip":
        amount = rule.fixed_amount
        kind = "customer_collected_tax" if rule.tax_target == "customer" else "operator_tax"
    elif rule.calculation_type == "fixed_daily":
        amount = int(rule.fixed_amount / ASSUMED_TRIPS_PER_DAY + 0.5)
        kind = "estimated_provision"
    elif rule.calculation_type == "fixed_monthly":
        amount = int(rule.fixed_amount / ASSUMED_TRIPS_PER_MONTH + 0.5)
        kind = "estimated_provision"
    elif rule.calculation_type == "fixed_annual":
        amount = int(rule.fixed_amount / ASSUMED_TRIPS_PER_YEAR + 0.5)
        kind = "estimated_provision"
    else:
        raise ValueError(f"Type de calcul fiscal inconnu : {rule.calculation_type!r}")
    return max(0, amount), kind


def applicable_taxes(
    rules: list[TaxRule],
    *,
    on_date: date,
    gross_amount: int,
    commune: str | None = None,
    vehicle_category: str | None = None,
    operator_regime: str | None = None,
) -> list[tuple[TaxRule, int, str]]:
    """Toutes les règles applicables à une transaction, avec montant et nature."""
    out = []
    for rule in rules:
        if rule_applies(
            rule,
            on_date=on_date,
            commune=commune,
            vehicle_category=vehicle_category,
            operator_regime=operator_regime,
        ):
            amount, kind = compute_tax(rule, gross_amount)
            out.append((rule, amount, kind))
    return out


def is_driver_burden(kind: str) -> bool:
    """Une taxe pèse-t-elle sur le net conducteur (souche) ?"""
    return kind in ("operator_tax", "estimated_provision")


# --------------------------------------------------------------------- seed démo

_DEMO_LEGAL_REF = "Règle fictive de démonstration : aucun texte officiel"


def demo_rules() -> list[dict]:
    """Règles de démonstration (is_official=false) livrées avec le prototype.

    Couverture volontaire : pourcentage client (facture), pourcentage opérateur,
    taxe communale par course, taxe communale DÉSACTIVÉE, provision annuelle
    ciblée gbaka, provision mensuelle toutes catégories, règle EXPIRÉE.
    """
    return [
        {
            "code": "DEMO_ETAT_COURSE",
            "label": "Règle de démonstration : contribution étatique par course (1,5 %)",
            "authority_type": "state",
            "authority_name": "État (fictif, démonstration)",
            "commune": None,
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "percentage",
            "tax_target": "operator",
            "rate": 1.5,
            "fixed_amount": 0,
            "frequency": "per_trip",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
        {
            "code": "DEMO_TVA_TRANSPORT",
            "label": "Règle de démonstration : TVA transport (2 %, incluse dans le tarif)",
            "authority_type": "state",
            "authority_name": "État (fictif, démonstration)",
            "commune": None,
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "percentage",
            "tax_target": "customer",
            "rate": 2.0,
            "fixed_amount": 0,
            "frequency": "per_trip",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
        {
            "code": "DEMO_COCODY_COURSE",
            "label": "Règle de démonstration : taxe communale par course (Cocody)",
            "authority_type": "communal",
            "authority_name": "Commune de Cocody (fictive, démonstration)",
            "commune": "Cocody",
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "fixed_per_trip",
            "tax_target": "operator",
            "rate": 0,
            "fixed_amount": 25,
            "frequency": "per_trip",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
        {
            "code": "DEMO_ADJAMME_COURSE",
            "label": "Règle de démonstration : taxe communale par course (Adjamé, désactivée)",
            "authority_type": "communal",
            "authority_name": "Commune d'Adjamé (fictive, démonstration)",
            "commune": "Adjamé",
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "fixed_per_trip",
            "tax_target": "operator",
            "rate": 0,
            "fixed_amount": 20,
            "frequency": "per_trip",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": False,  # désactivée : jamais appliquée
        },
        {
            "code": "DEMO_VIGNETTE_ANNUELLE",
            "label": "Règle de démonstration : provision vignette annuelle (gbaka)",
            "authority_type": "state",
            "authority_name": "État (fictif, démonstration)",
            "commune": None,
            "vehicle_category": "gbaka",
            "operator_regime": None,
            "calculation_type": "fixed_annual",
            "tax_target": "operator",
            "rate": 0,
            "fixed_amount": 36000,
            "frequency": "annual",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
        {
            "code": "DEMO_CIRCULATION_MENSUELLE",
            "label": "Règle de démonstration : provision taxe mensuelle de circulation",
            "authority_type": "state",
            "authority_name": "État (fictif, démonstration)",
            "commune": None,
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "fixed_monthly",
            "tax_target": "operator",
            "rate": 0,
            "fixed_amount": 12000,
            "frequency": "monthly",
            "effective_from": date(2026, 1, 1),
            "effective_to": date(2026, 12, 31),
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
        {
            "code": "DEMO_TAXE_EXPIREE",
            "label": "Règle de démonstration : taxe expirée (2025, jamais appliquée)",
            "authority_type": "state",
            "authority_name": "État (fictif, démonstration)",
            "commune": None,
            "vehicle_category": None,
            "operator_regime": None,
            "calculation_type": "percentage",
            "tax_target": "operator",
            "rate": 2.0,
            "fixed_amount": 0,
            "frequency": "per_trip",
            "effective_from": date(2025, 1, 1),
            "effective_to": date(2025, 12, 31),  # expirée depuis le 31/12/2025
            "legal_reference": _DEMO_LEGAL_REF,
            "is_official": False,
            "enabled": True,
        },
    ]


def parse_rule_row(row: dict) -> TaxRule:
    """Construit un TaxRule depuis une ligne de store (dict)."""
    return TaxRule(
        id=row["id"],
        code=row["code"],
        label=row["label"],
        authority_type=row["authority_type"],
        authority_name=row["authority_name"],
        commune=row.get("commune"),
        vehicle_category=row.get("vehicle_category"),
        operator_regime=row.get("operator_regime"),
        calculation_type=row["calculation_type"],
        rate=float(row.get("rate") or 0),
        fixed_amount=int(row.get("fixed_amount") or 0),
        frequency=row.get("frequency") or "per_trip",
        effective_from=row.get("effective_from"),
        effective_to=row.get("effective_to"),
        legal_reference=row.get("legal_reference"),
        is_official=bool(row.get("is_official", False)),
        enabled=bool(row.get("enabled", True)),
        tax_target=row.get("tax_target") or "operator",
    )
