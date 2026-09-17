"""Tests des bilans périodiques : conducteur (jour/semaine/mois/trimestre) et
passager (dépenses par période). Tout en mémoire, sans base."""

CHAMPS_PERIODE = {
    "gross_revenue",
    "payment_count",
    "payment_fees",
    "commissions",
    "tax_provisions",
    "expenses",
    "estimated_net_income",
}


def test_bilan_conducteur_toutes_periodes(client):
    """financial-summary expose désormais jour + semaine + mois + trimestre,
    avec les mêmes champs pour chaque période (extension additive)."""
    d = client.get("/api/driver/drv_001/financial-summary").json()
    for bloc in ("today", "week", "month", "quarter"):
        assert bloc in d, f"bloc manquant : {bloc}"
        assert CHAMPS_PERIODE <= set(d[bloc]), f"champs manquants dans {bloc}"
    # Le trimestre couvre le mois, qui couvre aujourd'hui (au sens des dates).
    assert d["quarter"]["from"] <= d["month"]["from"] <= d["today"]["date"]
    # Cohérence arithmétique sur chaque période.
    for bloc in ("today", "week", "month", "quarter"):
        b = d[bloc]
        attendu = (
            b["gross_revenue"]
            - b["payment_fees"]
            - b["commissions"]
            - b["tax_provisions"]
            - b["expenses"]
        )
        assert b["estimated_net_income"] == attendu


def test_bilan_passager_par_periode(client):
    """spending-summary agrège le journal : périodes, totaux, par opérateur."""
    d = client.get("/api/wallets/spending-summary").json()
    assert set(d["periods"]) == {"day", "week", "month", "quarter", "all"}
    # L'historique seedé (8 paiements sur les 6 derniers jours) alimente la semaine.
    assert d["periods"]["week"]["count"] >= 8
    assert d["periods"]["all"]["count"] >= d["periods"]["week"]["count"]
    assert d["periods"]["all"]["total"] >= d["periods"]["week"]["total"]
    # Répartition par opérateur cohérente avec le total.
    for p in d["periods"].values():
        assert sum(p["by_provider"].values()) == p["total"]


def test_bilan_passager_paiement_en_direct(client):
    """Un paiement fait maintenant apparaît immédiatement dans le bilan du jour."""
    d_avant = client.get("/api/wallets/spending-summary").json()
    client.post("/api/wallets/reset")
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
    d_apres = client.get("/api/wallets/spending-summary").json()
    assert (
        d_apres["periods"]["day"]["total"] == d_avant["periods"]["day"]["total"] + 300
    )
    assert d_apres["periods"]["all"]["total"] == d_avant["periods"]["all"]["total"] + 300
    assert d_apres["periods"]["day"]["by_provider"].get("Wave", 0) >= 200


def test_bilan_passager_ignore_les_rechargements(client):
    """Un rechargement n'est pas une dépense de transport : les bilans ne bougent pas."""
    avant = client.get("/api/wallets/spending-summary").json()
    r = client.post("/api/wallets/topup", json={"pin": "0000", "provider": "mtn", "amount": 5000})
    assert r.status_code == 200
    apres = client.get("/api/wallets/spending-summary").json()
    assert apres["periods"]["all"]["total"] == avant["periods"]["all"]["total"]
    assert apres["periods"]["all"]["count"] == avant["periods"]["all"]["count"]
