# AbidjanMob — Plateforme d'interopérabilité des transports d'Abidjan

Prototype de démonstration (AIMD 2026) : information multimodale temps réel + paiement
QR mobile money + module financier conducteur, sur le corridor pilote
**Cocody–Plateau–Adjamé**.

> ⚠️ Prototype : données indicatives, paiements **simulés** (aucun argent réel),
> frais/commissions/taxes de démonstration, FNE/RNE simulée.

## Structure

```
abidjanmod/
├── data/corpus/          # corpus pilote (23 arrêts dont gares woro, 22 lignes) — indicatif
├── demo/
│   ├── backend/          # API FastAPI · moteur d'itinéraires · live/ (flotte)
│   │   ├── quartiers.py  # référentiel ~260 quartiers d'Abidjan (14 communes)
│   │   ├── finance/      # module financier (factures, souches, taxes, FNE)
│   │   ├── wallets/      # portefeuilles mobile money (paiement multi-comptes)
│   │   └── tests/        # tests pytest (sans PostgreSQL)
│   ├── frontend/         # démo web React (mode mobile automatique)
│   │   └── scripts/      # cache des tuiles de carte (hors-ligne)
│   ├── demo.sh           # lancement local sans docker
│   └── smoke-test.sh     # test de fumée (11 vérifications)
├── docs/                 # plans, journal, scénario jury, Metabase, finance
├── docker-compose.yml    # api · nginx · db · db-init · metabase · tiles-init
└── Makefile              # gestion de la stack + qualité + tests
```

## Documentation

- `docs/plan-mvp.md` — plan MVP 6 mois (oct. 2026 → mars 2027)
- `docs/scénario-démo.md` — script de présentation jury (8–11 min, Q&A, plan B)
- `docs/module-financier.md` — module financier (facture/reçu, souches, dépenses, taxes, FNE)
- `docs/dashboards-metabase.md` — configuration + requêtes des tableaux de bord décideurs
- `docs/journal-de-suivi.md` — journal des étapes de réalisation (protocole du projet)

## Lancer la démo

### Option A — Docker (recommandé)

```bash
docker compose up --build     # ou simplement : make up
```

- Interface : **http://localhost:8080** · API (Swagger) : http://localhost:8000/docs ·
  Metabase : http://localhost:3000
- Sur un clone frais : `tiles-init` récupère les tuiles (~4 min, une fois) et `db-init`
  génère 14 jours de données analytics — ensuite tout fonctionne **hors-ligne**
- Arrêt : `make down` (⚠️ jamais `down -v` : cela effacerait les données et la config Metabase)

### Option B — Script local (sans Docker)

```bash
bash demo/demo.sh     # ou : make demo
```

- Interface : **http://127.0.0.1:4173** · API : http://127.0.0.1:8000/docs
- Sans PostgreSQL : l'app tourne en mode dégradé (finance en mémoire, pas d'analytics)

> ⚠️ Un mode à la fois : le port 8000 est partagé. Faire `make down` avant `make demo`,
> et inversement.

### Commandes rapides (Makefile)

```bash
make help          # liste complète
make up            # démarre la stack docker (api + nginx + db + metabase + tiles)
make down          # arrête la stack
make restart       # down + up (avec nettoyage des orphelins)
make logs / ps     # logs en direct · état des conteneurs
make smoke         # test de fumée (:8000)   · make smoke-nginx (:8080)
make test          # tests backend pytest (sans PostgreSQL)
make lint          # lint Python (ruff)      · make lint-fix (corrections auto)
make format        # formatage Python (black) · make format-check (vérif seule)
make psql          # console psql dans la base analytics
make demo          # mode local sans docker
```

Qualité : config `pyproject.toml` (ruff + black, line-length 100) · dépendances de
développement : `demo/backend/requirements-dev.txt` (`make deps-dev` les installe).

## Tester sur mobile (réseau local)

1. Téléphone connecté au **même Wi-Fi** que la machine
2. Repérer l'IP de la machine : `hostname -I` (ex. `192.168.100.74`)
3. Ouvrir **http://192.168.100.74:8080** sur le téléphone — l'app passe automatiquement
   en plein écran mobile (sans le cadre navigateur)

- Pas de Wi-Fi commun ? Connectez la machine au **hotspot du téléphone** et réutilisez
  la même recette avec l'IP obtenue — la démo reste 100 % locale, **sans internet**
- Si la page ne charge pas : pare-feu à vérifier (`sudo ufw status`, puis
  `sudo ufw allow 8080/tcp` si actif)

