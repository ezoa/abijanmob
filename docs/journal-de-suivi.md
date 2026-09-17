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

## Pilier analytics décideurs — PostgreSQL + Metabase (14/09, soirée)

Demande utilisateur : connaître montées/descentes par arrêt et véhicule pour faire des
statistiques, avec Metabase pour les décideurs. Plan complet validé.

### Étapes

1. ✅ Compose : services `db` (postgres:16-alpine, volume `pgdata`, healthcheck),
   `db-init` (one-shot idempotent), `metabase` (:3000, volume `metabase-data`) ;
   `api` reçoit `DATABASE_URL`
2. ✅ Modèle : `ridership_events` (ts, ligne, mode, formel, arrêt, commune, direction,
   montées, descentes) + `payments` (ts, billet, ligne, tarif, opérateur, conducteur)
3. ✅ `demo/backend/seed_analytics.py` : 14 jours de données synthétiques — double pic
   d'heure de pointe en semaine (7-9 h / 17-19 h), journée plate le week-end, montées
   côté résidentiel / descentes côté pôles d'emploi, adoption AbidjanMob par mode
   (SOTRA 22 % … woro 8 %), RNG déterministe (seed 42)
4. ✅ `demo/backend/analytics.py` : écriture **best-effort** — sans DATABASE_URL ou si
   PG tombe, l'app fonctionne sans erreur (l'analytics ne peut jamais casser la démo)
