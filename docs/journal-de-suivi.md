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

## J2 — (suite de la journée du 14/09)

### Étapes réalisées

1. ✅ Application React (Vite) complète : `demo/frontend/` — 14 fichiers
   - Accueil (recherche POI par commune, trajet démo présélectionné)
   - Résultats (carte + options formel/informel/taxi, tags, détails des étapes, CO₂)
   - Paiement simulé 4 étapes : scan QR conducteur → choix PSP (Wave/Orange/MTN/Moov) →
     écran PSP + code → débit → billet numérique avec QR
   - Mode conducteur : recettes du jour, répartition PSP, rafraîchissement 4 s
   - Branding placeholder (logo SVG, orange/vert/navy), cadre smartphone + plein écran
2. ✅ Backend : ajout des identifiants d'arrêts dans `/api/network` (tracé des itinéraires)
3. ✅ `npm install` (105 paquets) + `npm run build` — **compilation OK**
4. ✅ Script `demo.sh` (lancement complet en une commande)
5. ✅ Script `scripts/fetch_tiles.py` : mise en cache locale des tuiles OSM
   (z10–14 Grand Abidjan + z15 corridor) pour une démo **hors-ligne**

### Problème détecté et corrigé (important pour le jour J)

Capture headless Chrome : **MapLibre plantait toute l'app** si WebGL est indisponible
(exception non catchée → écran blanc). Corrigé : `try/catch` autour de l'init carte +
fallback « carte indisponible, itinéraires et paiement restent accessibles ». Le jour de
la démo, même un problème de driver graphique ne tuera pas la présentation.

### Vérifications J2

- `npm run build` : ✓ 45 modules, 1,6 s
- `curl http://127.0.0.1:4173/` : 200 ✓
- Rendu headless Chrome (`--dump-dom`) : « Où allez-vous », options POI « Riviera 2 »,
  « Cité Administrative », « Trajet démo », « Mode conducteur » présents ✓
- `<canvas>` présent (carte initialisée en WebGL logiciel) ✓
- Tuiles : 433 attendues, téléchargement en cours (0 erreur au pointage)

### Reste à faire (J3)

- Rebuild final avec tuiles complètes + capture d'écran de contrôle
- `docs/scénario-démo.md` (script de présentation pour le jury, avec transparent
  « ce qui est réel / ce qui est simulé »)
- Revue visuelle par l'équipe + répétition, corrections éventuelles
- Commit final + tag

## J3 (partiel, 14/09 au soir) — finalisation

1. ✅ Tuiles : **433/433 récupérées, 0 erreur, 11 Mo** ; rebuild → tuiles servies
   depuis `dist/` (vérifié `curl` sur z11/z12/z15 : 200, PNG réels de 29–36 Ko)
2. ✅ `docs/scénario-démo.md` : script de présentation 7–10 min (accroche, pilier
   information, pilier paiement, boucle données, conclusion), tableau de questions
   probables du jury avec réponses, plan B hors-ligne
3. ✅ README : instructions de lancement + scénario conseillé
4. ✅ Nettoyage : `package-lock.json` parasite à la racine supprimé (résidu du premier
   `npm install` lancé dans le mauvais répertoire)

### Livrables finaux de la démo

| Livrable | Emplacement |
|---|---|
| Application démo | `demo/frontend/` (React + MapLibre) — http://127.0.0.1:4173 |
| API + moteur d'itinéraires | `demo/backend/` (FastAPI) — http://127.0.0.1:8000/docs |
| Corpus pilote (indicatif) | `data/corpus/network.json` |
| Lancement 1 commande | `bash demo/demo.sh` |
| Plan MVP 6 mois | `docs/plan-mvp.md` |
| Script jury | `docs/scénario-démo.md` |
| Journal de suivi | `docs/journal-de-suivi.md` (ce fichier) |

### À faire par l'équipe avant le jour J

