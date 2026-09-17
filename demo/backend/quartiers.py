"""Quartiers d'Abidjan pour la recherche départ / destination.

Enrichit les 14 POI du corpus pilote avec le référentiel des quartiers du Grand
Abidjan (14 communes, ~260 quartiers). Chaque quartier est rattaché à un arrêt
du corpus :
1. règle nommée pour les grands quartiers desservis (Riviera, Angré, II
   Plateaux, Zone 4, gares...) ;
2. sinon arrêt de sa commune le plus proche du centre de commune ;
3. sinon (commune sans arrêt : Koumassi, Port-Bouët, Songon, Anyama,
   Bingerville, Brofodoumé) arrêt le plus proche parmi tous.
Les libellés des POI du corpus priment : un quartier homonyme n'est pas ajouté
en double. Les rattachements sont INDICATIFS (prototype) : l'arrêt retenu est
toujours affiché dans l'interface.
"""

from __future__ import annotations

import math
import unicodedata

# ------------------------------------------------------------------ référentiel

# Quartier → commune (référentiel de base, variantes orthographiques incluses).
_BASE: dict[str, str] = {
    # COCODY
    "Riviera 1": "Cocody",
    "Riviera 2": "Cocody",
    "Riviera 3": "Cocody",
    "Riviera 4": "Cocody",
    "Riviera 5": "Cocody",
    "Riviéra 1": "Cocody",
    "Riviéra 2": "Cocody",
    "Riviéra 3": "Cocody",
    "Riviéra 4": "Cocody",
    "Riviéra 5": "Cocody",
    "Riviera Bonoumin": "Cocody",
    "Riviera Golf": "Cocody",
    "Riviera Palmeraie": "Cocody",
    "Riviera Allabra": "Cocody",
    "Riviera Sideci": "Cocody",
    "Riviera Beach": "Cocody",
    "Riviera M'Badon": "Cocody",
    "Riviéra Bonoumin": "Cocody",
    "Riviéra Golf": "Cocody",
    "Riviéra Palmeraie": "Cocody",
    "Palmeraie": "Cocody",
    "Palmeraie Triangle": "Cocody",
    "Deux Plateaux": "Cocody",
    "2 Plateaux": "Cocody",
    "Deux-Plateaux": "Cocody",
    "2-Plateaux": "Cocody",
    "Le Vallon": "Cocody",
    "Les Vallons": "Cocody",
    "Vallons": "Cocody",
    "Angré": "Cocody",
    "Angré Extension": "Cocody",
    "Bonoumin": "Cocody",
    "Danga Nord": "Cocody",
    "Danga Sud": "Cocody",
    "Cocody Danga": "Cocody",
    "Ambassade": "Cocody",
    "Cocody Ambassades": "Cocody",
    "Attoban": "Cocody",
    "Anono Village": "Cocody",
    "Faya": "Cocody",
    "Blockhaus": "Cocody",
    "Blockhauss": "Cocody",
    "Aghien": "Cocody",
    "Mbadon": "Cocody",
    "M'Badon": "Cocody",
    "M'pouto": "Cocody",
    "M’pouto": "Cocody",
    "Mpouto": "Cocody",
    "Cocody Village": "Cocody",
    "Cocody centre": "Cocody",
    "Université": "Cocody",
    "Sideci": "Cocody",
    "Jardin de la Riviera": "Cocody",
    "Dokui": "Cocody",
    "Plateau Dokui": "Cocody",
    "SCI Les Rosiers": "Cocody",
    "Les Rosiers": "Cocody",
    "Rosier": "Cocody",
    "Rosier 4e Programme": "Cocody",
    "Genie 2000": "Cocody",
    "Génie 2000": "Cocody",
    "Les Perles": "Cocody",
    "Les Versants": "Cocody",
    "Akouédo": "Cocody",
    "Akouedo": "Cocody",
    "Mpouto Village": "Cocody",
    # YOPOUGON
    "Yopougon": "Yopougon",
    "Niangon": "Yopougon",
    "Niangon Nord": "Yopougon",
    "Niangon Sud": "Yopougon",
    "Yopougon Attié": "Yopougon",
    "Yopougon Selmer": "Yopougon",
    "Selmer": "Yopougon",
    "Kouté": "Yopougon",
    "Banco Nord": "Yopougon",
    "Banco Sud": "Yopougon",
    "Banco": "Attécoubé",
    "Wassakara": "Yopougon",
    "Siporex": "Yopougon",
    "Extension du Port": "Yopougon",
    "Andokoi": "Yopougon",
    "Andokoi Extension": "Yopougon",
    "Ananeraie": "Yopougon",
    "Adiopo Doumé": "Yopougon",
    # ABOBO
    "Abobo": "Abobo",
    "Abobo Gare": "Abobo",
    "N'Dotré": "Abobo",
    "Ndotré": "Abobo",
    "Abobo Baoulé": "Abobo",
    "Abobo Nord": "Abobo",
    "Abobo Deuxième": "Abobo",
    "PK 18": "Abobo",
    "PK 24": "Abobo",
    "Sagbé": "Abobo",
    "Djibi": "Abobo",
    "Anonkoua-Kouté": "Abobo",
    "Ebimpé": "Abobo",
    "Anyama Adjamé PK 18": "Abobo",
    # ADJAMÉ
    "Adjamé": "Adjamé",
    "Williamsville": "Adjamé",
    "Adjamé Nord": "Adjamé",
    "Adjamé Liberté": "Adjamé",
    "Adjamé Village": "Adjamé",
    "Adjamé-Nord": "Adjamé",
    "Zone Industrielle": "Adjamé",
    "Abrogoua": "Adjamé",
    # ATTÉCOUBÉ
    "Attécoubé": "Attécoubé",
    "Attécoubé Bramakote": "Attécoubé",
    "Parc National du Banco": "Attécoubé",
    # PLATEAU
    "Plateau": "Plateau",
    "Plateau Centre": "Plateau",
    "Commerce": "Plateau",
    "Indénié": "Plateau",
    "Port Douane": "Plateau",
    "Gare Lagune": "Plateau",
    "Les Jardins": "Plateau",
    "Quatre Villas": "Plateau",
    "Cité Esculape": "Plateau",
    # MARCORY
    "Marcory": "Marcory",
    "Zone 4": "Marcory",
    "Zone 4C": "Marcory",
    "Biétry": "Marcory",
    "Anoumabo": "Marcory",
    "Marcory résidentiel": "Marcory",
    "Résidentiel": "Marcory",
    "Jean Baptiste Mockey": "Marcory",
    "Champroux": "Marcory",
    # TREICHVILLE
    "Treichville": "Treichville",
    "Zone 1": "Treichville",
    "Zone 2": "Treichville",
    "Zone 3": "Treichville",
    "Port": "Treichville",
    "Arras": "Treichville",
    "Biafra": "Treichville",
    "Entente": "Treichville",
    "Notre Dame": "Treichville",
    # KOUMASSI
    "Koumassi": "Koumassi",
    "Remblais": "Koumassi",
    "Remblai": "Koumassi",
    "Petit Bassam": "Koumassi",
    "Belle Ville": "Koumassi",
    "SICOGI 1": "Koumassi",
    "SICOGI 2": "Koumassi",
    "Koumassi Nord-Est": "Koumassi",
    # PORT-BOUËT
    "Port-Bouët": "Port-Bouët",
    "Vridi": "Port-Bouët",
    "Gonzagueville": "Port-Bouët",
    "Adjouffou": "Port-Bouët",
    "Zone Aéroportuaire": "Port-Bouët",
    "Île Boulay": "Port-Bouët",
    "Ile Boulay": "Port-Bouët",
    "Jean Folly": "Port-Bouët",
    # SONGON
    "Songon": "Songon",
    "Songon-Gare": "Songon",
    "Songon-Kassemblé": "Songon",
    "Songon-Dagbé": "Songon",
    "Anguédédou": "Songon",
    "Abadjin-Koué": "Songon",
    "Bimbresso": "Songon",
    "Carrefour Bimbresso": "Songon",
    # BINGERVILLE
    "Bingerville": "Bingerville",
    "Centre Ville Bingerville": "Bingerville",
    "Adjamé Bingerville": "Bingerville",
    # ANYAMA
    "Anyama": "Anyama",
    # BROFODOUMÉ
    "Brofodoumé Centre": "Brofodoumé",
}

