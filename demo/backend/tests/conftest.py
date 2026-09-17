"""Configuration des tests backend AbidjanMob.

Les tests tournent SANS PostgreSQL : le module financier est forcé sur le store
mémoire (finance.store.MemoryFinanceStore). Le choix de conception — logique
métier pure (tax_engine, documents) + store interchangeable derrière une même
interface — rend le cœur financier testable sans docker ni base externe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Imports depuis demo/backend (main, finance, routing_engine…) — redondant avec
# pythonpath de pyproject.toml, mais robuste si pytest est lancé autrement.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finance import configure_for_tests  # noqa: E402
from wallets import configure_for_tests as configure_wallets_for_tests  # noqa: E402


def pytest_configure(config):
    # Force le store mémoire AVANT tout import d'application : aucun test ne
    # touche à PostgreSQL, même si DATABASE_URL était présent dans l'environnement.
    configure_for_tests()
    configure_wallets_for_tests()


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Client API avec événement de démarrage : le seed du jour de démonstration
    (SEED_RECEIPTS → transactions financières) est ainsi présent, comme en prod."""
    from main import app

    with TestClient(app) as c:
        yield c