5. ✅ Boucle live : chaque paiement insère une ligne `payments` **et** la montée
   associée dans `ridership_events` (le frontend envoie ligne + arrêt d'embarquement)
6. ✅ `docs/dashboards-metabase.md` : configuration en 2 min + 6 questions SQL
   (profil horaire, top arrêts, formel/informel, charge par ligne, recettes par
   opérateur, adoption par jour)
7. ✅ `make psql` (console base) · smoke test étendu à 9 vérifications · README,
   scénario jury (Q&A « données pour les décideurs ? »)

### Incident détecté et corrigé

Le test analytics était toujours esquivé : le grep cherchait « abidjan**mob** » (nom
produit) alors que les conteneurs sont préfixés « abidjan**mod** » (nom du dossier =
nom du projet compose). Remplacé par un test direct `pg_isready` via compose exec —
plus robuste, sans parsing de nom.

### Vérifications

- `db-init` : exit 0 — **128 382 événements · 150 954 paiements · 1 105 007 passagers**
  (14 jours) ; relance → « Base déjà initialisée » (idempotence ✓)
- Boucle live : paiement `ABJ-030F2D` → visible dans `payments` **et** montée
  « Riviera 2, boarded=1 » dans `ridership_events` ✓
- Metabase : HTTP 200 sur :3000 ✓
- `make lint` / `make format-check` : conformes ✓ (6 fichiers Python)
- `make smoke` : **9/9 OK** ✓ · `make smoke-nginx` : **9/9 OK** ✓

### Extension (même soirée) — test automatique de Metabase

- `make smoke` passe à **10 vérifications** : `GET :3000/api/health` (service en ligne)
  + `has-user-setup` via `/api/session/properties` — tant que la configuration
  initiale n'est pas faite, le test affiche un rappel au lieu d'un échec ; une fois
  l'admin créé et la base connectée, il affiche « Metabase configuré ».
- Vérifié : **10/10 OK** (avec rappel « configuration initiale à faire » — attendu)

## Fichiers d'environnement `.env` (14/09, nuit)

Demande utilisateur : centraliser les identifiants dans des `.env` pour les tests.

### Étapes

1. ✅ `.env.example` (versionné) — modèle documenté : identifiants PostgreSQL,
   ports (`API_PORT`, `WEB_PORT`, `METABASE_PORT`), emplacement réservé aux futures
   clés PSP du MVP ; avertissement « les identifiants ne s'appliquent qu'à la
   première création du volume pgdata »
2. ✅ `.env` (démo/tests — valeurs actuelles, sans risque) et `.env.prod`
   (placeholders `CHANGE_ME` pour le MVP) — tous deux **gitignorés**
3. ✅ `docker-compose.yml` paramétré : `${POSTGRES_USER:-abidjanmob}` etc. —
   valeurs par défaut inchangées → aucun impact opérationnel sans `.env`
4. ✅ `make psql` et `smoke-test.sh` : identifiants lus depuis l'environnement du
   conteneur (`sh -c 'psql -U "$POSTGRES_USER" …'`) au lieu d'être codés en dur
5. ✅ README : section « Fichiers d'environnement »

### Vérifications

- `make restart` + `make smoke` : **11/11 OK** (1er passage 9/11 : Metabase encore
  en démarrage — re-test immédiat 11/11, faux positif temporel documenté)
- `SELECT count(*) FROM driver_stubs` via la nouvelle commande psql : 2 526 ✓
- `git status` : `.env` et `.env.prod` absents (ignorés) ✓ · `.env.example` présent
  en non-suivi ✓
- NB : constaté que l'utilisateur a indexé lui-même 18 fichiers (revue en cours) —
  l'index n'a pas été touché par l'assistant

## Module financier de démonstration (14/09, nuit)

Demande : étendre le prototype avec un module financier complet — facture/reçu client,
souche numérique conducteur, suivi recettes/dépenses, estimation des taxes communales
et étatiques, relevé journalier, préparation FNE/RNE (sans jamais l'appeler).
Cahier des charges intégral respecté ; documentation dédiée : `docs/module-financier.md`.

### Architecture retenue

- Nouveau paquet backend `demo/backend/finance/` (8 modules) : `tax_engine.py`
  (moteur fiscal PUR, zéro dépendance base), `fees.py` (frais 1 % + commission 1,5 % —
  valeurs de démo), `fne.py` (`InvoiceCertificationProvider` + `MockFNEProvider`),
  `documents.py` + `documents_numbering.py` (génération + numérotation
  FAC/STB/CLR-AAAA-NNNNNN), `store.py` (deux implémentations derrière la même
  interface : PostgreSQL / mémoire), `service.py` (façade best-effort à la
  analytics.py — jamais bloquante pour un paiement), `api.py` (routeur /api).
- `analytics.py` **inchangé** : le module financier enrichit la ligne `payments`
  existante (UPDATE par ticket_id) au lieu de doublonner les écritures.
- Contrats préservés : `POST /api/payments` et `GET /api/driver/{id}/receipts`
  répondent exactement comme avant ; les infos financières viennent en complément.
- Choix tests : logique métier pure + store interchangeable → **pytest sans
  PostgreSQL** (store mémoire forcé par `tests/conftest.py`). Les chemins
  PostgreSQL sont couverts par le parcours curl fonctionnel post-déploiement.

### Étapes réalisées

1. ✅ Backend : module `finance/` complet + intégration dans `main.py`
   (router préfixé `/api`, événement de démarrage, enrichissement de la réponse
   de paiement) ; `PaymentRequest` + champ optionnel `dest_stop_id`.
2. ✅ Migrations idempotentes (DDL_STATEMENTS) : évolution de `payments`
   (9 colonnes + index unique `ticket_id`), 6 nouvelles tables + index.
3. ✅ Seed de 7 règles fiscales de démonstration (is_official=false) : pourcentage
   opérateur/client, communale Cocody, communale Adjamé **désactivée**, provisions
   annuelle (gbaka) et mensuelle, règle **expirée 2025**. Aucun taux officiel codé
   en dur ; l'ancien prélèvement de 4 % n'est pas réutilisé.
4. ✅ Seed du jour de démo : les 12 SEED_RECEIPTS de Koffi deviennent des
   transactions complètes (idempotent par date) → les deux dashboards (recettes
   et financier) affichent les mêmes montants.
5. ✅ Backfill one-shot PostgreSQL : 2 500 paiements seedés des 7 jours précédents
   → documents + souches `settled` (drv_001 : 1 214 · drv_002 : ~565 · drv_003 : ~721)
   → la semaine affiche ~491 200 F de brut.
6. ✅ Frontend : `ReceiptView` (reçu A4 imprimable + QR de vérification + partage
   Web Share/repli copie), boutons sur `TicketView` (Voir le reçu / Imprimer-PDF /
   Partager), `DriverView` réorganisé en 5 onglets « Ma caisse » + 4 nouveaux
   composants (Souches, Dépenses, Taxes, Clôture), CSS print + tabular-nums +
   boutons ≥ 44 px. Lien direct `#driver` ajouté (démo/test).
7. ✅ Docs : `docs/module-financier.md` (nouveau), section Metabase **en fin de**
   `docs/dashboards-metabase.md` (7 requêtes — contenu existant intact), README,
   ce journal.
8. ✅ Tests : `demo/backend/tests/` (23 tests pytest, sans base), pytest+httpx
   ajoutés à `requirements-dev.txt`, cible `make test`, config pytest dans
   `pyproject.toml`.

### Incidents détectés et corrigés en cours de route

1. **695 ticket_id dupliqués** dans les 151 k paiements seedés (paradoxe des
   anniversaires sur 24 bits) — l'index unique exigé ne pouvait pas être posé.
   Correction : déduplication idempotente à la migration (renommage des doublons
   en hexa de l'id sur **8 caractères**, longueur disjointe de l'espace aléatoire
   à 6 caractères — la 1re tentative sur 6 caractères entrait encore en collision
   avec des ticket_id existants) + `seed_analytics.py` passe en numérotation
   séquentielle pour les installations fraîches.
2. **`tax_rules.code` sans contrainte unique** → `ON CONFLICT (code)` refusé par
   PostgreSQL. Correction : index unique `uq_tax_rules_code` dans la DDL.
3. **Ordre du démarrage** : le seed du jour de démo faisait échapper le garde-fou
   du backfill (« aucun document existant »). Correction : backfill AVANT seed.
   (Une remise à zéro des tables finance fraîchement créées a été faite une fois
   pour laisser le backfill corrigé se déclencher.)
4. **psycopg `AmbiguousParameter`** : les filtres optionnels (`%(x)s IS NULL OR …`)
   échouaient quand le paramètre vaut None (non typé). Correction : casts explicites
   (`CAST(%(x)s AS text/date) IS NULL OR …`) dans `list_stubs` et `list_expenses`.
   Bug invisible en store mémoire → détecté par le parcours curl sur la stack
   docker (les tests pytest seuls ne l'attrapaient pas).

### Vérifications (toutes exécutées, résultats réels)

- `make lint` : **All checks passed** (16 fichiers, ruff E4/E7/E9/F/I) ✓
- `make format-check` : 16 fichiers conformes (black, line-length 100) ✓
- `make test` : **23 passed** (9 moteur fiscal + 14 API, store mémoire) ✓
- `npm run build` : ✓ built in 1,7 s (2e build après module : 1,71 s) ✓
- `make restart` : stack reconstruite (api, nginx, db, db-init idempotent, metabase,
  tiles-init « déjà présentes ») ; `curl /api/health` → `finance_store: "postgres"` ✓
- Migration vérifiée en base : colonnes `payments` présentes (transaction_id, status,
  gross_amount, currency, provider_key, line_id, stop_id, created_at, updated_at),
  index `uq_payments_ticket_id` posé, **0 doublon restant**, 2 500 paiements
  enrichis d'un transaction_id ✓
- Tables finance : 2 512 documents · 2 512 souches · 9 988 calculs fiscaux · 7 règles ✓
- `bash demo/smoke-test.sh` : **11/11 OK** ✓ · `API=http://localhost:8080 …` : **11/11 OK** ✓
- Parcours curl fonctionnel (stack docker) : paiement → reçu FAC-2026-002516
  (commune Cocody, FNE non certifié, 4 lignes fiscales) → QR vérifié (bon jeton ✓,
  mauvais jeton ✗, doc inconnu 404) → souche unique STB-2026-002516 (net 250 F =
  300 − 3 − 5 − 42) → filtres (opérateur, statut, dates) → dépense créée/listée/
  supprimée (201/200/204/404) → synthèse fiscale (5 règles, taxes 47 896 F +
  provisions 18 438 F) → clôtures idempotentes (201 puis 200 « déjà clôturée ») →
  7 règles, 422 sur catégorie/statut invalides ✓
- Mode local dégradé (uvicorn sans DATABASE_URL, port 8010) : paiement → document
  en mémoire, dashboard recettes == résumé financier (4 700 F), dépense, clôture,
  synthèse fiscale, `finance_store: "memory"` ✓ — demo.sh fonctionnel par équivalence
- Rendu headless Chrome (:8080) : accueil OK (canvas + 75 marqueurs véhicules) ;
  `#driver` → « Ma caisse » avec 5 onglets, 27 cartes, 12 recettes, 4 barres
  opérateurs, montants tabulaires (4 400 F jour · 491 200 F semaine · 4 790 F à
  reverser) ✓

### Décisions notables

- Les recettes seedées du jour ne sont PAS écrites dans `payments` (le comportement
  Metabase existant est préservé) : elles vivent uniquement dans les tables finance
  (payment_id déterministes `PAY-SEED-AAAAMMJJ-nn`).
- Le backfill exclut le jour même pour garder la cohérence dashboard recettes /
  dashboard financier.
- Colonne `provider` ajoutée à `driver_stubs` et `commune` à `customer_documents`
  (filtre opérateur et requête Metabase « recettes par commune » exigés par le
  cahier des charges), `tax_target` ajoutée à `tax_rules` (nature client/opérateur).
- Dépenses : pas d'upload de fichier, référence justificatif saisie manuellement.
- Une souche confirmée n'est jamais modifiable : correction = annulation/remboursement/
  avoir, non implémenté dans ce lot (mention affichée dans le détail de souche).

## Recherche par quartiers, portefeuilles multi-comptes, bilans périodiques (17/09/2026)

Deux grandes fonctionnalités demandées + trois observations, implémentées en quatre
chantiers avec tests à chaque étape. Approche : étude du code d'abord (architecture
cartographiée), puis chantiers du plus sûr au plus structurant.

### Chantier 1 : quick wins UI

- Suppression des tirets cadratins « — » de tous les textes affichés (~37 chaînes :
  frontend + résumés d'itinéraires du moteur, libellés des règles fiscales, messages
  de clôture). Les commentaires/docstrings du code ne sont pas affichés : intouchés.
- Bouton « Mode conducteur » : libellé dynamique orienté action (« 🚐 Mode
  conducteur » ↔ « 👤 Mode passager »), cohérent avec le bouton plein écran.

### Chantier 2 : recherche exhaustive + position actuelle (Idée 1)

- Nouveau module `quartiers.py` : référentiel ~260 quartiers / 14 communes du Grand
  Abidjan (fourni par l'équipe produit, porté depuis un référentiel TypeScript :
  normalisation des accents, noms canoniques, dédoublonnage, la base prime sur les
  entrées complémentaires).
- Rattachement de chaque quartier à un arrêt du corpus : règles nommées (Riviera,
  Angré, II Plateaux, Zone 4, gares...), sinon arrêt de la commune le plus proche du
  centre de commune, sinon arrêt le plus proche global (Koumassi, Port-Bouët, Songon,
  Anyama, Bingerville, Brofodoumé n'ont pas d'arrêt). L'arrêt de rattachement est
  affiché dans l'UI (transparence).
- Fusion dans `Network.pois` : 269 POI au total, les 14 POI du corpus priment.
- `/api/plan` accepte en plus `from_stop`/`to_stop` (additif, contrat préservé) : la
  position actuelle géolocalisée côté client (navigator.geolocation → arrêt le plus
  proche, calcul local, fonctionne hors-ligne) planifie par arrêt direct.
- Frontend : les listes déroulantes deviennent des champs avec autocomplétion
  (insensible aux accents/casse, navigation clavier) + entrée « 📍 Position
  actuelle » en tête du départ (une liste native de 269 entrées est inutilisable).

### Chantier 3 : portefeuilles multi-comptes (Idée 2)

- Nouveau package `wallets/`, même architecture que finance/ (models, store
  mémoire+PostgreSQL, façade best-effort, routeur). Soldes de départ volontairement
  modestes (Wave 400 · Orange 600 · MTN 500 · Moov 500) : la répartition s'impose
  naturellement, ex. 1 400 F exige plusieurs comptes.
- `POST /api/wallets/unlock` : les soldes ne sortent jamais sans code secret
  (4 chiffres quelconques, simulation, cohérent avec le code de paiement).
  `POST /api/wallets/reset` (réinitialisation démo), `GET /api/wallets/transactions`.
- `POST /api/payments` accepte en plus `splits: [{provider, amount}]` : le champ
  `provider` seul reste le chemin historique inchangé (contrat gelé, test dédié
  vert). Validations strictes : somme = montant exact, opérateur unique, solde
  suffisant (refus 400 explicite). Débit atomique (`UPDATE ... WHERE balance >= x`
  tout ou rien, journal dans la même transaction). Pannes de store = best-effort
  (le paiement ne s'arrête jamais), refus métier = 400.
- Clé `multi` + libellé combiné (« Wave + Orange Money ») pour le module financier
  et analytics (colonnes texte libres, aucun taux ni liste fixe impliqués).
- Frontend PaymentView : scan → conducteur → déverrouillage par code → répartition
  (soldes affichés, montants modifiables, remplissage automatique, total vs à
  payer, réinitialisation) → traitement. Billet : ligne « Répartition » si
  multi-comptes.

### Chantier 4 : bilans périodiques

- Conducteur : `financial-summary` étendu de façon additive (jour inchangé +
  semaine / mois / trimestre, mêmes champs par période). Sélecteur de période dans
  la Vue d'ensemble de « Ma caisse ».
- Passager : `GET /api/wallets/spending-summary` + écran « 📊 Mes dépenses » depuis
  l'accueil (totaux, paiements, ticket moyen, répartition par opérateur, derniers
  mouvements), alimenté par le journal des portefeuilles + un historique seedé de
  8 paiements sur 6 jours (idempotent, soldes reconstitués pour retomber
  exactement sur les soldes actuels).

### Vérifications

- `make lint` / `make format-check` : 22 fichiers conformes ✓
- `make test` : **44 passed** (23 initiaux + 8 quartiers + 10 portefeuilles +
  3 bilans, tout en mémoire sans PostgreSQL) ✓
- `make restart` (corpus + module wallets copiés dans l'image api) puis
  `make smoke` : **16/16 OK**, dont paiement réparti 200 Wave + 100 Orange avec
  débit vérifié en base PostgreSQL (Wave 400 → 200 F), plan par arrêt direct /
  position actuelle, bilans périodiques conducteur et passager ✓
- Contrats préservés : tests legacy (paiement, souches, reçus) verts, smoke du
  paiement historique inchangé ✓

### Décisions notables

- Les portefeuilles sont un compte SIMULÉ interne à la démo : aucun compte mobile
  money réel n'est accessible. Dans le MVP, les adaptateurs PSP (clés réservées
  dans .env.example) exécuteront chaque prélèvement avec le consentement de
  l'utilisateur, validé dans son application opérateur : AbidjanMob orchestre,
  les PSP exécutent.
- Code d'accès aux soldes : 4 chiffres quelconques (simulation), comme le code de
  paiement existant, pour éviter toute friction le jour J.
- Un paiement réparti écrit UNE seule ligne analytics `payments` (provider =
  libellé combiné) : les requêtes Metabase « revenus par opérateur » verront une
  tranche « Wave + Orange Money » ; le détail par opérateur vit dans
  `wallet_transactions`.
- L'historique passager seedé ne débite pas les soldes actuels : il reconstitue
  les soldes « avant » pour retomber exactement sur les soldes initiaux.
- Rattachement quartier → arrêt : indicatif (comme tout le corpus), arrêt affiché
  dans l'UI ; les règles nommées priment sur la distance au centre de commune.

## Gares woro, taxis communaux, marche + rechargement des portefeuilles (17/09/2026, suite)

Retours d'utilisateur après test réel : trois chantiers.

### Réseau réaliste : gares, taxis communaux, marche

- Diagnostic du signalement « position à Riviera Bonoumin détectée Riviera 1 » :
  la géolocalisation fonctionnait (arrêt le plus proche parmi les 20 du corpus,
  Riviera 1 à ~850 m), mais le corpus n'avait pas d'arrêt à Bonoumin, et la règle
  de rattachement envoyait le quartier vers Riviera 3. Les noms du référentiel
  fourni étaient bien tous intégrés.
- Arrêts ajoutés aux positions OpenStreetMap (Nominatim) : Riviera Bonoumin
  (5.3647, -3.9726), Gare Anono (5.3421, -3.9736) ; Gare 9 Kilo (Angré) placée de
  façon indicative (absent d'OSM, gare informelle). Cocody Mairie devient hub :
  4 gares à Cocody (9 Kilo, Riviera 2, Anono, Cocody centre).
- Nouveau mode « taxi communal » (30 km/h, informel) : navettes à coût réduit vers
  les gares (100 à 300 F). Exclu du suivi en direct (flotte = gbakas + woros) et
  ajouté aux dictionnaires du seed analytics.
- Woro/gbaka DIRECTS inter-gares, conformes au modèle réel (hub-and-spoke : pas de
  transit inter-communes en véhicule en commun) : Riviera 2 → Treichville 800 F,
  9 Kilo → Treichville 1 000 F, Riviera 2 → Zone 4, 9 Kilo → Yopougon,
  Anono → Adjamé.
- Nouvelle passe Dijkstra « sans taxi communal » : fait émerger l'option
  « Marche + transport » (rejoindre l'arrêt ou la gare à pied, tag dédié).
- Rattachements corrigés : Riviera Bonoumin → arrêt Bonoumin (et non Riviera 3),
  Anono → Gare Anono, 9 kilo → Gare 9 Kilo.
- Scénario vérifié en direct : Bonoumin → Treichville = taxi communal (200 F) +
  woro direct (800 F) = 1 000 F [Le plus rapide] · marche 857 m + transports
  [Marche + transport] · taxi 1 950 F.

### Affichage « Mes dépenses »

- Date et heure compactes sur une seule ligne (« 17/09 · 14:30 »), police réduite,
  grille adaptée (la colonne temps était calée sur « 07:05 »).

### Portefeuilles : rechargement + pédagogie

- Modèle explicité et confirmé : comptes VIRTUELS AbidjanMob-Wave / AbidjanMob-
  Orange Money / etc. Le code secret est un code AbidjanMob unique, jamais les
  codes des opérateurs (aucune interopérabilité réelle). Dans le MVP, les APIs
  PSP rechargeront les portefeuilles virtuels depuis les vrais comptes, avec
  validation dans l'application de l'opérateur.
- `POST /api/wallets/topup {pin, provider, amount}` : crédite le portefeuille,
  journal kind='topup', message « Rechargement simulé depuis votre compte X
  réel : +N F sur AbidjanMob-X ». Les bilans « Mes dépenses » ignorent les
  rechargements (ce ne sont pas des dépenses de transport).
- Frontend paiement : bouton « + » par compte (rechargement inline), comptes
  renommés « AbidjanMob-Wave » etc., glisser-déposer pour réordonner la priorité
  de prélèvement (ordre persisté sur l'appareil), tooltips sur « Remplir
  automatiquement » (ordre d'affichage haut → bas) et « Réinitialiser les
  soldes » (libellé sans « (démo) »), bouton « ? » ouvrant un écran d'aide
  complet (comptes virtuels, code secret, rechargement, priorités).

### Vérifications

- `make lint` / `make format-check` : 22 fichiers conformes ✓
- `make test` : **49 passed** (+1 scénario Bonoumin → Treichville, +3
  rechargement, +1 bilans/rechargement) ✓
- `make restart` + `make smoke` : **17/17 OK** (22 lignes / 23 arrêts / 271 POI,
  rechargement vérifié en base : Wave 200 → 1 200 F) ✓

## Corrections après revue (17/09/2026, fin de journée)

- Bouton « 👀 Voir côté conducteur » retiré de l'écran billet : redondant avec la
  bascule « Mode conducteur » du bandeau (substitut temporaire aux futurs comptes
  passager/conducteur). La bascule conserve le retour au billet (returnTo) et
  affiche le libellé dynamique « 👤 Mode passager ». Parcours du README, script
  jury (scénario-démo.md, étape paiement actualisée : code AbidjanMob puis
  répartition) et module-financier.md mis à jour. « Nouvelle recherche » devient
  l'action principale de l'écran billet.
- « Gare 9 Kilo (Angré) » renommée **Gare 9 Kilo** et déplacée près de l'arrêt
  Riviera 3 (5.3660, -3.9380, à ~480 m à pied) : 9 Kilo est un quartier de la
  Riviera 3, pas d'Angré (correction utilisateur).