# Entrées complémentaires : ajoutées seulement si le quartier n'existe pas déjà
# (la base prime, comme dans le référentiel d'origine).
_NOUVELLES: dict[str, str] = {
    # YOPOUGON
    "Sikasso": "Yopougon",
    "Académie de la Mer": "Yopougon",
    "Académie résidentiel": "Yopougon",
    "Andokoi": "Yopougon",
    "Atchi": "Yopougon",
    "Azito Village": "Yopougon",
    "Bagouda": "Yopougon",
    "Banco 2": "Yopougon",
    "Batim 2": "Yopougon",
    "Béago": "Yopougon",
    "Bel Air": "Yopougon",
    "Camp Militaire": "Yopougon",
    "Cité Bracodi": "Yopougon",
    "Cité Caféiers": "Yopougon",
    "Cité CNPS": "Yopougon",
    "Cité Marine": "Yopougon",
    "Cité Mamie Adjoua": "Yopougon",
    "Cité Nawa": "Yopougon",
    "Cité Sodefor": "Yopougon",
    "Cité Sotra": "Yopougon",
    "Cité Verte": "Yopougon",
    "Gesco": "Yopougon",
    "GFCI": "Yopougon",
    "Niangon Adjamé": "Yopougon",
    "Niangon à droite": "Yopougon",
    "Niangon à gauche": "Yopougon",
    "Niangon Lokoa": "Yopougon",
    "Niangon Sicogi Canal": "Yopougon",
    "Niangon Sud Sicogi": "Yopougon",
    "Quartier Maroc": "Yopougon",
    "Quartier Millionnaire": "Yopougon",
    "Saint Hubert": "Yopougon",
    "Selmer ponty": "Yopougon",
    "Sicogi": "Yopougon",
    "Sideci": "Yopougon",
    "Sogefiha Solic": "Yopougon",
    "Sopim": "Yopougon",
    "Toit vert": "Yopougon",
    "Yao Séhi": "Yopougon",
    "Yopougon-Santé": "Yopougon",
    # PORT-BOUËT
    "Abouabou": "Port-Bouët",
    "Adjifou Un": "Port-Bouët",
    "Adjifou Deux": "Port-Bouët",
    "Adjoufou": "Port-Bouët",
    "Anani-Amamou": "Port-Bouët",
    "Ancien camp CNRA": "Port-Bouët",
    "Benogosso": "Port-Bouët",
    "Janfoldi": "Port-Bouët",
    "Kaotri": "Port-Bouët",
    "Mafiblé 2": "Port-Bouët",
    "Nouveau camp CRNA": "Port-Bouët",
    "Pedéko": "Port-Bouët",
    "Quartier Éléphant": "Port-Bouët",
    "Sié": "Port-Bouët",
    "Vridi Ako": "Port-Bouët",
    # ATTÉCOUBÉ
    "Abobo Doumé": "Attécoubé",
    "Agban-Attié": "Attécoubé",
    "Agban-village": "Attécoubé",
    "Attécoubé Nimatoulaye": "Attécoubé",
    "Bidjanté": "Attécoubé",
    "Boribana": "Attécoubé",
    "Djéné": "Attécoubé",
    "Gbebouto": "Attécoubé",
    "Jérusalem": "Attécoubé",
    "Jérusalem résidentiel": "Attécoubé",
    "Lackman": "Attécoubé",
    "Locodjro": "Attécoubé",
    "Moussikro": "Attécoubé",
    "Nimatoulaye": "Attécoubé",
    "Quartier École": "Attécoubé",
    "Quartier Espoir": "Attécoubé",
    "Quartier La Paix": "Attécoubé",
    "Quartier Lagune": "Attécoubé",
    "Sebroko": "Attécoubé",
    # ADJAMÉ
    "Bidonville": "Adjamé",
    "220 logements": "Adjamé",
    "Bracodi": "Adjamé",
    "Bromakoté": "Adjamé",
    "Habitat": "Adjamé",
    "Humici": "Adjamé",
    "Latin": "Adjamé",
    "Macaci": "Adjamé",
    "Pailler": "Adjamé",
    "Quartier Manguier": "Adjamé",
    "Saint Michel": "Adjamé",
    # ABOBO
    "Abobo RTI": "Abobo",
    "Abobo Sud": "Abobo",
    "Agbekoi": "Abobo",
    "Akeikoi": "Abobo",
    "Anonkoua": "Abobo",
    "Belleville": "Abobo",
    "Cité de la Grâce": "Abobo",
    "Kennedy": "Abobo",
    "N'dotré": "Abobo",
    "Palmafrique V2": "Abobo",
    "Sagbé Nord": "Abobo",
    "Sagbé Sud": "Abobo",
    "Sos Abobo": "Abobo",
    # SONGON
    "Abadjin-Doumé": "Songon",
    "Adiopodoumé": "Songon",
    "Allokoi": "Songon",
    "Bimbresso": "Songon",
    "Songon M'brathé": "Songon",
    "Songon-Té": "Songon",
    "Kilomètre 17": "Songon",
    # BINGERVILLE
    "Abatta": "Bingerville",
    "Achokoi": "Bingerville",
    "Agban": "Bingerville",
    "Aguien": "Bingerville",
    "Akakro": "Bingerville",
    "Akandjé": "Bingerville",
    "Akwè Djèmin": "Bingerville",
    "Bokate": "Bingerville",
    "Brégbo": "Bingerville",
    "Eloka": "Bingerville",
    "Figuier": "Bingerville",
    "Gbagba": "Bingerville",
    "M'batto-Bouaké": "Bingerville",
    "Sebia Yao": "Bingerville",
    "Riviéra 6": "Bingerville",
    # ANYAMA
    "Aghien-Télégraphe": "Anyama",
    "Akoupé": "Anyama",
    # COCODY
    "Caféier": "Cocody",
    "Gendarmerie Agban": "Cocody",
    "Lycée Technique": "Cocody",
    "RTI": "Cocody",
    "Vieux Cocody": "Cocody",
    "Port Royal": "Cocody",
    # BROFODOUMÉ
    "Brofodoumé Centre": "Brofodoumé",
}