- Ouvrir http://127.0.0.1:4173 et **dérouler le scénario complet au moins 2 fois**
- Ajuster si besoin : textes, tarifs du corpus, couleurs
- Préparer les captures d'écran de secours (cf. §7 du scénario)
- Décider : présentation sur cet ordinateur ou un autre (si autre → `git clone` +
  `bash demo/demo.sh`, prévoir ~10 min d'installation + tuiles)

## Dockerisation (14/09, après gel de la démo)

Demande utilisateur : pouvoir lancer la démo avec docker-compose. Plan complet validé
(proxy `/api` propre inclus) avant implémentation.

### Étapes

1. ✅ `demo/backend/Dockerfile` — python:3.12-slim ; le corpus est copié vers
   `/data/corpus` pour reproduire l'arborescence que `routing_engine.py` résout
   (`parents[2]/data/corpus`)
2. ✅ `demo/frontend/Dockerfile` multi-étapes (node:22-alpine → nginx:1.27-alpine)
   + `nginx.conf` (fallback SPA, gzip, proxy `/api` → service `api`)
3. ✅ Refactor frontend : `api.js` en URL **relative** + proxy `/api` dans
   `vite.config.js` (server + preview) → demo.sh et docker partagent le même code,
   plus de CORS ni d'URL codée en dur
4. ✅ `docker-compose.yml` : `api` (:8000), `web` (:8080), `tiles-init` (one-shot
   idempotent, bind mount `./demo/frontend/public/tiles`) ; `.dockerignore`
   (node_modules, .venv, tuiles hors contexte de build)
5. ✅ `fetch_tiles.py` : répertoire de sortie paramétrable (`TILES_DIR`)
6. ✅ README : section Docker + avertissement « un mode à la fois » (port 8000 partagé)

### Vérifications

- Accès démon Docker sans sudo confirmé (25 autres conteneurs tournent sur la machine —
  aucun touché, préfixe projet `abidjanmod-`)
- `docker compose up --build -d` : 3 services, build OK
- `tiles-init` : **Exited(0)**, « 0 récupérées, 433 déjà présentes » (idempotence OK)
- `http://localhost:8080` : 200 · `/api/health` via proxy nginx : OK · tuile via
  nginx : 200 (34 Ko) · `POST /api/plan` via nginx : 3 itinéraires OK
- Rendu headless Chrome sur :8080 : UI complète + canvas carte OK
- Chemin `demo.sh` re-vérifié après refactor : rebuild + preview 4173 avec proxy
  `/api` (vers l'API docker sur 8000) : OK · tuiles 200

### URLs de démonstration actuels

| URL | Service |
|---|---|
| http://localhost:8080 | nginx (docker) — mode recommandé |
| http://127.0.0.1:4173 | preview Vite local (proxy vers l'API sur 8000) |
| http://localhost:8000/docs | API Swagger (conteneur docker) |

## Suivi en direct des véhicules (14/09, soirée)

Demande utilisateur : tracer le déplacement du chauffeur et partager sa position pour
éviter de faire attendre l'autre. Plan complet validé avant implémentation.

### Étapes

1. ✅ `demo/backend/live.py` — simulation **déterministe sur l'horloge** (pas de thread :
   fonction pure du temps, époque fixe → trajectoires continues, robustes aux redémarrages).
   Temps accéléré ×4 (mention affichée à l'écran), pauses aux terminus, allers-retours.
2. ✅ **Modèle flotte** : 2–3 véhicules par ligne informelle (25 véhicules au total),
   espacés selon la fréquence du corpus — les ETA sont cohérentes avec les
   « départs ~ toutes les X min » affichés. Les 3 conducteurs du corpus (Koffi, Mariam,
   Yao) sont rattachés au véhicule n°0 de leur ligne.
   *Correction en cours de route : la 1re version (1 véhicule/ligne) donnait des ETA
   de ~30 min, incohérentes avec les fréquences affichées — remplacée avant le frontend.*
3. ✅ Endpoints : `GET /api/drivers/live` (positions de la flotte),
   `GET /api/lines/{id}/eta?stop_id=` (prochains passages),
   `GET /api/driver/{id}/position` (position partagée d'un conducteur)
4. ✅ Frontend : marqueurs 🚐🚕 animés (halo pulsant, couleur par mode) sur toutes les
   cartes, polling 2 s ; chips « 🔴 … arrive à … dans ~X min · puis ~Y min » sur les
   itinéraires informels et sur le billet ; carte « 📍 Position partagée » + mini-carte
   dans le mode conducteur
5. ✅ Dockerfile backend : `live.py` ajouté au COPY (oubli détecté via les logs du
   conteneur au premier rebuild)
6. ✅ Scénario jury : nouvelle étape « Suivi en direct », durée 8–11 min, ligne Q&A
   « positions réelles ? »

### Vérifications

- `GET /api/drivers/live` : 25 véhicules, positions distinctes, directions cohérentes
- Mouvement confirmé : **24/25 véhicules déplacés en 4 s** (le 25e en pause à un terminus)
- `GET /api/lines/wo_riviera/eta?stop_id=st_riviera2` → `eta_min: 1.0, eta2_min: 7.3` ✓
- Rendu headless : 25 marqueurs `.vhc` présents sur l'accueil (localhost:4173 ET
  docker :8080), légende « Véhicules en direct » ✓
- Conteneurs api + web reconstruits, stack complète opérationnelle sur :8080

## Guide de test + smoke test (14/09, soirée)

Demande utilisateur : « how to test ». Ajouté :

1. ✅ `demo/smoke-test.sh` — 8 vérifications automatiques (santé, corpus, POI,
   itinéraire phare, flotte en mouvement, ETA, paiement simulé, dashboard).
   **Résultat : 8/8 OK sur les deux chemins** (API directe :8000 et proxy nginx :8080)
2. ✅ README : section « Comment tester » (test auto, parcours manuel en 8 clics,
   variantes, robustesse/plan B, comportements normaux)

## Makefile + qualité Python + nginx explicite (14/09, soirée)

Demandes utilisateur : Makefile de gestion, lint + black, et nginx visible dans le
compose. Linter choisi : **ruff** (validé par l'utilisateur).

### Étapes

1. ✅ `Makefile` racine : `help · up · down · build · restart · logs · ps · demo ·
   smoke · smoke-nginx · tiles · deps-dev · lint · lint-fix · format · format-check`
2. ✅ `pyproject.toml` : black + ruff (line-length 100, règles E4/E7/E9/F/I)
3. ✅ `demo/backend/requirements-dev.txt` : ruff + black (séparé des deps prod)
4. ✅ Service compose `web` renommé **`nginx`** — il s'agissait déjà de nginx
   (image finale du Dockerfile frontend) ; le renommage le rend visible dans
   `docker compose ps` et le compose documente chaque service
5. ✅ Passage de `make lint-fix` : imports triés (1 correctif auto) + renommage
   des variables `l` → `leg` (11× E741 « nom ambigu ») ; `make format` : 4 fichiers
   reformatés par black

### Incident détecté et corrigé

Le renommage du service a laissé l'ancien conteneur `abidjanmod-web-1` **orphelin**,
qui conservait le port 8080 bloqué (`docker compose down` ne supprime pas les orphelins
par défaut). Corrigé : `--remove-orphans` ajouté aux cibles `down` et `restart` du
Makefile.

### Vérifications

- `make lint` : **All checks passed** ✓ · `make format-check` : 4 fichiers conformes ✓
- `make restart` : stack redémarrée proprement — `abidjanmod-nginx-1` actif sur :8080
- `make smoke` : **8/8 OK** ✓ · `make smoke-nginx` : **8/8 OK** ✓ (le backend reformaté
  n'a aucun impact fonctionnel)
