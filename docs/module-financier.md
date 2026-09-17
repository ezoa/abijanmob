# Module financier — AbidjanMob (prototype de démonstration)

> ⚠️ **Tout est simulé** : frais, commissions, taxes et « certification FNE » sont des
> mécanismes de démonstration. Aucun taux fiscal ivoirien officiel n'est codé en dur,
> aucun appel n'est fait aux systèmes DGI/FNE, aucun argent ne circule.

Le module financier étend le prototype avec la chaîne complète :

```
Paiement confirmé
   → Transaction comptable (TRX-…)
      ├── Billet de transport (ABJ-…, existant)
      ├── Facture / reçu client (FAC-AAAA-NNNNNN) + QR de vérification AbidjanMob
      ├── Souche numérique conducteur (STB-AAAA-NNNNNN)
      ├── Calcul des frais et commissions (1 % + 1,5 % — valeurs de démo)
      ├── Calcul / provision des taxes (règles configurables `tax_rules`)
      └── Écriture de relevé conducteur (résumés, clôtures journalières)
```

Tous les documents d'un même paiement partagent les identifiants communs
`payment_id`, `transaction_id`, `ticket_id`, `document_id`, `driver_id`.

## 1. Parcours client — facture / reçu

1. Le client paie (flux existant, inchangé) → `POST /api/payments`.
2. La réponse contient, en complément du billet habituel : `transaction_id`,
   `payment_id`, `document_id`, `document_number`, `verification_token`,
   `verify_payload`, `stub_number` et un bloc `financial` (brut, frais, commission,
   provisions, net conducteur).
3. Sur l'écran du billet, de nouveaux boutons : **« Voir le reçu »**,
   **« Imprimer / Enregistrer en PDF »** (mise en page A4 via CSS `@media print`),
   **« Partager »** (Web Share API, repli copie dans le presse-papiers) et
   **« Nouvelle recherche »** (existant). L'accès à la vue conducteur se fait par
   la bascule **« Mode conducteur »** du bandeau (retour au billet conservé).
4. Le reçu affiche : logo AbidjanMob, mention « Prototype de démonstration », numéro
   unique, date/heure, exploitant/conducteur, ligne, origine → destination (si
   disponibles), montant brut, détail des taxes **uniquement si une règle
   client s'applique**, moyen de paiement, identifiants de transaction, QR de
   vérification **AbidjanMob** (jamais un QR FNE), et le statut de certification :
   **« non certifié — prototype »**.
5. Vérification : `GET /api/customer/documents/{id}/verify?token=…` → `{valid: true/false}`.

Le QR de vérification encode `ABJMOB|VERIF|{document_number}|{jeton}` — un QR de
démonstration AbidjanMob, sans lien avec la facturation normalisée électronique.

## 2. Parcours conducteur — souche numérique