# Orthographe canonique d'affichage (clé : nom normalisé).
_NOMS_CANONIQUES: dict[str, str] = {
    "2 plateaux": "Deux-Plateaux",
    "2-plateaux": "Deux-Plateaux",
    "deux plateaux": "Deux-Plateaux",
    "deux-plateaux": "Deux-Plateaux",
    "palmeraie": "Riviera Palmeraie",
    "palmeraie triangle": "Riviera Palmeraie",
    "riviera palmeraie": "Riviera Palmeraie",
    "blockhaus": "Blockhauss",
    "bonoumin": "Riviera Bonoumin",
    "riviera bonoumin": "Riviera Bonoumin",
    "riviera m'badon": "Riviera M'Badon",
    "m'badon": "Riviera M'Badon",
    "mbadon": "Riviera M'Badon",
    "m'pouto": "Riviera M'pouto",
    "mpouto": "Riviera M'pouto",
    "mpouto village": "Riviera M'pouto",
    "vallons": "Les Vallons",
    "le vallon": "Les Vallons",
    "les vallons": "Les Vallons",
    "rosier": "Les Rosiers",
    "rosier 4e programme": "Les Rosiers",
    "sci les rosiers": "Les Rosiers",
    "les rosiers": "Les Rosiers",
    "attoban": "Riviera Attoban",
}