## Fichiers d'environnement (`.env`)

| Fichier | Rôle | Committé ? |
|---|---|---|
| `.env.example` | Modèle documenté — à copier en `.env` sur un clone frais (`cp .env.example .env`) | ✅ oui |
| `.env` | Identifiants et ports de démo/tests (lisible par docker compose automatiquement) | ❌ jamais |
| `.env.prod` | Placeholders pour le déploiement MVP (`CHANGE_ME…` à remplacer) | ❌ jamais |

Contenu : `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB`, ports
(`API_PORT`, `WEB_PORT`, `METABASE_PORT`), et emplacement réservé aux futures clés
PSP du MVP (Wave, Orange Money… — jamais dans un fichier committé).

> ⚠️ Les identifiants PostgreSQL ne s'appliquent qu'à la **première création** du
> volume `pgdata`. Les changer ensuite exige soit un volume neuf (données perdues),
> soit un `ALTER USER` via `make psql`.

## Analytics décideurs (Metabase)

La stack docker inclut **PostgreSQL + Metabase** : http://localhost:3000

- Au premier lancement, `db-init` génère **14 jours de fréquentation + paiements
  simulés** (pics d'heure de pointe, semaine/week-end) — idempotent
- **Chaque paiement fait dans la démo s'ajoute aux données en temps réel** (le
  principe « le paiement génère la donnée » du dossier, implémenté littéralement)
- Guide de configuration (2 min, une seule fois) + requêtes des tableaux de bord :
  **`docs/dashboards-metabase.md`**
- C'est le « produit données » Phase 2 (AMUGA, SOTRA, urbanistes) — sans PII par design

## Module financier (démonstration)

Chaque paiement simulé génère une **transaction comptable** complète : facture/reçu
client (imprimable A4, QR de vérification AbidjanMob), **souche numérique conducteur**
(brut − frais − commissions − taxes = net), suivi des **dépenses**, **estimation des
taxes** communales et étatiques (règles de démonstration configurables — aucun taux
officiel codé en dur), **clôture journalière** idempotente, et une architecture prête
pour une future intégration **FNE/RNE** (fournisseur simulé, jamais appelé).

## Portefeuilles mobile money & bilans périodiques (démonstration)

