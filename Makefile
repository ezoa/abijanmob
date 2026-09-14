# AbidjanMob — démo · gestion de la stack
# « make help » (ou « make ») liste toutes les commandes.

API_VENV := demo/backend/.venv
PY_FILES := demo/backend/main.py demo/backend/routing_engine.py demo/backend/live.py demo/frontend/scripts/fetch_tiles.py

.DEFAULT_GOAL := help

.PHONY: help up down build restart logs ps demo smoke smoke-nginx tiles deps-dev lint lint-fix format format-check

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

up: ## Démarre la stack docker (build si nécessaire)
	docker compose up --build -d
	@echo ""
	@echo "→ Interface : http://localhost:8080 · API : http://localhost:8000/docs"

down: ## Arrête la stack docker
	docker compose down --remove-orphans

build: ## (Re)construit les images
	docker compose build

restart: ## Redémarre la stack (down + up)
	docker compose down --remove-orphans && docker compose up --build -d

logs: ## Suit les logs de la stack (Ctrl+C pour quitter)
	docker compose logs -f

ps: ## État des conteneurs
	docker compose ps

demo: ## Mode local sans docker (demo/demo.sh)
	bash demo/demo.sh

smoke: ## Test de fumée — API directe (:8000)
	bash demo/smoke-test.sh

smoke-nginx: ## Test de fumée — via nginx (:8080)
	API=http://localhost:8080 bash demo/smoke-test.sh

tiles: ## Récupère les tuiles de carte manquantes (idempotent)
	python3 demo/frontend/scripts/fetch_tiles.py

deps-dev: ## Installe les outils de développement (ruff, black)
	[ -d $(API_VENV) ] || python3 -m venv $(API_VENV)
	$(API_VENV)/bin/pip install -q -r demo/backend/requirements-dev.txt

lint: deps-dev ## Lint Python (ruff)
	$(API_VENV)/bin/ruff check $(PY_FILES)

lint-fix: deps-dev ## Lint + corrections automatiques sûres (ruff --fix)
	$(API_VENV)/bin/ruff check --fix $(PY_FILES)

format: deps-dev ## Formate le code Python (black)
	$(API_VENV)/bin/black $(PY_FILES)

format-check: deps-dev ## Vérifie le formatage sans modifier (black --check)
	$(API_VENV)/bin/black --check $(PY_FILES)