# Centre approximatif de chaque commune (rattachement des quartiers sans règle).
CENTRE_COMMUNES: dict[str, tuple[float, float]] = {
    "Abobo": (5.4189, -4.0167),
    "Adjamé": (5.3667, -4.0167),
    "Attécoubé": (5.3333, -4.0333),
    "Cocody": (5.3667, -3.9833),
    "Koumassi": (5.3000, -3.9500),
    "Marcory": (5.2989, -3.9856),
    "Plateau": (5.3197, -4.0156),
    "Port-Bouët": (5.2553, -3.9303),
    "Treichville": (5.2925, -4.0086),
    "Yopougon": (5.3333, -4.0833),
    "Anyama": (5.4944, -4.0511),
    "Bingerville": (5.3556, -3.8889),
    "Brofodoumé": (5.5140, -3.9305),
    "Songon": (5.2667, -4.2333),
}

# Règles nommées (mot-clé normalisé → arrêt du corpus). Une règle ne s'applique
# que si son arrêt appartient à la commune du quartier ; l'ordre va du
# spécifique au générique.
_REGLES_NOM: list[tuple[str, str]] = [
    ("riviera 1", "st_riviera1"),
    ("riviera 2", "st_riviera2"),
    ("riviera 3", "st_riviera3"),
    ("riviera bonoumin", "st_bonoumin"),
    ("bonoumin", "st_bonoumin"),
    ("riviera golf", "st_bonoumin"),
    ("anono", "st_gare_anono"),
    ("9 kilo", "st_gare_9kilo"),
    ("neuf kilo", "st_gare_9kilo"),
    ("riviera", "st_riviera3"),
    ("palmeraie", "st_riviera3"),
    ("angre 7", "st_angre7"),
    ("angre", "st_angre2"),
    ("plateaux", "st_2plt_vallon"),
    ("vallon", "st_2plt_vallon"),
    ("sicogi", "st_2plt_sicogi"),
    ("dokui", "st_chateau"),
    ("chateau", "st_chateau"),
    ("cocody", "st_cocody_mairie"),
    ("zone 4", "st_marcory_z4"),
    ("bietry", "st_marcory_z4"),
    ("anoumabo", "st_marcory_z4"),
    ("marcory", "st_marcory_z4"),
    ("220 logements", "st_adjamme_220"),
    ("adjamme", "st_adjamme_gare"),
    ("williamsville", "st_adjamme_gare"),
    ("abrogoua", "st_adjamme_gare"),
    ("bidonville", "st_adjamme_gare"),
    ("zone industrielle", "st_adjamme_gare"),
    ("baoule", "st_abobo_baoule"),
    ("abobo", "st_abobo_gare"),
    ("siporex", "st_yopougon_siporex"),
    ("niangon", "st_yopougon_siporex"),
    ("yopougon", "st_yopougon_siporex"),
    ("banco", "st_attiecoube"),
    ("attiecoube", "st_attiecoube"),
    ("gare lagune", "st_plateau_jardins"),
    ("treichville", "st_treichville_gare"),
    ("cite administrative", "st_plateau_cite"),
    ("esculape", "st_plateau_cite"),
    ("indenie", "st_plateau_cite"),
    ("commerce", "st_plateau_ruecommerce"),
    ("jardins", "st_plateau_jardins"),
    ("plateau", "st_plateau_cite"),
]