Le passager dispose d'un compte démo avec 4 **portefeuilles virtuels** (AbidjanMob-
Wave, AbidjanMob-Orange Money, AbidjanMob-MTN MoMo, AbidjanMob-Moov Money ; soldes
de départ : 400 · 600 · 500 · 500 F). **Aucun compte réel n'est accessible** : les
opérateurs ne sont pas interopérables, et le code secret (4 chiffres, simulation)
est un code AbidjanMob unique, pas celui de vos applications mobile money. On
**recharge** chaque portefeuille depuis son vrai compte (simulation ; APIs PSP au
MVP), puis on **répartit un paiement sur plusieurs comptes** : ex. 1 400 F =
400 Wave + 600 Orange + 400 Moov. Validations strictes (somme exacte, soldes
suffisants), débit atomique, journal des mouvements, ordre de priorité des comptes
par glisser-déposer, écran d'aide « ? » pendant le paiement. Bilans périodiques :
conducteur (jour/semaine/mois/trimestre dans « Ma caisse ») et passager
(« 📊 Mes dépenses » sur l'accueil).

- Guide complet : **`docs/module-financier.md`** · endpoints dans http://localhost:8000/docs
- Dashboard conducteur → onglets **Ma caisse** (vue d'ensemble, souches, dépenses,
  taxes, clôture)
- Requêtes Metabase supplémentaires : fin de `docs/dashboards-metabase.md`

## Comment tester

### 1. Tests automatiques (quelques secondes)

```bash
make smoke               # ou : bash demo/smoke-test.sh (API directe :8000)
make smoke-nginx         # via nginx (:8080)
make test                # 49 tests pytest (finance, quartiers, portefeuilles, bilans)
```

`smoke` vérifie 17 points : API, corpus, POI et quartiers, itinéraire phare, plan par
arrêt direct (position actuelle), flotte en mouvement, ETA, paiement, dashboard
conducteur, portefeuilles (déverrouillage, paiement réparti, débit et rechargement
vérifiés), bilans périodiques (conducteur + passager), base analytics, Metabase en
ligne et configuré. **Résultat attendu : 17/17 OK.**

### 2. Parcours manuel complet (au moins 2 fois avant le jour J)

Sur http://localhost:8080, suivre dans l'ordre — chaque point est un clic :

1. **Accueil** : carte visible, véhicules 🚐🚕 qui circulent, légende « En direct »
2. **⚡ Trajet démo** → 3 options : SOTRA 36 min/300 F · informel 39 min/500 F · taxi 25 min/1 900 F
3. **Option informelle** : chip « 🔴 … arrive à Riviera 2 dans ~X min » — le compte à
   rebours descend-il ?
4. **Détails de l'itinéraire** : étapes, attente, marche, tarifs
5. **Payer ce trajet** → Scanner le QR → conducteur Koffi → code secret du compte
   (4 chiffres quelconques) → répartition entre vos comptes (soldes simulés : Wave,
   Orange, MTN, Moov ; un seul compte suffit, le bouton « Remplir automatiquement »
   propose la répartition) → billet numérique avec QR
6. **Billet** : chip « Votre woro arrive dans ~X min » · bouton **« Voir le reçu »** →
   facture FAC-…, QR de vérification, badge « non certifié FNE — prototype » ·
   **Imprimer / PDF** (une page A4 propre) · **Partager**
7. **🚐 Mode conducteur** (bouton du bandeau) → « Ma caisse » : la recette du
   paiement apparaît en direct, position partagée, cartes financières (vue
   d'ensemble) · **👤 Mode passager** pour revenir au billet
8. **Onglet Souches** : détail décomposé (brut − frais − commissions − taxes = net) ·
   **Dépenses** : ajouter une dépense puis la supprimer (confirmation) ·
   **Clôture** : « Clôturer ma journée » puis re-cliquer (« déjà clôturée », pas de doublon)
9. **Refaire un paiement** → nouvelle recette dans le dashboard en < 5 s, nouvelle
   souche dans l'onglet Souches

### 3. Variantes à essayer

- Autres trajets : *Yopougon Siporex → Zone 4* (multimodal, bateau-bus) ·
  *Treichville → Cité Administrative* (bateau direct, 200 F)
- Scénario gares woro : *Riviera Bonoumin → Treichville* → taxi communal jusqu'à
  la gare Riviera 2 (200 F) puis woro DIRECT (800 F) = 1 000 F · option
  « Marche + transport » (857 m à pied) · les taxis communaux 🚙 desservent les
  gares (100 à 300 F)
- Recherche par quartier : tapez « Angré », « Palmeraie », « Sikasso »… (271 lieux
  et quartiers, arrêt de rattachement affiché) · « 📍 Position actuelle » en départ
  (géolocalisation, arrêt le plus proche)
- Inverser départ/destination (⇅) · répartir un paiement sur plusieurs comptes
  mobile money quand un seul ne suffit pas (ex. 1 400 F = 400 Wave + 600 Orange + 400 Moov)
- Recharger un compte (bouton +) depuis son « vrai » compte (simulation) ·
  glisser-déposer les comptes pour changer la priorité de « Remplir
  automatiquement » · bouton « ? » pendant le paiement : aide complète
- « 📊 Mes dépenses de transport » sur l'accueil : bilan jour / semaine / mois /
  trimestre côté passager · même sélecteur de période dans « Ma caisse » côté conducteur
- Bouton ⛶ plein écran (projection) · **sur mobile** (cf. section ci-dessus)
- Metabase : créer les questions du guide → refaire un paiement → ré-exécuter une
  requête → le paiement apparaît

### 4. Robustesse (plan B)

- **Hors-ligne** : couper le wifi puis recharger la page → tout doit continuer de marcher
- **Redémarrage** : `make restart` → état intact (volumes persistants)
- API Swagger : http://localhost:8000/docs (si le jury veut voir l'API)

### 5. Comportements normaux (ce ne sont pas des bugs)

- ETA variables : les véhicules bougent réellement (simulation accélérée ×4, mention
  affichée)
- Zoom très rapproché hors corridor : tuiles absentes (cache limité au corridor, z10–15)
- Le taxi n'offre pas de paiement : hors plateforme, affiché pour comparaison
- Chaque `smoke-test.sh` ajoute un paiement simulé au dashboard conducteur
- Metabase : ~1 min au premier démarrage ; frais (1 %/1,5 %) et règles fiscales =
  **valeurs de démonstration**, clairement marquées comme telles
- La requête « dépenses » de Metabase est vide tant qu'aucune dépense n'a été saisie

Scénario complet de présentation au jury : `docs/scénario-démo.md`.

Fond de carte : © OpenStreetMap contributors.
