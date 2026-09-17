"""Constantes et exception du module portefeuilles (simulation)."""

from __future__ import annotations

# Opérateurs mobile money simulés (doublon volontaire de main.PROVIDERS pour
# garder le module autonome, comme finance.models.MOBILE_MONEY_PROVIDERS).
PROVIDERS: dict[str, str] = {
    "wave": "Wave",
    "orange": "Orange Money",
    "mtn": "MTN MoMo",
    "moov": "Moov Money",
}

# Soldes de départ du compte passager de démonstration (F CFA). Volontairement
# modestes : la répartition multi-comptes devient naturelle dès qu'un trajet
# dépasse le solde d'un compte (ex. 1 400 F exige plusieurs opérateurs).
SOLDES_INITIAUX: dict[str, int] = {
    "wave": 400,
    "orange": 600,
    "mtn": 500,
    "moov": 500,
}

CODE_LONGUEUR = 4
COMPTE_DEMO = "demo"


class WalletError(Exception):
    """Refus métier : code invalide, répartition incohérente ou solde insuffisant."""