# ------------------------------------------------------------------ normalisation


def normaliser(texte: str) -> str:
    """Minuscules sans accents, apostrophes unifiées, espaces compactés."""
    decompose = unicodedata.normalize("NFD", texte)
    sans_accents = "".join(c for c in decompose if not unicodedata.combining(c))
    return " ".join(sans_accents.replace("’", "'").lower().split())


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a1, b1, a2, b2 = map(math.radians, (lat1, lon1, lat2, lon2))
    h = math.sin((a2 - a1) / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin((b2 - b1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


# ------------------------------------------------------------------ assemblage


def _fusion_referentiel() -> dict[str, tuple[str, str]]:
    """Clé normalisée → (nom d'affichage d'origine, commune) ; la base prime."""
    entrees: dict[str, tuple[str, str]] = {}
    for quartier, commune in _BASE.items():
        entrees.setdefault(normaliser(quartier), (quartier, commune))
    for quartier, commune in _NOUVELLES.items():
        entrees.setdefault(normaliser(quartier), (quartier, commune))
    return entrees


def _quartiers_par_commune() -> dict[str, list[str]]:
    par_commune: dict[str, list[str]] = {}
    deja_vus: set[tuple[str, str]] = set()
    for cle, (nom, commune) in _fusion_referentiel().items():
        nom_final = _NOMS_CANONIQUES.get(cle, nom)
        cle_finale = normaliser(nom_final)
        if (cle_finale, commune) in deja_vus:
            continue
        deja_vus.add((cle_finale, commune))
        par_commune.setdefault(commune, []).append(nom_final)
    for quartiers in par_commune.values():
        quartiers.sort(key=str.casefold)
    return par_commune


QUARTIERS_PAR_COMMUNE: dict[str, list[str]] = _quartiers_par_commune()


def snap_quartier(nom: str, commune: str, stops: dict[str, dict]) -> str | None:
    """Arrêt du corpus de rattachement d'un quartier (voir docstring du module)."""
    cle = normaliser(nom)
    for mot_cle, stop_id in _REGLES_NOM:
        if mot_cle in cle:
            stop = stops.get(stop_id)
            if stop is not None and stop["commune"] == commune:
                return stop_id
    centre = CENTRE_COMMUNES.get(commune)
    if centre is None:
        return None
    candidats = [s for s in stops.values() if s["commune"] == commune] or list(stops.values())
    return min(
        candidats,
        key=lambda s: _distance_m(centre[0], centre[1], s["lat"], s["lon"]),
    )["id"]


def _slug(nom: str) -> str:
    propre = normaliser(nom).replace("'", "").replace("-", " ")
    return "q_" + "_".join(propre.split())


def build_quartier_pois(stops: dict[str, dict], pois_existants: dict[str, dict]) -> list[dict]:
    """POI quartiers prêts à fusionner dans Network.pois (même contrat que le corpus)."""
    prises = {normaliser(p["label"]) for p in pois_existants.values()}
    ids_pris = set(pois_existants)
    out: list[dict] = []
    for commune in sorted(QUARTIERS_PAR_COMMUNE):
        for nom in QUARTIERS_PAR_COMMUNE[commune]:
            if normaliser(nom) in prises:
                continue
            slug = _slug(nom)
            if slug in ids_pris:
                continue
            stop_id = snap_quartier(nom, commune, stops)
            if stop_id is None:
                continue
            ids_pris.add(slug)
            out.append(
                {
                    "id": slug,
                    "label": nom,
                    "commune": commune,
                    "stop_id": stop_id,
                    "stop_name": stops[stop_id]["name"],
                    "kind": "quartier",
                }
            )
    return out
