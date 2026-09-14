# Dashboards décideurs — Metabase

> Le « produit données » du dossier AIMD (Phase 2 : vente de données anonymisées à
> AMUGA, SOTRA, urbanistes). Données **synthétiques** pour le prototype (14 jours,
> pics d'heure de pointe), **sans aucune donnée personnelle**.

## 1. Première configuration (2 minutes, une seule fois)

1. Ouvrir **http://localhost:3000** (laisser ~1 min à Metabase au premier démarrage)
2. Choisir la langue → « Commencer »
3. Créer le compte administrateur (ex. `admin@abidjanmob.local` + mot de passe local —
   c'est une instance de démonstration)
4. « Ajouter vos données » → **PostgreSQL** :
   - Hôte : `db` · Port : `5432`
   - Base : `abidjanmob` · Utilisateur : `abidjanmob` · Mot de passe : `abidjanmob`
   - Enregistrer
5. L' état est conservé dans le volume `metabase-data` : plus jamais à refaire
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
