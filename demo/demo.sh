#!/usr/bin/env bash
# Démo AbidjanMob — démarre l'API (port 8000) et l'interface web (port 4173).
# Usage : bash demo.sh   (Ctrl+C pour tout arrêter)
set -euo pipefail
cd "$(dirname "$0")"

PIDS=()
cleanup() {
  for p in "${PIDS[@]:-}"; do kill "$p" 2>/dev/null || true; done
}
trap cleanup EXIT INT TERM

echo "① Backend FastAPI…"
cd backend
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q -r requirements.txt
./.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
PIDS+=($!)
cd ..

echo "② Interface web…"
cd frontend
[ -d node_modules ] || npm install --no-fund --no-audit
if [ -z "$(find public/tiles -name '*.png' 2>/dev/null | head -1)" ]; then
  echo "   Premier lancement : récupération des tuiles de carte (~4 min, une seule fois)."
  python3 scripts/fetch_tiles.py
fi
npm run build
npx vite preview --host 127.0.0.1 --port 4173 --strictPort &
PIDS+=($!)
cd ..

echo
echo "✅ Démo AbidjanMob prête :  http://127.0.0.1:4173"
echo "   API (docs Swagger)    :  http://127.0.0.1:8000/docs"
echo "   Ctrl+C pour arrêter."
wait
