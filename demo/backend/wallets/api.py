"""Points d'entrée HTTP du module portefeuilles (simulation)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .service import WalletError, get_service

router = APIRouter()


class UnlockRequest(BaseModel):
    pin: str


class TopupRequest(BaseModel):
    pin: str
    provider: str
    amount: int = Field(gt=0, le=1_000_000)


@router.post("/wallets/unlock")
def unlock(req: UnlockRequest):
    """Débloque l'accès aux soldes par code secret. Simulation : 4 chiffres
    quelconques (comme le code de paiement), aucun compte réel n'est touché."""
    try:
        return get_service().unlock(req.pin)
    except WalletError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wallets/topup")
def topup(req: TopupRequest):
    """Recharge un portefeuille virtuel depuis le « vrai » compte de l'opérateur
    (simulation dans le prototype : les APIs PSP arriveront avec le MVP)."""
    try:
        result = get_service().topup(req.pin, req.provider, req.amount)
    except WalletError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if result is None:
        raise HTTPException(status_code=503, detail="Portefeuilles indisponibles")
    return result


@router.post("/wallets/reset")
def reset():
    """Réinitialise les soldes de démonstration (utile pendant les répétitions)."""
    result = get_service().reset()
    if result is None:
        raise HTTPException(status_code=503, detail="Portefeuilles indisponibles")
    return result


@router.get("/wallets/transactions")
def transactions(limit: int = 50):
    """Journal des mouvements (paiements + historique de démonstration)."""
    result = get_service().history(limit)
    if result is None:
        raise HTTPException(status_code=503, detail="Portefeuilles indisponibles")
    return {"transactions": result}


@router.get("/wallets/spending-summary")
def spending_summary():
    """Bilan des dépenses de transport du passager par période (jour, semaine,
    mois, trimestre) : totaux, paiements, répartition par opérateur."""
    result = get_service().spending_summary()
    if result is None:
        raise HTTPException(status_code=503, detail="Portefeuilles indisponibles")
    return result
