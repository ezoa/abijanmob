# Plan MVP AbidjanMob — Octobre 2026 → Mars 2027

> Version condensée du plan validé le 14/09/2026. Document de référence pour le jury AIMD
> et l'équipe. La démo de la semaine (14–17/09) en constitue la préfiguration (Phase 0).

## 1. Objectif du MVP

Livrer en 6 mois la plateforme complète sur le corridor pilote **Cocody–Plateau–Adjamé** :

- Application mobile usager (Android puis iOS) : itinéraires multimodaux, tarifs, paiement QR
- Paiement **réel** Wave / Orange Money intégré (MTN, Moov en adaptateurs)
- Module de contribution communautaire + validation automatique
- Pilote avec 30–50 conducteurs et recrutement d'usagers réels
- Partenariats signés avec les syndicats de transport

**Critères de fin de MVP** : apps Android + iOS en ligne · paiement Wave/OM réel · module
communautaire actif · pilote lancé sur le corridor · partenariats syndicats signés.
KPI pilote : taux de succès paiement > 95 % · planification < 2 s · ≥ 30 conducteurs actifs ·
≥ 500 trajets payés / semaine fin mars 2027.

## 2. Architecture cible

```
 App Usager      App Conducteur     Dashboard Ops
 (Flutter)       (Flutter)          (Flutter Web)
 ─────┬──────────────┬──────────────────┬─────
      └──────────────┼──────────────────┘
            ┌────────▼────────┐
            │  API Gateway    │  FastAPI — auth, métier
            └───┬─────────┬───┘
    ┌───────────▼──┐   ┌──▼─────────────────┐
    │ Itinéraires  │   │ Service Paiement   │ adaptateurs PSP + grand livre
    │ (OTP2)       │   │ (ledger, payouts)  │
    └──────┬───────┘   └──────┬─────────────┘
           └──────┬───────────┘
          ┌───────▼────────────┐
          │ PostgreSQL + PostGIS │ arrêts · lignes · tarifs · contributions · transactions
          └───────┬────────────┘
          ┌───────▼─────────────┐     ┌──────────────────────┐
          │ Pipeline Données    │────▶│ OpenTripPlanner 2    │
          │ OSM · GTFS · IA     │     │ (Docker, rebuild     │
          │ validation          │     │  nocturne)           │
          └─────────────────────┘     └──────────────────────┘
```

Stack : **Flutter** (apps) · **Python/FastAPI** (backend) · **PostgreSQL + PostGIS** ·
**OpenTripPlanner 2** (Docker) · **OpenStreetMap** · 1 VPS 4 vCPU / 8 Go, Docker Compose,
GitHub Actions.

## 3. Décisions techniques structurantes

1. **Paiement QR statique d'abord** : carte QR plastifiée chez le conducteur (ID + ligne) ;
   l'usager scanne, paie le montant exact, le conducteur reçoit la confirmation (push ou
   SMS). Aucun smartphone requis chez le conducteur — clé pour l'adoption Gbaka/Woro-woro.
2. **Transport informel modélisé en GTFS** (`frequencies.txt`, arrêts approximatifs) : OTP2
   planifie alors nativement le multimodal. Un « GTFS builder » convertit les données
   terrain/communautaires.
3. **Boucle données** : chaque trajet payé = (ligne, tarif, horodatage, point GPS). Clustering
   GPS → arrêts inférés ; statistiques robustes → tarifs dynamiques. Retour nightly dans le
   graphe OTP. C'est le principe « le paiement génère la donnée » du dossier AIMD.
4. **Adaptateurs PSP** : une interface, un adaptateur par opérateur (Wave, Orange Money, MTN,
   Moov) + PSP mock pour le développement (réutilisé par la démo actuelle).
5. **PII séparée des événements de mobilité dès le jour 1** : rend le produit « données
   anonymisées » (Phase 2 : AMUGA, SOTRA, urbanistes) peu coûteux au lieu d'une refonte.
6. **Authentification par numéro de téléphone (OTP)** ; KYC léger conducteur.

## 4. Planning M0 → M5

Responsables : **LD** = Lead Développeur · **CP** = Coordonnateur · **EX** = Experte Transformation Numérique.

| Mois | Thème | Chantiers clés | Livrable fin de mois |
|---|---|---|---|
| **M0 — oct. 2026** | Fondations & données | (LD) Monorepo, docker-compose, CI/CD, VPS ; extrait OSM Grand Abidjan ; GTFS builder v1 ; **graphe OTP2** ; API v0. (CP) Demandes d'agrément Wave + Orange **envoyées** ; LOI syndicats. (Tous) Campagne terrain #1 : 15–25 lignes corridor (tracés, arrêts, tarifs, fréquences) | Démo interne : itinéraire multimodal sur corridor avec données réelles collectées |
| **M1 — nov. 2026** | Paiement sandbox & apps v0 | Service paiement (adaptateurs, mock + premier PSP sandbox, QR statique/dynamique, ledger, webhooks). Apps Flutter v0 (usager, conducteur) + dashboard ops v0 | Flux paiement bout-en-bout en sandbox sur données corridor réelles |
| **M2 — déc. 2026** | Contribution & IA v1 | Module contribution in-app (signaler arrêt/tarif) ; pipeline validation (clustering GPS, détection anomalies tarifaires, file de revue) ; rebuild nightly ; service estimation tarifaire v1 ; campagne terrain #2 | La boucle fonctionne : contribution → validation → itinéraires améliorés |
| **M3 — janv. 2027** | Paiements réels & durcissement | Intégration production Wave/OM ; payouts conducteurs + ledger commissions ; sécurité (auth, anti-fraude, rate limits) ; mode offline/low-data ; Sentry. Bêta fermée ~50 usagers, ~10 conducteurs | Premières transactions réelles sur le corridor |
| **M4 — fév. 2027** | Pilote Cocody–Plateau | 30–50 conducteurs recrutés/formés (syndicats) ; cartes QR imprimées ; acquisition usagers aux arrêts ; monitoring (Prometheus/Grafana) ; support ; itérations hebdo | Pilote en marche : 300–500 trajets payés / semaine |
| **M5 — mars 2027** | Consolidation & lancement | Perf, iOS + stores, runbooks ; rapport pilote KPI ; reporting AIMD ; plan Phase 2 | **MVP lancé** · rapport pilote · plan croissance |

## 5. Risques majeurs & mitigations

| Risque | Mitigation |
|---|---|
| Accès APIs Wave/Orange lent (démarches commerciales) | Demandes dès la semaine 1 de M0 ; développement sur mock + sandbox MTN en parallèle ; architecture adaptateur |
| Qualité des données informelles | Boucle paiement→données + 2 campagnes terrain + revue humaine avant publication |
| Adoption conducteurs | QR statique (sans smartphone), partenariats syndicats, dashboard recettes = valeur immédiate |
| OTP ne promet pas d'horaires précis pour l'informel | UX honnête : itinéraires indicatifs (fréquences, pas horaires) |
| Coût data des usagers | Offline-first, tuiles cachées, APK léger, mode low-data |

## 6. Lien avec la démo de septembre 2026

La démo de cette semaine préfigure le MVP : moteur d'itinéraires (version légère ; OTP2 en
cible), corpus corridor (à remplacer par la campagne terrain M0), paiement mock (PSP réels en
M1/M3), dashboard conducteur. Tout le backend et les données sont réutilisés — zéro travail
perdu.
