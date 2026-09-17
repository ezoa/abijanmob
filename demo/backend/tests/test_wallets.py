"""Tests du module portefeuilles (simulation) : déverrouillage, répartition
multi-comptes, débit, journal, réinitialisation. Tout en mémoire, sans base."""

from wallets import SOLDES_INITIAUX


def _reset(client):
    r = client.post("/api/wallets/reset")
    assert r.status_code == 200


def _unlock(client, pin="0000"):
    r = client.post("/api/wallets/unlock", json={"pin": pin})
    assert r.status_code == 200
    return r.json()


def test_unlock_code_invalide(client):
    """Le code doit faire exactement 4 chiffres."""
    assert client.post("/api/wallets/unlock", json={"pin": "12"}).status_code == 400
    assert client.post("/api/wallets/unlock", json={"pin": "abcd"}).status_code == 400
    assert client.post("/api/wallets/unlock", json={"pin": ""}).status_code == 400


def test_unlock_expose_les_soldes(client):
    _reset(client)
    d = _unlock(client)
    assert set(d["balances"]) == set(SOLDES_INITIAUX)
    assert d["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"]
    assert d["balances"]["wave"]["label"] == "Wave"
    assert d["total"] == sum(SOLDES_INITIAUX.values())


def test_paiement_reparti(client):
    """Un paiement soldé par plusieurs comptes : débit exact + journal + billet."""
    _reset(client)
    r = client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 300,
            "driver_id": "drv_001",
            "splits": [
                {"provider": "wave", "amount": 200},
                {"provider": "orange", "amount": 100},
            ],
        },
    )
    assert r.status_code == 200
    t = r.json()
    assert t["status"] == "PAYÉ (simulation)"
    assert t["provider"] == "Wave + Orange Money"
    assert [(s["provider"], s["amount"]) for s in t["splits"]] == [
        ("Wave", 200),
        ("Orange Money", 100),
    ]
    # Soldes débités d'exactement les montants alloués.
    d = _unlock(client)
    assert d["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"] - 200
    assert d["balances"]["orange"]["balance"] == SOLDES_INITIAUX["orange"] - 100
    assert d["balances"]["mtn"]["balance"] == SOLDES_INITIAUX["mtn"]
    # Journal : deux mouvements liés au billet.
    tx = client.get("/api/wallets/transactions").json()["transactions"]
    du_billet = [x for x in tx if x["ticket_id"] == t["ticket_id"]]
    assert {(x["provider"], x["amount"]) for x in du_billet} == {("wave", 200), ("orange", 100)}


def test_paiement_reparti_compte_unique(client):
    """Une répartition à un seul compte se comporte comme le chemin historique."""
    _reset(client)
    r = client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 300,
            "driver_id": "drv_001",
            "splits": [{"provider": "mtn", "amount": 300}],
        },
    )
    assert r.status_code == 200
    assert r.json()["provider"] == "MTN MoMo"


def test_paiement_reparti_somme_incoherente(client):
    _reset(client)
    r = client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 300,
            "driver_id": "drv_001",
            "splits": [{"provider": "wave", "amount": 200}],
        },
    )
    assert r.status_code == 400
    # Aucun débit en cas de refus.
    assert _unlock(client)["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"]


def test_paiement_reparti_solde_insuffisant(client):
    _reset(client)
    r = client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 500,
            "driver_id": "drv_001",
            "splits": [{"provider": "wave", "amount": 500}],
        },
    )
    assert r.status_code == 400
    assert _unlock(client)["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"]


def test_paiement_reparti_operateur_inconnu_ou_double(client):
    _reset(client)
    base = {"line_name": "Woro Riviera", "mode": "woro", "fare": 400, "driver_id": "drv_001"}
    r = client.post(
        "/api/payments",
        json={**base, "splits": [{"provider": "visa", "amount": 400}]},
    )
    assert r.status_code == 400
    r = client.post(
        "/api/payments",
        json={
            **base,
            "splits": [
                {"provider": "wave", "amount": 200},
                {"provider": "wave", "amount": 200},
            ],
        },
    )
    assert r.status_code == 400


def test_paiement_legacy_sans_repartition_ne_debite_pas(client):
    """Le chemin historique (provider seul) reste intact et ne touche pas aux
    portefeuilles : contrat préservé pour les clients existants."""
    _reset(client)
    r = client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 300,
            "provider": "wave",
            "driver_id": "drv_001",
        },
    )
    assert r.status_code == 200
    assert r.json()["provider"] == "Wave"
    assert "splits" not in r.json()
    assert _unlock(client)["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"]


def test_reset_restaure_les_soldes(client):
    _reset(client)
    client.post(
        "/api/payments",
        json={
            "line_name": "Woro Riviera",
            "mode": "woro",
            "fare": 300,
            "driver_id": "drv_001",
            "splits": [
                {"provider": "wave", "amount": 200},
                {"provider": "orange", "amount": 100},
            ],
        },
    )
    d = client.post("/api/wallets/reset").json()
    assert d["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"]
    assert d["balances"]["orange"]["balance"] == SOLDES_INITIAUX["orange"]


def test_historique_seed_present(client):
    """L'historique de démonstration alimente « Mes dépenses » dès le départ."""
    tx = client.get("/api/wallets/transactions").json()["transactions"]
    assert any(x["kind"] == "seed" for x in tx)
    assert all("line_name" in x for x in tx)


def test_rechargement_credite_le_portefeuille(client):
    """Recharger approvisionne le portefeuille virtuel (simulation : le « vrai »
    compte de l'opérateur n'est jamais débité) et journalise le mouvement."""
    _reset(client)
    r = client.post("/api/wallets/topup", json={"pin": "0000", "provider": "wave", "amount": 1000})
    assert r.status_code == 200
    d = r.json()
    assert d["credited"] == 1000
    assert d["balances"]["wave"]["balance"] == SOLDES_INITIAUX["wave"] + 1000
    assert "AbidjanMob-Wave" in d["message"]
    tx = client.get("/api/wallets/transactions").json()["transactions"]
    assert any(x["kind"] == "topup" and x["amount"] == 1000 for x in tx)


def test_rechargement_puis_paiement_impossible_possible(client):
    """Un rechargement permet de solder un trajet que le solde initial refuse."""
    _reset(client)
    corps = {
        "line_name": "Woro Riviera",
        "mode": "woro",
        "fare": 1200,
        "driver_id": "drv_001",
        "splits": [{"provider": "wave", "amount": 1200}],
    }
    assert client.post("/api/payments", json=corps).status_code == 400
    assert (
        client.post(
            "/api/wallets/topup", json={"pin": "0000", "provider": "wave", "amount": 1000}
        ).status_code
        == 200
    )
    assert client.post("/api/payments", json=corps).status_code == 200


def test_rechargement_validations(client):
    _reset(client)
    assert (
        client.post(
            "/api/wallets/topup", json={"pin": "00", "provider": "wave", "amount": 500}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/wallets/topup", json={"pin": "0000", "provider": "visa", "amount": 500}
        ).status_code
        == 400
    )