Chaque paiement confirmé génère automatiquement **une seule** souche (contrainte
d'unicité sur `payment_id`) :

```
Montant brut − frais de paiement − commission plateforme − taxes/provisions = net conducteur
```

- Liste filtrable par **date**, **ligne**, **opérateur mobile money** et **statut de
  reversement** (`pending` = à reverser, `settled` = reversé).
- Détail consultable : décomposition ligne à ligne + règles fiscales appliquées.
- Une souche confirmée n'est **jamais modifiable directement** : une correction passe
  par annulation / remboursement / avoir — non implémenté dans ce lot (le modèle
  prévoit `cancelled_at` sur les documents et `refunded` comme statut de paiement).

## 3. Espace « Ma caisse » (dashboard conducteur, 5 onglets)

| Onglet | Contenu |
|---|---|
| **Vue d'ensemble** | Contenu existant (recettes du jour en direct, répartition par opérateur, position partagée, liste des recettes) + cartes financières : frais & commissions, provisions fiscales, dépenses, bénéfice net estimé (±), recettes 7 jours, solde à reverser |
| **Souches** | Liste + filtres + détail (décomposition et taxes) |
| **Dépenses** | Ajout (catégorie, date, montant, description, référence de justificatif — pas d'upload), consultation, filtrage, suppression avec confirmation |
| **Taxes** | Synthèse par règle sur une période, provisions estimées, avertissement systématique |
| **Clôture** | Récapitulatif du jour + action « Clôturer ma journée » (idempotente : une seule clôture par date) + historique |

## 4. Dépenses conducteur

13 catégories (cahier des charges) : carburant, entretien, réparation, pneus,
assurance, visite technique, stationnement, frais de gare, péage, lavage,
cotisation syndicale, taxe, autre. Montants en FCFA entiers positifs. La référence
de justificatif est saisie manuellement — **aucun fichier n'est stocké**.

## 5. Calcul fiscal — règles configurables, zéro taux codé en dur

Le moteur (`finance/tax_engine.py`) lit **exclusivement** les règles actives de la
table `tax_rules` : date d'effet, commune, catégorie de véhicule, régime
d'exploitant, fréquence, type de calcul. Une règle s'applique si elle est activée,
dans ses dates d'effet, et ciblée sur la transaction (NULL = tous).

Types de calcul :

| Type | Formule | Nature |
|---|---|---|
| `percentage` | `taux × brut` | taxe par course (client ou opérateur selon `tax_target`) |
| `fixed_per_trip` | montant fixe | taxe par course (client ou opérateur) |
| `fixed_daily` | `montant / 40 courses` | **provision estimative** |
| `fixed_monthly` | `montant / 1 040 courses` (26 j × 40) | **provision estimative** |
| `fixed_annual` | `montant / 12 480 courses` | **provision estimative** |

### Taxe réelle vs provision estimée

- Une taxe `percentage` ou `fixed_per_trip` est calculée **par course** : c'est le
  seul cas où un montant est réellement rattaché à la transaction.
- Une taxe journalière/mensuelle/annuelle **ne se prélève pas par course** : le
  moteur la répartit en **provision estimative** (marquée
  `estimated_provision`, affichée « ∝ » dans l'interface). Elle sert à montrer au
  conducteur ce que la course « rembourse » de ses obligations périodiques —
  jamais comme un prélèvement légalement exigible par course.

Mention affichée systématiquement (API + interface) :

> « Estimation indicative fondée sur les règles configurées. À confirmer par
> l'administration fiscale ou communale compétente. »

### Règles livrées (toutes `is_official=false`, désactivables)

| Code | Nature | Détail |
|---|---|---|
| `DEMO_ETAT_COURSE` | opérateur, 1,5 % par course | étatique (fictive) |
| `DEMO_TVA_TRANSPORT` | client, 2 % incluse (affichée sur le reçu) | étatique (fictive) |
| `DEMO_COCODY_COURSE` | opérateur, 25 F/course | communale, **commune de Cocody** |
| `DEMO_ADJAMME_COURSE` | opérateur, 20 F/course | communale Adjamé, **désactivée** |
| `DEMO_VIGNETTE_ANNUELLE` | provision, 36 000 F/an ÷ 12 480 | cible **gbaka** |
| `DEMO_CIRCULATION_MENSUELLE` | provision, 12 000 F/mois ÷ 1 040 | toutes catégories |
| `DEMO_TAXE_EXPIREE` | 2 % | **expirée au 31/12/2025** — jamais appliquée |

NB : l'ancien prélèvement de 4 % sur les conducteurs de plateformes (modifié par
l'annexe fiscale 2026) n'est **pas** réutilisé.

La commune retenue pour une transaction est celle de l'**arrêt d'embarquement**
(`stop_id`) ; à défaut, celle du premier arrêt de la ligne ; sinon aucune (les
règles communales ne s'appliquent pas). La catégorie de véhicule est le mode
(gbaka, woro, …).

## 6. Certification FNE/RNE — préparée, simulée, jamais appelée

- Interface de service : `finance/fne.py::InvoiceCertificationProvider`.
- Fournisseur livré : `MockFNEProvider` →
  `{"status": "not_certified_demo", "reference": null, "message": "Certification
  FNE non activée dans le prototype"}`.
- Le futur adaptateur de l'API DGI (facturation normalisée électronique,
  https://www.fne.dgi.gouv.ci/facturation.php) se branchera en implémentant
  l'interface et en remplaçant le fournisseur retourné par
  `get_certification_provider()`. **Le prototype ne l'appelle jamais**, ne
  fabrique aucun QR FNE, n'utilise aucun secret, et ne mentionne jamais
  « facture certifiée ».

## 7. Modèle de données

Migrations **idempotentes** (`finance/store.py`, DDL_STATEMENTS) :
`CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS`. La table `payments`
existante (~151 k lignes seedées) continue de fonctionner ; les colonnes NOT NULL
sont ajoutées avec des DEFAULT sûrs (`status='paid'`, `currency='XOF'`).

| Table | Rôle |
|---|---|
| `payments` (évolution) | + `transaction_id`, `status`, `gross_amount`, `currency`, `provider_key`, `line_id`, `stop_id`, `created_at`, `updated_at` ; **index unique sur `ticket_id`** |
| `customer_documents` | factures/reçus clients (`document_type`, montants, `fne_status`, `verification_token`, …) |
| `driver_stubs` | souches conducteur (frais, commission, provision, net, `settlement_status`, + colonne `provider` pour le filtre opérateur) |
| `driver_expenses` | dépenses (13 catégories, référence justificatif) |
| `tax_rules` | moteur fiscal configurable et versionné (+ colonne `tax_target` : `customer` \| `operator`) |
| `tax_calculations` | un calcul par (paiement × règle), avec `calculation_kind` |
| `daily_closures` | clôtures journalières, `UNIQUE (driver_id, closure_date)` |
| `finance_sequences` | séquences de numérotation atomiques |

Deux particularités documentées :

1. **Déduplication des ticket_id seedés** : le seed historique tirait 6 caractères
   hexa aléatoires (24 bits) → ~695 doublons sur 151 k lignes (paradoxe des
   anniversaires). La migration renomme les doublons en `ABJ-` + id de ligne en hexa
   complété à 8 caractères — longueur disjointe de l'espace aléatoire à 6 caractères,
   donc sans collision possible et unique par construction — **avant** de poser
   l'index unique exigé. Aucune autre donnée n'est modifiée. `seed_analytics.py`
   génère désormais des numéros séquentiels (sans collision) pour les installations
   fraîches.
2. **Backfill one-shot** : au premier démarrage avec PostgreSQL, les paiements seedés
   des 7 derniers jours (avant aujourd'hui, plafonnés à 2 500) reçoivent documents +
   souches (`settlement_status='settled'`) pour donner de la matière aux tableaux de
   bord. Le jour même n'est pas backfillé : le dashboard du jour repose sur les
   recettes de démonstration + les paiements live (cohérence avec
   `/api/driver/{id}/receipts`).

## 8. Numérotation

| Document | Format | Exemple |
|---|---|---|
| Billet (existant) | `ABJ-XXXXXX` | `ABJ-A8D68C` |
| Paiement | `PAY-XXXXXXXX` | `PAY-3F9C21AB` |
| Transaction comptable | `TRX-XXXXXXXX` | `TRX-77B0E4D2` |
| Facture / reçu client | `FAC-AAAA-NNNNNN` | `FAC-2026-000123` |
| Souche conducteur | `STB-AAAA-NNNNNN` | `STB-2026-000123` |
| Clôture de journée | `CLR-AAAA-NNNNNN` | `CLR-2026-000007` |
| QR de vérification | `ABJMOB\|VERIF\|FAC-AAAA-NNNNNN\|jeton` | — |

Séquences annuelles atomiques (table `finance_sequences` / compteurs mémoire).

## 9. Endpoints

Nouveaux (préfixe `/api`, erreurs explicites 404/422) :

| Méthode | Chemin | Rôle |
|---|---|---|
| GET | `/customer/documents/{document_id}` | reçu complet (+ lignes fiscales, QR) |
| GET | `/customer/documents/{document_id}/verify?token=` | vérification par jeton |
| GET | `/driver/{driver_id}/stubs` | souches filtrées (dates, ligne, opérateur, reversement) + totaux |
| GET | `/driver/{driver_id}/stubs/{stub_id}` | détail d'une souche (+ taxes) |
| GET | `/driver/{driver_id}/financial-summary` | vue d'ensemble jour/semaine |
| GET/POST | `/driver/{driver_id}/expenses` | dépenses (filtres / création 201) |
| DELETE | `/driver/{driver_id}/expenses/{expense_id}` | suppression (204, 404) |
| GET | `/driver/{driver_id}/tax-summary` | synthèse fiscale par règle (7 j par défaut) |
| GET/POST | `/driver/{driver_id}/daily-closures` | clôtures (création 201, déjà clôturée 200) |
| GET | `/tax-rules` | règles configurées |

Compatibilité préservée : `POST /api/payments` et
`GET /api/driver/{driver_id}/receipts` gardent leur contrat exact — le frontend
existant fonctionne inchangé ; les informations financières viennent **en complément**
dans la réponse de paiement.

## 10. Architecture technique

```
demo/backend/finance/
├── models.py               # dataclasses partagées (documents, souches, dépenses…)
├── fees.py                 # frais 1 % + commission 1,5 % (VALEURS DE DÉMO)
├── tax_engine.py           # moteur fiscal pur (aucune dépendance base)
├── fne.py                  # InvoiceCertificationProvider + MockFNEProvider
├── documents.py            # contexte de paiement → transaction complète
├── documents_numbering.py  # formats FAC/STB/CLR-AAAA-NNNNNN
├── store.py                # MemoryFinanceStore + PostgresFinanceStore (même interface)
├── service.py              # façade best-effort (jamais bloquante) + seeds + backfill
└── api.py                  # routeur FastAPI des endpoints ci-dessus
```

Comme `analytics.py`, la persistance est **best-effort** : sans `DATABASE_URL`
(mode `demo/demo.sh`) ou si PostgreSQL est indisponible, les documents vivent en
mémoire et la démo continue sans erreur (`finance_store: "memory"` dans
`/api/health`). Le moteur fiscal et la génération de documents sont **purs** :
testables sans aucune base (c'est le choix retenu pour pytest).

## 11. Procédure de test

```bash
make test            # pytest : 23 tests, SANS PostgreSQL (store mémoire)
make lint && make format-check   # ruff + black
cd demo/frontend && npm run build  # le frontend se construit
make restart         # stack docker (api + db + metabase + nginx)
bash demo/smoke-test.sh                       # 10 vérifications (:8000)
API=http://localhost:8080 bash demo/smoke-test.sh   # via nginx
```

Parcours fonctionnel rapide (curl) :

```bash
# 1. Paiement → document + souche
curl -s -X POST localhost:8000/api/payments -H 'Content-Type: application/json' \
  -d '{"line_name":"Woro Riviera","mode":"woro","fare":300,"provider":"wave",
       "driver_id":"drv_001","line_id":"wo_riviera","stop_id":"st_riviera2",
       "dest_stop_id":"st_plateau_cite"}' | python3 -m json.tool
# → document_id, document_number (FAC-…), verification_token, financial.net_amount

# 2. Reçu + vérification
curl -s localhost:8000/api/customer/documents/{document_id} | python3 -m json.tool
curl -s "localhost:8000/api/customer/documents/{document_id}/verify?token={token}"

# 3. Souches, résumé, taxes, clôture
curl -s "localhost:8000/api/driver/drv_001/stubs?provider=Wave" | python3 -m json.tool
curl -s localhost:8000/api/driver/drv_001/financial-summary | python3 -m json.tool
curl -s localhost:8000/api/driver/drv_001/tax-summary | python3 -m json.tool
curl -s -X POST localhost:8000/api/driver/drv_001/daily-closures -H 'Content-Type: application/json' -d '{}'

# 4. Règles fiscales
curl -s localhost:8000/api/tax-rules | python3 -m json.tool
```

Interface : http://localhost:8080 → payer un trajet → billet → « Voir le reçu » /
« Imprimer / PDF » / « Partager » ; « Mode conducteur » → onglets Ma caisse.
