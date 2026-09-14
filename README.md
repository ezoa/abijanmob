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

```bash
bash demo/demo.sh
```

Puis ouvrir **http://127.0.0.1:4173** dans un navigateur.

- Premier lancement : installe les dépendances et récupère les tuiles de carte (~4 min).
- Lancements suivants : démarrage en quelques secondes, **fonctionne hors-ligne**
  (tuiles en cache local, aucun service externe requis).
- API (docs Swagger) : http://127.0.0.1:8000/docs

Scénario conseillé : bouton « ⚡ Trajet démo » → comparer les options formel/informel/taxi →
« Payer ce trajet » → QR conducteur → opérateur mobile money → code (4 chiffres quelconque) →
billet numérique → « Mode conducteur » pour voir la recette arriver en direct.

Fond de carte : © OpenStreetMap contributors.
