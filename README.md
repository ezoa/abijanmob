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

Scénario conseillé : bouton « ⚡ Trajet démo » → comparer les options formel/informel/taxi →
« Payer ce trajet » → QR conducteur → opérateur mobile money → code (4 chiffres quelconque) →
billet numérique → « Mode conducteur » pour voir la recette arriver en direct.

Fond de carte : © OpenStreetMap contributors.
