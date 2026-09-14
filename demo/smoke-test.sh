#!/usr/bin/env bash
# Test de fumée AbidjanMob — vérifie les endpoints principaux en quelques secondes.
# Usage : bash demo/smoke-test.sh   (API attendue sur http://localhost:8000,
# ou : API=http://localhost:8080 bash demo/smoke-test.sh pour passer par nginx)
set -uo pipefail

API="${API:-http://localhost:8000}"
pass=0
fail=0

check() {
  if [ "$2" -eq 0 ]; then
    echo "✓ $1"
    pass=$((pass + 1))
  else
    echo "✗ $1"
    fail=$((fail + 1))
  fi
}

echo "— Tests de fumée AbidjanMob (API : $API) —"

curl -sf "$API/api/health" >/dev/null
check "API en ligne (/api/health)" $?

n=$(curl -sf "$API/api/network" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['lines']), len(d['stops']['features']))" 2>/dev/null)
lines=${n% *}
stops=${n#* }
[ "${lines:-0}" -ge 12 ] && [ "${stops:-0}" -ge 20 ]
check "Corpus réseau ($lines lignes / $stops arrêts)" $?

n=$(curl -sf "$API/api/pois" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))" 2>/dev/null)
[ "${n:-0}" -ge 13 ]
check "POI de recherche ($n lieux)" $?

n=$(curl -sf -X POST "$API/api/plan" -H 'Content-Type: application/json' \
  -d '{"from_poi":"riviera2","to_poi":"cite_administrative"}' |
  python3 -c "import json,sys; print(len(json.load(sys.stdin)['itineraries']))" 2>/dev/null)
[ "${n:-0}" -ge 3 ]
check "Itinéraire phare Riviera 2 → Cité Administrative ($n options)" $?

python3 - "$API" <<'EOF'
import json, sys, time, urllib.request

api = sys.argv[1]

def live():
    with urllib.request.urlopen(api + "/api/drivers/live") as r:
        return {v["vehicle_id"]: (v["lat"], v["lon"]) for v in json.load(r)}

a = live()
time.sleep(0.3)
b = live()
sys.exit(0 if len(a) >= 20 and a != b else 1)
EOF
check "Flotte en direct (≥20 véhicules, positions en mouvement)" $?

eta=$(curl -sf "$API/api/lines/wo_riviera/eta?stop_id=st_riviera2" |
  python3 -c "import json,sys; print(json.load(sys.stdin)['eta_min'])" 2>/dev/null)
[ -n "${eta:-}" ]
check "ETA Woro Riviera → Riviera 2 (~${eta} min)" $?

tid=$(curl -sf -X POST "$API/api/payments" -H 'Content-Type: application/json' \
  -d '{"line_name":"Woro Riviera","mode":"woro","fare":300,"provider":"wave","driver_id":"drv_001"}' |
  python3 -c "import json,sys; print(json.load(sys.stdin)['ticket_id'])" 2>/dev/null)
[ -n "${tid:-}" ]
check "Paiement simulé ($tid)" $?

total=$(curl -sf "$API/api/driver/drv_001/receipts" |
  python3 -c "import json,sys; print(json.load(sys.stdin)['total'])" 2>/dev/null)
[ "${total:-0}" -ge 4400 ]
check "Dashboard conducteur (recettes du jour : ${total} F)" $?

echo
if [ "$fail" -eq 0 ]; then
  echo "Résultat : $pass/$pass tests OK ✅"
  exit 0
else
  echo "Résultat : $pass OK, $fail échec(s) ❌"
  exit 1
fi
