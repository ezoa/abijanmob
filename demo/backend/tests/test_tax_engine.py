"""Tests unitaires du moteur fiscal (pur — aucune base requise).

Couvre : règle inactive jamais appliquée (5), règle expirée jamais appliquée (6),
règle communale limitée à sa commune (7), arrondis et provisions estimatives.
"""

from __future__ import annotations

from datetime import date

from finance import tax_engine


def _rules_by_code() -> dict:
    return {r["code"]: tax_engine.parse_rule_row({**r, "id": i}) for i, r in enumerate(tax_engine.demo_rules(), 1)}


def test_demo_rules_are_not_official():
    """Toutes les règles livrées sont des règles de démonstration désactivables."""
    for r in tax_engine.demo_rules():
        assert r["is_official"] is False
        assert r["label"].startswith("Règle de démonstration")


def test_inactive_rule_is_never_applied():
    """(Test 5) Une règle désactivée ne s'applique pas — même dans sa commune."""
    rules = _rules_by_code()
    adjamme = rules["DEMO_ADJAMME_COURSE"]
    assert adjamme.enabled is False
    assert not tax_engine.rule_applies(adjamme, on_date=date(2026, 9, 14), commune="Adjamé")
    # Même dans une liste, elle n'est jamais retenue :
    applicable = tax_engine.applicable_taxes(
        list(rules.values()), on_date=date(2026, 9, 14), gross_amount=400, commune="Adjamé"
    )
    assert all(rule.code != "DEMO_ADJAMME_COURSE" for rule, _amount, _kind in applicable)


def test_expired_rule_is_never_applied():
    """(Test 6) Une règle hors dates d'effet ne s'applique pas."""
    rules = _rules_by_code()
    expired = rules["DEMO_TAXE_EXPIREE"]
    assert expired.effective_to == date(2025, 12, 31)
    assert not tax_engine.rule_applies(expired, on_date=date(2026, 9, 14))
    # En 2025 elle aurait été applicable :
    assert tax_engine.rule_applies(expired, on_date=date(2025, 6, 1))


def test_communal_rule_applies_only_to_its_commune():
    """(Test 7) Une règle communale ne s'applique qu'à la bonne commune."""
    rules = _rules_by_code()
    cocody = rules["DEMO_COCODY_COURSE"]
    assert tax_engine.rule_applies(cocody, on_date=date(2026, 9, 14), commune="Cocody")
    assert not tax_engine.rule_applies(cocody, on_date=date(2026, 9, 14), commune="Plateau")
    assert not tax_engine.rule_applies(cocody, on_date=date(2026, 9, 14), commune=None)


def test_vehicle_category_scoping():
    """La provision vignette annuelle ne vise que les gbakas."""
    rules = _rules_by_code()
    vignette = rules["DEMO_VIGNETTE_ANNUELLE"]
    assert tax_engine.rule_applies(vignette, on_date=date(2026, 9, 14), vehicle_category="gbaka")
    assert not tax_engine.rule_applies(vignette, on_date=date(2026, 9, 14), vehicle_category="woro")


def test_percentage_rounding_and_kinds():
    """Arrondi commercial au franc + natures customer/operator."""
    rules = _rules_by_code()
    etat = rules["DEMO_ETAT_COURSE"]  # 1,5 % opérateur
    tva = rules["DEMO_TVA_TRANSPORT"]  # 2 % client
    amount, kind = tax_engine.compute_tax(etat, 300)  # 4,5 F → 5 F
    assert (amount, kind) == (5, "operator_tax")
    amount, kind = tax_engine.compute_tax(tva, 300)  # 6 F exact
    assert (amount, kind) == (6, "customer_collected_tax")


def test_fixed_provisions_are_estimates():
    """Les taxes jour/mois/année deviennent des provisions réparties par course."""
    rules = _rules_by_code()
    mensuelle = rules["DEMO_CIRCULATION_MENSUELLE"]  # 12 000 F / 1 040 courses
    amount, kind = tax_engine.compute_tax(mensuelle, 400)
    assert (amount, kind) == (12, "estimated_provision")  # 11,54 → 12
    annuelle = rules["DEMO_VIGNETTE_ANNUELLE"]  # 36 000 F / 12 480 courses
    amount, kind = tax_engine.compute_tax(annuelle, 400)
    assert (amount, kind) == (3, "estimated_provision")  # 2,88 → 3
    # Une provision n'est JAMAIS un prélèvement exigible par course :
    assert tax_engine.is_driver_burden("estimated_provision")
    assert not tax_engine.is_driver_burden("customer_collected_tax")


def test_no_hardcoded_official_rates():
    """Aucun taux officiel ivoirien n'est codé en dur : tout vient des règles."""
    # L'ancien prélèvement de 4 % (modifié par l'annexe fiscale 2026) est absent.
    codes = {r["code"] for r in tax_engine.demo_rules()}
    rates = {r["rate"] for r in tax_engine.demo_rules() if r["calculation_type"] == "percentage"}
    assert 4.0 not in rates
    assert len(codes) == 7
