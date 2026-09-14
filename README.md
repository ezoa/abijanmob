# AbidjanMob — Plateforme d'interopérabilité des transports d'Abidjan

Prototype de démonstration (AIMD 2026) : information multimodale + paiement QR mobile money
sur le corridor pilote **Cocody–Plateau–Adjamé**.

> ⚠️ Prototype : données indicatives, paiements **simulés** (aucun argent réel).

## Structure

```
abidjanmod/
├── data/corpus/        # corpus pilote (arrêts, lignes, tarifs) — indicatif
├── demo/
│   ├── backend/        # API FastAPI + moteur d'itinéraires
│   └── frontend/       # Démo web React (cadre smartphone)
└── docs/               # plan MVP, journal de suivi, scénario de démo
```

## Documentation

- `docs/plan-mvp.md` — plan MVP 6 mois (oct. 2026 → mars 2027)
- `docs/journal-de-suivi.md` — journal des étapes de réalisation
- `docs/scenario-demo.md` — scénario de démonstration (à venir)

## Lancer la démo

### Option A — Docker (recommandé)

```bash
docker compose up --build
```

- Interface : **http://localhost:8080** · API (docs Swagger) : http://localhost:8000/docs
- Sur un clone frais, le service `tiles-init` récupère les tuiles au premier lancement
  (~4 min) ; ensuite tout fonctionne **hors-ligne**.
- Arrêt : `docker compose down`

### Option B — Script local (sans Docker)

```bash
bash demo/demo.sh
```

- Interface : **http://127.0.0.1:4173** · API : http://127.0.0.1:8000/docs

> ⚠️ Un mode à la fois : le port 8000 est partagé. Faire `docker compose down` avant
> `demo.sh`, et inversement.

## Comment tester

### 1. Test automatique (5 secondes)

```bash
bash demo/smoke-test.sh                        # API directe (:8000)
API=http://localhost:8080 bash demo/smoke-test.sh   # via nginx (docker)
```

Vérifie : API en ligne, corpus (12 lignes / 20 arrêts), 14 POI, itinéraire phare
(≥ 3 options), flotte en direct (≥ 20 véhicules en mouvement), ETA, paiement simulé,
dashboard conducteur. **Résultat attendu : 8/8 OK.**

### 2. Parcours manuel complet (à faire au moins 2 fois avant le jour J)

Sur http://localhost:8080, suivre dans l'ordre — chaque point est un clic :

1. **Accueil** : carte visible, véhicules 🚐🚕 qui circulent, légende « En direct »
2. **⚡ Trajet démo** → 3 options : SOTRA 36 min/300 F · informel 39 min/500 F · taxi 25 min/1 900 F
3. **Option informelle** : chip « 🔴 … arrive à Riviera 2 dans ~X min » — le compte à
   rebours descend-il ?
4. **Détails de l'itinéraire** : étapes, attente, marche, tarifs
5. **Payer ce trajet** → Scanner le QR → conducteur Koffi → Wave → code (4 chiffres
   quelconques) → billet numérique avec QR
6. **Billet** : chip « Votre woro arrive dans ~X min »
7. **👀 Voir côté conducteur** : recettes, répartition par opérateur, « monnaie
   rendue : 0 F »
8. **Refaire un paiement** → la nouvelle recette apparaît dans le dashboard en < 5 s

### 3. Variantes à essayer

- Autres trajets : *Yopougon Siporex → Zone 4* (multimodal, bateau-bus) ·
  *Treichville → Cité Administrative* (bateau direct, 200 F)
- Inverser départ/destination (⇅) · les 4 opérateurs mobile money
- Bouton ⛶ plein écran (projection) · bouton « Mode conducteur » depuis l'accueil

### 4. Robustesse (plan B)

- **Hors-ligne** : couper le wifi puis recharger la page → tout doit continuer de marcher
- **Redémarrage** : `docker compose down && docker compose up -d` → état intact
- API Swagger : http://localhost:8000/docs (si le jury veut voir l'API)

### 5. Comportements normaux (ce ne sont pas des bugs)

- ETA variables : les véhicules bougent réellement (simulation accélérée ×4, mention
  affichée)
- Zoom très rapproché hors corridor : tuiles absentes (cache limité au corridor, z10–15)
- Le taxi n'offre pas de paiement : hors plateforme, affiché pour comparaison
- Chaque `smoke-test.sh` ajoute un paiement simulé au dashboard conducteur

Scénario complet de présentation au jury : `docs/scénario-démo.md`.

Fond de carte : © OpenStreetMap contributors.
