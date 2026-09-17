"""Portefeuilles mobile money du passager (simulation) : paiement multi-comptes.

Le prototype ne débite AUCUN compte réel : les soldes vivent dans la base de la
démo (PostgreSQL en docker, mémoire en local). L'utilisateur débloque l'accès à
ses soldes par un code secret (4 chiffres, simulation), choisit combien prélever
sur chaque opérateur, et le paiement est soldé par la somme des prélèvements
(ex. 1 400 F = 400 Wave + 600 Orange + 400 Moov). Dans le MVP réel, ce seront
les adaptateurs PSP (clés réservées dans .env.example) qui exécuteront chaque
prélèvement avec le consentement de l'utilisateur, validé dans son application
mobile money : AbidjanMob orchestre, les PSP exécutent.

Modules :
- models   — constantes (opérateurs, soldes initiaux) + WalletError
- store    — persistance : PostgreSQL (docker) ou mémoire (local / tests)
- service  — façade best-effort (déverrouillage, débit, reset, historique)
- api      — points d'entrée HTTP du module
"""

from .models import PROVIDERS, SOLDES_INITIAUX, WalletError
from .service import configure_for_tests, get_service

__all__ = [
    "PROVIDERS",
    "SOLDES_INITIAUX",
    "WalletError",
    "configure_for_tests",
    "get_service",
]
