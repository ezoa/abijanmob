# Dashboards décideurs — Metabase

> Le « produit données » du dossier AIMD (Phase 2 : vente de données anonymisées à
> AMUGA, SOTRA, urbanistes). Données **synthétiques** pour le prototype (14 jours,
> pics d'heure de pointe), **sans aucune donnée personnelle**.

## 1. Première configuration (2 minutes, une seule fois)

1. Ouvrir **http://localhost:3000** (laisser ~1 min à Metabase au premier démarrage)
2. Choisir la langue → « Commencer »
3. Créer le compte administrateur (ex. `admin@abidjanmob.local` + mot de passe local —
   c'est une instance de démonstration)
4. « Ajouter vos données » → type **PostgreSQL**, puis remplir le formulaire ainsi :

| Champ du formulaire | Valeur | D'où ça vient |
|---|---|---|
| Nom | `AbidjanMob analytics` (libre — simple libellé) | votre choix |
| Hôte | `db` | nom du service `db` dans docker-compose.yml (réseau interne Docker) |
| Port | `5432` | port interne PostgreSQL |
| Nom de la base de données | `abidjanmob` | `POSTGRES_DB` du service `db` |
| Nom d'utilisateur | `abidjanmob` | `POSTGRES_USER` du service `db` |
| Mot de passe | `abidjanmob` | `POSTGRES_PASSWORD` du service `db` |

   Astuce : tout est « abidjanmob », sauf l'hôte (`db`) et le port (`5432`).
   Ne pas mettre « localhost » comme hôte : depuis le conteneur Metabase, `db`
   désigne le serveur PostgreSQL dans le réseau Docker.

5. L'état est conservé dans le volume `metabase-data` : plus jamais à refaire
   (sauf `docker compose down -v`).

## 2. Questions à créer (Nouvelle question → Native / SQL)

### a) Profil horaire — le double pic d'Abidjan
```sql
SELECT extract(hour FROM ts) AS heure,
       sum(boarded) AS montées,
       sum(alighted) AS descentes
FROM ridership_events
GROUP BY 1 ORDER BY 1;
```

### b) Top arrêts par montées (7 derniers jours)
```sql
SELECT stop_name AS arrêt, commune,
       sum(boarded) AS montées, sum(alighted) AS descentes
FROM ridership_events
WHERE ts > now() - interval '7 days'
GROUP BY 1, 2 ORDER BY montées DESC LIMIT 15;
```

### c) Réseau formel vs informel
```sql
SELECT CASE WHEN formal THEN 'Formel' ELSE 'Informel' END AS réseau,
       sum(boarded) AS passagers
FROM ridership_events GROUP BY 1;
```

### d) Charge par ligne
```sql
SELECT line_name AS ligne, mode,
       sum(boarded) AS montées, sum(alighted) AS descentes
FROM ridership_events GROUP BY 1, 2 ORDER BY montées DESC;
```

### e) Recettes par opérateur mobile money
```sql
SELECT provider AS opérateur,
       count(*) AS paiements, sum(fare) AS recettes
FROM payments GROUP BY 1 ORDER BY recettes DESC;
```

### f) Recettes et adoption par jour
```sql
SELECT date_trunc('day', ts)::date AS jour,
       count(*) AS paiements,
       sum(fare) AS recettes,
       round(100.0 * count(*) / NULLIF((SELECT sum(boarded) FROM ridership_events r
             WHERE date_trunc('day', r.ts) = date_trunc('day', payments.ts)), 0), 1) AS adoption_pct
FROM payments GROUP BY 1 ORDER BY 1;
```

## 3. Tableau de bord suggéré

Créer un tableau de bord « **Décideurs — corridor pilote AbidjanMob** » et y ajouter :
(a) en courbe, (b) en tableau/barres, (c)+(d) en camembert/barres, (e)+(f) en
chiffres/barres. Chaque paiement effectué pendant la démo s'y ajoutera en temps réel
(rafraîchir la question).

## 4. Accès direct à la base

```bash
make psql   # console psql dans le conteneur db
```

Tables : `ridership_events` (fréquentation : horodatage, ligne, mode, formel/informel,
arrêt, commune, direction, montées, descentes) · `payments` (billet, ligne, tarif,
opérateur, conducteur).

## 5. Module financier — questions supplémentaires

> Tables ajoutées par le module financier (voir `docs/module-financier.md`) :
> `customer_documents` (reçus/factures), `driver_stubs` (souches conducteur),
> `driver_expenses` (dépenses), `tax_rules` + `tax_calculations` (moteur fiscal),
> `daily_closures` (clôtures). Montants en FCFA. **Données de démonstration** :
> frais, commissions et taxes sont simulés (règles fictives `is_official=false`).

### g) Recettes brutes par jour (souches conducteur)
```sql
SELECT date_trunc('day', created_at)::date AS jour,
       count(*) AS paiements,
       sum(gross_amount) AS recettes_brutes
FROM driver_stubs
GROUP BY 1 ORDER BY 1;
```

### h) Recettes nettes conducteur par jour
```sql
SELECT date_trunc('day', created_at)::date AS jour,
       sum(net_amount) AS recettes_nettes,
       sum(payment_fee) AS frais_paiement,
       sum(platform_fee) AS commissions
FROM driver_stubs
GROUP BY 1 ORDER BY 1;
```

### i) Dépenses par catégorie
```sql
SELECT category AS catégorie,
       count(*) AS nb,
       sum(amount) AS total
FROM driver_expenses
GROUP BY 1 ORDER BY total DESC;
```

### j) Provisions et taxes par règle fiscale
```sql
SELECT r.code, r.label,
       tc.calculation_kind AS nature,
       count(*) AS calculs,
       sum(tc.calculated_amount) AS montant
FROM tax_calculations tc
JOIN tax_rules r ON r.id = tc.tax_rule_id
GROUP BY 1, 2, 3
ORDER BY montant DESC;
```
NB : `estimated_provision` = provision estimative répartie par course (taxe
journalière/mensuelle/annuelle) — jamais un prélèvement exigible par course.

### k) Résultat net estimé par conducteur et par jour
```sql
WITH recettes AS (
    SELECT driver_id,
           date_trunc('day', created_at)::date AS jour,
           sum(net_amount) AS net_conducteur,
           sum(tax_provision) AS provisions
    FROM driver_stubs GROUP BY 1, 2
), depenses AS (
    SELECT driver_id, expense_date AS jour, sum(amount) AS depenses
    FROM driver_expenses GROUP BY 1, 2
)
SELECT r.driver_id, r.jour,
       r.net_conducteur, r.provisions,
       coalesce(d.depenses, 0) AS depenses,
       r.net_conducteur - coalesce(d.depenses, 0) AS resultat_net_estime
FROM recettes r
LEFT JOIN depenses d ON d.driver_id = r.driver_id AND d.jour = r.jour
ORDER BY r.jour DESC, r.driver_id;
```

### l) Recettes par commune d'embarquement
```sql
SELECT commune,
       count(*) AS recus,
       sum(gross_amount) AS recettes
FROM customer_documents
WHERE commune IS NOT NULL
GROUP BY 1 ORDER BY recettes DESC;
```

### m) Souches par conducteur
```sql
SELECT driver_id,
       count(*) AS souches,
       sum(gross_amount) AS brut,
       sum(net_amount) AS net,
       sum(tax_provision) AS provisions,
       count(*) FILTER (WHERE settlement_status = 'pending') AS a_reverser
FROM driver_stubs
GROUP BY 1 ORDER BY brut DESC;
```
