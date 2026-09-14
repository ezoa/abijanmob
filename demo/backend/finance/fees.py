"""Frais appliqués aux paiements — VALEURS FICTIVES DE DÉMONSTRATION.

Ces taux ne correspondent à aucun tarif officiel de PSP ni à aucune commission
réelle : ce sont des constantes de démonstration, librement ajustables, choisies
pour illustrer le mécanisme « brut − frais − commission = net conducteur ».
"""

from __future__ import annotations

# Frais de paiement (frais PSP facturés au conducteur) — démonstration.
PAYMENT_FEE_RATE_PCT = 1.0
# Commission de la plateforme AbidjanMob — démonstration.
PLATFORM_COMMISSION_RATE_PCT = 1.5


def _round_f(x: float) -> int:
    """Arrondi commercial au franc (0,5 → 1), montants toujours positifs."""
    return max(0, int(x + 0.5))


def compute_fees(gross_amount: int) -> tuple[int, int]:
    """(frais de paiement, commission plateforme) pour un montant brut donné."""
    payment_fee = _round_f(gross_amount * PAYMENT_FEE_RATE_PCT / 100.0)
    platform_fee = _round_f(gross_amount * PLATFORM_COMMISSION_RATE_PCT / 100.0)
    return payment_fee, platform_fee
