"""Tests du référentiel des quartiers d'Abidjan (fusion POI + rattachement arrêts)."""

from quartiers import QUARTIERS_PAR_COMMUNE, normaliser
from routing_engine import get_network


def test_couverture_referentiel():
    """Les 14 communes du Grand Abidjan sont couvertes, avec un volume significatif."""
    assert len(QUARTIERS_PAR_COMMUNE) == 14
    assert sum(len(q) for q in QUARTIERS_PAR_COMMUNE.values()) >= 250


def test_fusion_dans_le_reseau():
    """Les quartiers deviennent des POI valides : arrêt existant, ids et libellés uniques."""
    net = get_network()
    quartiers = [p for p in net.pois.values() if p.get("kind") == "quartier"]
    assert len(quartiers) >= 250
    ids = [p["id"] for p in net.pois.values()]
    labels = [normaliser(p["label"]) for p in net.pois.values()]
    assert len(ids) == len(set(ids))
    assert len(labels) == len(set(labels))
    for p in quartiers:
        assert p["stop_id"] in net.stops
        assert p["stop_name"] == net.stops[p["stop_id"]]["name"]


def test_rattachements_attendus():
    """Les grands quartiers connus tombent sur l'arrêt attendu (règles nommées)."""
    net = get_network()
    q = {p["label"]: p for p in net.pois.values() if p.get("kind") == "quartier"}
    assert q["Angré"]["stop_id"] == "st_angre2"
    assert q["Riviera Palmeraie"]["stop_id"] == "st_riviera3"
    assert q["Deux-Plateaux"]["stop_id"] == "st_2plt_vallon"
    assert q["Zone Industrielle"]["stop_id"] == "st_adjamme_gare"
    # Arrêts réels ajoutés aux positions OpenStreetMap : quartier et
    # géolocalisation tombent désormais sur le même endroit.
    assert net.pois["bonoumin"]["stop_id"] == "st_bonoumin"
    assert q["Anono Village"]["stop_id"] == "st_gare_anono"


def test_scenario_bonoumin_treichville(client):
    """Scénario réel demandé : depuis Riviera Bonoumin, taxi communal jusqu'à la
    gare (Riviera 2 ou 9 Kilo), puis véhicule en commun DIRECT vers Treichville,
    avec possibilité de marcher jusqu'à l'arrêt le plus proche."""
    r = client.post("/api/plan", json={"from_poi": "bonoumin", "to_poi": "treichville"})
    assert r.status_code == 200
    its = r.json()["itineraries"]
    assert len(its) >= 3
    modes = {leg["mode"] for it in its for leg in it["legs"] if leg["type"] == "ride"}
    assert "taxi_communal" in modes
    assert "woro" in modes
    # L'option attendue : taxi Bonoumin → Riviera 2 (200 F) + woro direct (800 F).
    assert any(it["fare"] == 1000 for it in its)
    # L'option de marche jusqu'à un arrêt proche (Bonoumin ↔ Riviera 1 ≈ 850 m).
    assert any(leg["type"] == "walk" for it in its for leg in it["legs"])


def test_communes_sans_arret_restant_cherchables():
    """Koumassi (sans arrêt dans le corpus) reste cherchable, rattachée à un arrêt réel."""
    net = get_network()
    q = [p for p in net.pois.values() if p.get("kind") == "quartier" and p["commune"] == "Koumassi"]
    assert len(q) >= 5
    assert all(p["stop_id"] in net.stops for p in q)


def test_api_pois_enrichis(client):
    d = client.get("/api/pois").json()
    assert len(d) >= 250
    assert all("stop_name" in p and "kind" in p for p in d)


def test_api_plan_depuis_quartier(client):
    r = client.post("/api/plan", json={"from_poi": "q_angre", "to_poi": "cite_administrative"})
    assert r.status_code == 200
    assert len(r.json()["itineraries"]) >= 1


def test_api_plan_par_arret(client):
    """/api/plan accepte un arrêt direct (position actuelle) en plus des POI."""
    r = client.post("/api/plan", json={"from_stop": "st_riviera2", "to_poi": "cite_administrative"})
    assert r.status_code == 200
    d = r.json()
    assert d["from"]["label"] == "Riviera 2"
    assert len(d["itineraries"]) >= 3


def test_api_plan_sans_depart_ou_destination(client):
    r = client.post("/api/plan", json={"to_poi": "cite_administrative"})
    assert r.status_code == 422
