# Journal de suivi — AbidjanMob

Protocole de travail : chaque étape est consignée ici (quoi, fichiers, commandes, résultats de vérification) afin de pouvoir évaluer le travail après coup.

## Contexte de la semaine

- **Démo devant le jury AIMD sous 2–3 jours** (semaine du 14 septembre 2026).
- Périmètre réduit à l'essentiel : **moteur d'itinéraires** + **flux de paiement simulé** + mini **tableau de bord conducteur**.
- Public : jury AIMD → narratif orienté innovation (boucle données), impact climatique, faisabilité, ancrage local.

### Décisions J1 (validées par l'utilisateur le 14/09/2026)

| Décision | Choix | Justification |
|---|---|---|
| Frontend démo | React (Vite) dans un cadre smartphone | Le plus rapide à polir en < 7 jours ; Flutter non installé ; backend 100 % réutilisable par les apps Flutter du MVP |
| Backend | Python / FastAPI | Choix stack MVP validé |
| Moteur d'itinéraires | Moteur léger custom (Python) sur corpus corridor + vraies rues OSM | Zéro dépendance Java/OTP pour la démo ; OTP2 reste l'architecture cible du MVP (open source éprouvé, cf. `plan-mvp.md`) |
| Paiement | Mock (simulateur Wave / Orange / MTN / Moov) | Pas d'accès PSP en 3 jours ; flux bout-en-bout réel, argent simulé |
| Données | Corpus corridor Cocody–Plateau–Adjamé : ~20 arrêts, 12 lignes, 13 POI — **indicatives, à valider terrain (M0 du MVP)** | Pas de données terrain disponibles à ce jour |
| Carte | Tuiles OpenStreetMap mises en cache localement | Démo robuste même sans connexion au moment de la présentation |
| Branding | Placeholder (logo SVG, couleurs orange/vert ivoirien) | Aucun actif fourni |

## J1 — lundi 14 septembre 2026

### Plan de la journée

1. Journal de suivi + `docs/plan-mvp.md` (plan MVP 6 mois, version française condensée)
2. Corpus pilote : `data/corpus/network.json`
3. Moteur d'itinéraires : `demo/backend/routing_engine.py`
4. API : `demo/backend/main.py`
5. Vérification : installation, démarrage, requêtes curl réelles

### Étapes réalisées

1. ✅ Initialisation dépôt git + `.gitignore`
2. ✅ Rédaction `docs/journal-de-suivi.md` (ce fichier), `docs/plan-mvp.md`, `data/README.md`
3. ✅ Corpus : 20 arrêts (Plateau, Cocody, Adjamé, Abobo, Yopougon, Marcory, Treichville, Attécoubé), 12 lignes (4 gbakas, 5 woro-woro, 2 SOTRA, 1 bateau-bus), 13 POI de recherche, 1 conducteur
4. ✅ Moteur : Dijkstra multi-passes (rapide / économique / formel / informel) + taxi estimé + marche ; attente = fréquence/2 ; lignes bidirectionnelles
5. ✅ API FastAPI : `/api/health`, `/api/meta`, `/api/network`, `/api/pois`, `POST /api/plan`, `POST /api/payments`, `GET /api/driver/{id}/receipts`

### Vérifications (résultats bruts consignés ci-dessous au fil de l'exécution)

- `pip install` : fastapi 0.141.1 · uvicorn 0.52.4 · pydantic 2.13.5 — **OK**
- Démarrage : `.venv/bin/uvicorn main:app --port 8000` (arrière-plan) — **OK**
- `GET /api/health` → `{"status":"ok","service":"abidjanmob-demo",...}` — **OK**
- `POST /api/plan` **Riviera 2 → Cité Administrative** (trajet phare de la démo) :
  - SOTRA L105 direct — 36 min · 300 F — « Le plus rapide »
  - Woro Riviera + Woro Plateau — 39 min · 500 F — « Réseau informel », 1 correspondance
  - Taxi estimé — 25 min · 1 900 F
- `POST /api/plan` **Yopougon Siporex → Zone 4** : 3 options multimodales dont
  SOTRA + Bateau-bus (« Le moins cher », 500 F) — **OK**
- `POST /api/plan` **Treichville → Cité Administrative** : Bateau-bus direct 36 min · 200 F — **OK**
- `POST /api/payments` (mock Wave) → ticket `ABJ-A8D68C` généré — **OK**
- `GET /api/driver/drv_001/receipts` → 13 paiements · 4 700 F · répartition par PSP ·
  le paiement simulé apparaît en direct — **OK**

### Correction apportée en cours de J1

Le filtre de dominance Pareto supprimait l'option « réseau informel » (dominée par le
SOTRA sur le trajet phare). Remplacé par « une option par type de réseau » : la
comparaison formel/informel — cœur de la proposition — est désormais toujours visible.

### Reste à faire (J2/J3)

- J2 : application web React (carte MapLibre, recherche, itinéraires, flux paiement,
  dashboard conducteur, branding), tuiles OSM mises en cache pour la démo hors-ligne
- J3 : tests de bout en bout, `scénario-démo.md`, script de lancement `demo.sh`, répétition
