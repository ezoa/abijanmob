# Scénario de démonstration — AbidjanMob (jury AIMD)

Durée conseillée : **8–11 minutes** + questions. Répété au moins deux fois avant le jour J.

## 0. Avant de commencer (checklist)

- [ ] `docker compose up --build` (ou `bash demo/demo.sh`) lancé → http://localhost:8080 ouvert
- [ ] Vérifier la page d'accueil : carte du réseau visible, **véhicules 🚐🚕 circulant
      en direct**, 14 lieux proposés
- [ ] Mode plein écran (bouton ⛶) si projection ; F11 pour le navigateur
- [ ] Fermer les onglets/notifications parasites ; couper les mises à jour

## 1. Accroche (1 min) — les 3 problèmes du dossier

> « À Abidjan, 6 millions d'habitants se déplacent sans information fiable : ni horaires,
> ni tarifs, ni itinéraires pour les gbakas et woro-woro. À la descente, l'apprenti rend
> la monnaie de cinq passagers en même temps. Et le mobile money, pourtant universel,
> reste hors des transports informels. **AbidjanMob répond aux trois problèmes d'un coup,
> avec une seule idée : le paiement génère la donnée.** »

## 2. Pilier INFORMATION (3 min)

1. Sur l'accueil : « *Où allez-vous ?* » — cliquer **⚡ Trajet démo : Riviera 2 → Cité Administrative**.
2. Lire les résultats à voix haute :
   - **Bus SOTRA L105 direct** — 36 min, 300 F → *« l'usager ne savait même pas que cette
     ligne directe existait »*
   - **Réseau informel : Woro Riviera + Woro Plateau** — 39 min, 500 F, 1 correspondance →
     *« l'informel est enfin visible, comparé, avec tarifs et fréquences estimées »*
   - **Taxi estimé** — 25 min mais 1 900 F → *« l'alternative chère, en un coup d'œil »*
3. Déplier les détails d'un itinéraire : étapes, attente estimée, marche, CO₂ évité.
4. Montrer la carte : le réseau complet (cliquer une ligne → tarif et fréquence) et les
   **véhicules qui circulent en direct**.
   Variante pour questions : tester *Yopougon Siporex → Zone 4* (3 options multimodales
   dont le bateau-bus) ou *Treichville → Cité Administrative* (bateau direct, 200 F).

## 3. Suivi en direct (1–2 min) — personne n'attend dans le vide

1. Sur l'option informelle, montrer la chip **« 🔴 Woro Riviera — arrive à Riviera 2
   dans ~X min · puis ~Y min »** : le compte à rebours défile sous les yeux du jury.
2. Montrer le véhicule 🚕 correspondant qui avance sur la carte.
   > « L'usager sait exactement quand se présenter à l'arrêt — il n'attend pas dans le
   > vide. Et le conducteur ne tourne pas à vide non plus : le partage de position fait
   > gagner du temps aux deux côtés. »
3. (Optionnel) « Mode conducteur » → carte **📍 Position partagée** : le conducteur voit
   ce que voient les usagers, en temps réel.

## 4. Pilier PAIEMENT (3 min) — « zéro monnaie, zéro friction »

1. Choisir l'option informelle → **Payer ce trajet · 500 F**.
2. **Scanner le QR du conducteur** → « chaque conducteur affiche une carte QR plastifiée ;
   aucun smartphone spécial, aucun équipement à acheter ».
3. **Débloquer mes comptes** avec le code secret (4 chiffres, simulation) →
   répartition du paiement entre les portefeuilles virtuels (le bouton « Remplir
   automatiquement » propose la répartition ; on peut aussi la répartir sur
   plusieurs comptes) → **Payer**.
4. Billet numérique : QR, montant exact, horodatage.
   > « Le débit est du montant **exact** du trajet. L'apprenti ne cherche plus de monnaie,
   > le conducteur ne refuse plus de client. »
5. Basculer en **🚐 Mode conducteur** (bouton du bandeau) → le paiement apparaît
   **en direct** dans « Ma caisse » : recettes du jour, répartition par opérateur,
   *monnaie rendue : 0 F* → revenir avec **👤 Mode passager**.

## 5. La boucle données (1 min) — le cœur de l'innovation

> « Chaque paiement produit une donnée structurée : ligne, tarif, heure, position.
> Des milliers de paiements = la cartographie vivante du transport informel d'Abidjan,
> sans campagne de mesure coûteuse. C'est l'IA collaborative du dossier : elle valide,
> consolide, et améliore les itinéraires de tous les usagers, chaque jour. »

## 6. Conclusion (1 min) — vision et faisabilité

> « Ce prototype fonctionne dès aujourd'hui sur le corridor Cocody–Plateau–Adjamé.
> Le MVP (octobre 2026 – mars 2027) ajoute les paiements réels Wave/Orange, l'application
> mobile, et le pilote avec 30 à 50 conducteurs. Feuille de route détaillée : docs/plan-mvp.md. »

## 7. Transparence — questions probables du jury

| Question | Réponse courte |
|---|---|
| « C'est du vrai paiement ? » | Non — **simulation PSP** dans le prototype ; intégrations Wave/Orange (API existantes) planifiées M1–M3 du MVP. Le flux applicatif, lui, est réel de bout en bout. |
| « Les positions véhicules sont réelles ? » | Simulation accélérée ×4 dans le prototype (mention affichée). En MVP : GPS du smartphone conducteur (ou boîtier dédié) vers les mêmes endpoints — l'architecture est identique. |
| « Les données sont fiables ? » | Corpus **indicatif** pour la démo ; remplacé par l'enquête terrain M0 puis enrichi en continu par la boucle paiement→donnée. |
| « Quel moteur de routage ? » | Prototype : moteur léger custom (graphe arrêts/lignes, Dijkstra multi-critères). Cible MVP : **OpenTripPlanner 2** + OpenStreetMap (open source éprouvés) — cf. plan. |
| « Les conducteurs sans smartphone ? » | Carte QR **statique** imprimée : le passager scanne, le conducteur reçoit une confirmation (app ou SMS). Zéro barrière à l'entrée. |
| « Pourquoi l'informel n'est pas toujours le moins cher ? » | C'est exactement le propos : **comparer objectivement** formel et informel. Sur certains trajets le bus formel gagne — l'usager le découvre grâce à AbidjanMob. |
| « Comment gagnez-vous de l'argent ? » | Commission 1–2 % par transaction, données de mobilité anonymisées (AMUGA/SOTRA/urbanistes), offres B2B — cf. dossier §5.3. |
| « Et l'IA ? » | v1 : validation automatique des contributions (clustering GPS, détection d'anomalies tarifaires) et estimation dynamique des tarifs. v2 : prédiction de congestion, itinéraires alternatifs. |
| « Et les données pour les décideurs ? » | **Montrer Metabase (http://localhost:3000)** : profils horaires, top arrêts, recettes par opérateur — c'est le produit « données anonymisées » de Phase 2 (AMUGA/SOTRA/urbanistes, dossier §5.3). Chaque paiement fait pendant la démo y apparaît. Données synthétiques pour le prototype. |

## 8. Plan B (si panne le jour J)

- La démo est **100 % hors-ligne** après le premier lancement (tuiles en cache, API locale) —
  couper le wifi ne change rien.
- Si la carte ne s'affiche pas (problème graphique) : l'app le signale et **itinéraires +
  paiement + dashboard restent utilisables** — poursuivre le scénario sans carte.
- Capture d'écran de secours : garder `docs/captures/` à jour (faire F12 → capture
  complète de chaque écran avant le jour J).
