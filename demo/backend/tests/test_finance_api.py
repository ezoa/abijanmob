"""Tests d'intégration du module financier — via l'API, SANS PostgreSQL.

Store mémoire forcé par conftest.py. Couvre les exigences 1 à 4 et 8 à 12 du
cahier des charges (les exigences 5-7, unitaires, sont dans test_tax_engine.py).
"""

from __future__ import annotations

import re
from datetime import date

from fastapi.testclient import TestClient

from finance import tax_engine
from finance.fees import compute_fees

# Paiement type de la démo : Woro Riviera, embarquement Riviera 2 (Cocody),
# destination Cité Administrative (Plateau).
PAY_BODY = {
    "line_name": "Woro Riviera",
    "mode": "woro",
    "fare": 300,
    "provider": "wave",
    "driver_id": "drv_001",
    "line_id": "wo_riviera",
    "stop_id": "st_riviera2",
    "dest_stop_id": "st_plateau_cite",
}

FAC_RE = re.compile(r"^FAC-\d{4}-\d{6}$")
STB_RE = re.compile(r"^STB-\d{4}-\d{6}$")


def _pay(client: TestClient, **overrides) -> dict:
    body = {**PAY_BODY, **overrides}
    r = client.post("/api/payments", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _expected_provision(gross: int, commune: str | None, vehicle_category: str) -> int:
    """Provision fiscale attendue (taxes à la charge du conducteur), moteur pur."""
    rules = [
        tax_engine.parse_rule_row({**r, "id": i})
        for i, r in enumerate(tax_engine.demo_rules(), 1)
    ]
    taxes = tax_engine.applicable_taxes(
        rules,
        on_date=date.today(),
        gross_amount=gross,
        commune=commune,
        vehicle_category=vehicle_category,
    )
    return sum(a for _r, a, k in taxes if tax_engine.is_driver_burden(k))


def _expected_net(gross: int, commune: str | None, vehicle_category: str) -> int:
    """Net attendu, recalculé via le moteur pur (taxes à la charge du conducteur)."""
    payment_fee, platform_fee = compute_fees(gross)
    return gross - payment_fee - platform_fee - _expected_provision(
        gross, commune, vehicle_category
    )


# ----------------------------------------------------------------- chaîne documentaire


def test_payment_generates_receipt_document(client: TestClient):
    """(Test 1) Un paiement confirmé génère une facture/reçu client."""
    pay = _pay(client)
    assert pay["document_id"], "le paiement doit référencer un document client"
    r = client.get(f"/api/customer/documents/{pay['document_id']}")
    assert r.status_code == 200
    doc = r.json()
    assert FAC_RE.match(doc["document_number"])
    assert doc["document_type"] == "receipt"
    assert doc["gross_amount"] == 300
    assert doc["issuer_name"] == "Koffi Assamoi"
    assert doc["issuer_identifier"] == "drv_001"
    assert doc["line_name"] == "Woro Riviera"
    assert doc["origin_name"] == "Riviera 2"
    assert doc["destination_name"] == "Cité Administrative"
    assert doc["commune"] == "Cocody"  # commune d'embarquement (règles communales)
    assert doc["payment_provider"] == "Wave"
    assert doc["ticket_id"] == pay["ticket_id"]


def test_single_stub_per_payment(client: TestClient):
    """(Test 2) Le même paiement génère exactement une souche conducteur."""
    pay = _pay(client)
    r = client.get("/api/driver/drv_001/stubs")
    assert r.status_code == 200
    stubs = [s for s in r.json()["stubs"] if s["payment_id"] == pay["payment_id"]]
    assert len(stubs) == 1, "une seule souche par paiement"
    assert STB_RE.match(stubs[0]["stub_number"])


def test_document_and_stub_share_payment_id(client: TestClient):
    """(Test 3) Facture et souche partagent le même payment_id (et transaction_id)."""
    pay = _pay(client)
    doc = client.get(f"/api/customer/documents/{pay['document_id']}").json()
    r = client.get("/api/driver/drv_001/stubs")
    stub = next(s for s in r.json()["stubs"] if s["payment_id"] == pay["payment_id"])
    assert doc["payment_id"] == stub["payment_id"]
    assert doc["transaction_id"] == stub["transaction_id"]
    assert doc["ticket_id"] == stub["ticket_id"] == pay["ticket_id"]


def test_net_amount_computation(client: TestClient):
    """(Test 4) Montant net conducteur = brut − frais − commission − taxes/provisions."""
    pay = _pay(client)  # woro, embarquement Cocody
    fin = pay["financial"]
    assert fin["gross_amount"] == 300
    assert fin["payment_fee"] == 3  # 1 % (frais de paiement — démo)
    assert fin["platform_fee"] == 5  # 1,5 % arrondi (commission — démo)
    expected_net = _expected_net(300, "Cocody", "woro")
    assert fin["net_amount"] == expected_net
    assert fin["net_amount"] == (
        fin["gross_amount"] - fin["payment_fee"] - fin["platform_fee"] - fin["tax_provision"]
    )
    # La souche raconte la même histoire :
    r = client.get("/api/driver/drv_001/stubs")
    stub = next(s for s in r.json()["stubs"] if s["payment_id"] == pay["payment_id"])
    assert stub["net_amount"] == expected_net
    # Et le gbaka de Koffi (catégorie ciblée par la vignette annuelle démo) :
    pay2 = _pay(client, mode="gbaka", fare=400, line_id="gb_riviera_adjamme")
    assert pay2["financial"]["net_amount"] == _expected_net(400, "Cocody", "gbaka")


def test_numbering_unique_and_formats(client: TestClient):
    """Deux paiements → numéros uniques aux formats documentés."""
    pay1, pay2 = _pay(client), _pay(client)
    assert pay1["document_number"] != pay2["document_number"]
    assert pay1["stub_number"] != pay2["stub_number"]
    assert FAC_RE.match(pay1["document_number"]) and FAC_RE.match(pay2["document_number"])
    assert STB_RE.match(pay1["stub_number"]) and STB_RE.match(pay2["stub_number"])


# ----------------------------------------------------------------- dépenses


def test_expense_appears_in_summary(client: TestClient):
    """(Test 8) Une dépense saisie apparaît dans le résumé financier (et disparaît)."""
    # Conducteur isolé (drv_002) : aucune recette seedée chez lui.
    today = date.today().isoformat()
    r = client.post(
        "/api/driver/drv_002/expenses",
        json={"category": "fuel", "amount": 2500, "description": "Essence (démo)", "expense_date": today},
    )
    assert r.status_code == 201, r.text
    expense = r.json()
    assert expense["amount"] == 2500 and expense["category"] == "fuel"

    summary = client.get("/api/driver/drv_002/financial-summary").json()
    assert summary["today"]["expenses"] == 2500
    assert summary["today"]["estimated_net_income"] == -2500  # aucune recette chez drv_002

    # La dépense est listée, filtrable par catégorie, puis supprimable :
    lst = client.get("/api/driver/drv_002/expenses").json()
    assert lst["total"] == 2500 and lst["count"] == 1
    filt = client.get("/api/driver/drv_002/expenses", params={"category": "tires"}).json()
    assert filt["count"] == 0
    r = client.delete(f"/api/driver/drv_002/expenses/{expense['id']}")
    assert r.status_code == 204
    summary = client.get("/api/driver/drv_002/financial-summary").json()
    assert summary["today"]["expenses"] == 0
    # Double suppression → 404 explicite :
    assert client.delete(f"/api/driver/drv_002/expenses/{expense['id']}").status_code == 404


def test_expense_validation(client: TestClient):
    """Catégorie inconnue → 422 ; montant invalide → 422."""
    r = client.post(
        "/api/driver/drv_002/expenses", json={"category": "helicopter", "amount": 100}
    )
    assert r.status_code == 422
    r = client.post("/api/driver/drv_002/expenses", json={"category": "fuel", "amount": -5})
    assert r.status_code == 422


# ----------------------------------------------------------------- clôtures


def test_daily_closure_idempotent(client: TestClient):
    """(Test 9) Une double clôture journalière ne crée pas de doublon."""
    today = date.today().isoformat()
    r1 = client.post("/api/driver/drv_002/daily-closures", json={"closure_date": today})
    assert r1.status_code == 201, r1.text
    closure1 = r1.json()
    assert closure1["payment_count"] == 0  # drv_002 n'a pas de recettes

    r2 = client.post("/api/driver/drv_002/daily-closures", json={"closure_date": today})
    assert r2.status_code == 200  # déjà clôturée → pas de doublon
    closure2 = r2.json()
    assert closure2["already_closed"] is True
    assert closure2["closure_number"] == closure1["closure_number"]

    lst = client.get("/api/driver/drv_002/daily-closures").json()
    assert lst["count"] == 1
    assert {c["closure_date"] for c in lst["closures"]} == {today}


def test_closure_amounts_match_stubs(client: TestClient):
    """La clôture récapitule les souches du jour (recettes, frais, net, nombre)."""
    _pay(client)  # une recette live chez drv_001
    today = date.today().isoformat()
    r = client.post("/api/driver/drv_001/daily-closures", json={"closure_date": today})
    assert r.status_code == 201
    closure = r.json()
    summary = client.get("/api/driver/drv_001/financial-summary").json()
    assert closure["gross_revenue"] == summary["today"]["gross_revenue"]
    assert closure["payment_count"] == summary["today"]["payment_count"]
    assert closure["fees"] == summary["today"]["payment_fees"] + summary["today"]["commissions"]
    assert closure["tax_provisions"] == summary["today"]["tax_provisions"]


# ----------------------------------------------------------------- vérification / FNE


def test_qr_verification_finds_document(client: TestClient):
    """(Test 10) Le QR de vérification retrouve le bon document (jeton valide)."""
    pay = _pay(client)
    payload = pay["verify_payload"]
    assert payload.startswith("ABJMOB|VERIF|")
    parts = payload.split("|")
    assert len(parts) == 4  # ABJMOB | VERIF | numéro de document | jeton
    token = parts[-1]
    assert parts[2] == pay["document_number"]
    r = client.get(
        f"/api/customer/documents/{pay['document_id']}/verify", params={"token": token}
    )
    assert r.status_code == 200
    verification = r.json()
    assert verification["valid"] is True
    assert verification["document_number"] == pay["document_number"]
    assert verification["ticket_id"] == pay["ticket_id"]
    # Mauvais jeton → vérification négative (pas une erreur serveur) :
    r = client.get(
        f"/api/customer/documents/{pay['document_id']}/verify",
        params={"token": "0" * 16},
    )
    assert r.status_code == 200
    assert r.json()["valid"] is False
    # Document inconnu → 404 :
    assert client.get("/api/customer/documents/99999999").status_code == 404
    assert client.get("/api/customer/documents/99999999/verify", params={"token": token}).status_code == 404


def test_document_states_not_fne_certified(client: TestClient):
    """(Test 11) Le document indique clairement qu'il n'est PAS certifié FNE."""
    pay = _pay(client)
    doc = client.get(f"/api/customer/documents/{pay['document_id']}").json()
    assert doc["fne_status"] == "not_certified_demo"
    assert doc["fne_reference"] is None
    assert "non activée" in doc["fne_message"]
    assert doc["fne_status"] != "certified"


# ----------------------------------------------------------------- contrats existants


def test_legacy_payment_contract_preserved(client: TestClient):
    """(Test 12a) POST /api/payments garde son contrat + enrichissements financiers."""
    # Corps minimal, comme le smoke test (sans line_id/stop_id) :
    pay = _pay(client, line_name="Woro Riviera", line_id=None, stop_id=None, dest_stop_id=None)
    for key in ("ticket_id", "created_at", "time_hm", "line_name", "mode", "fare", "provider",
                "driver_id", "status"):
        assert key in pay, f"clé historique manquante : {key}"
    assert pay["status"] == "PAYÉ (simulation)"
    assert re.match(r"^ABJ-[0-9A-F]{6}$", pay["ticket_id"])
    assert isinstance(pay["fare"], int)
    # Nouvelles informations financières, en complément :
    assert "document_id" in pay and "verification_token" in pay
    assert "transaction_id" in pay and "financial" in pay
    # Sans arrêt/ligne : pas de taxes communales, mais les règles nationales s'appliquent
    assert pay["financial"]["tax_provision"] == _expected_provision(300, None, "woro")
    assert pay["financial"]["net_amount"] == _expected_net(300, None, "woro")


def test_legacy_driver_receipts_contract_preserved(client: TestClient):
    """(Test 12b) GET /api/driver/{id}/receipts garde son contrat."""
    _pay(client)
    r = client.get("/api/driver/drv_001/receipts")
    assert r.status_code == 200
    data = r.json()
    assert data["driver"]["name"] == "Koffi Assamoi"
    assert data["count"] >= 13  # 12 recettes seedées + au moins le paiement live
    assert data["total"] >= 4700  # 4 400 F seedés + paiements live
    assert data["receipts"][0]["time_hm"]
    assert "by_provider" in data and "no_change_given" in data
    # Conducteur inconnu → 404 :
    assert client.get("/api/driver/drv_999/receipts").status_code == 404


def test_health_and_rules(client: TestClient):
    """Santé + règles fiscales exposées (toutes de démonstration, désactivables)."""
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["finance_store"] == "memory"  # tests sans PostgreSQL
    rules = client.get("/api/tax-rules").json()
    codes = {r["code"] for r in rules["rules"]}
    assert "DEMO_COCODY_COURSE" in codes and "DEMO_TAXE_EXPIREE" in codes
    assert all(r["is_official"] is False for r in rules["rules"])
    assert "Estimation indicative" in rules["disclaimer"]


def test_stub_filters(client: TestClient):
    """Filtres souches : opérateur, statut de reversement ; erreurs 422/404."""
    _pay(client, provider="moov")  # Moov Money
    r = client.get("/api/driver/drv_001/stubs", params={"provider": "Moov Money"})
    assert r.status_code == 200
    stubs = r.json()["stubs"]
    assert stubs and all(s["provider"] == "Moov Money" for s in stubs)
    r = client.get("/api/driver/drv_001/stubs", params={"provider": "Wave"})
    assert all(s["provider"] == "Wave" for s in r.json()["stubs"])
    # Aucune souche réglée en mémoire (pas de backfill sans PostgreSQL) :
    r = client.get("/api/driver/drv_001/stubs", params={"settlement_status": "settled"})
    assert r.json()["count"] == 0
    r = client.get("/api/driver/drv_001/stubs", params={"settlement_status": "nope"})
    assert r.status_code == 422
    # Détail d'une souche avec sa décomposition fiscale :
    lst = client.get("/api/driver/drv_001/stubs").json()["stubs"]
    detail = client.get(f"/api/driver/drv_001/stubs/{lst[0]['id']}")
    assert detail.status_code == 200
    assert "taxes" in detail.json()
    assert client.get("/api/driver/drv_001/stubs/999999").status_code == 404
    assert client.get("/api/driver/drv_999/stubs").status_code == 404
