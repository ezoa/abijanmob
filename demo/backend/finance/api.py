"""Points d'entrée HTTP du module financier (préfixe /api, via FastAPI router).

Tous les endpoints renvoient des erreurs explicites : 404 conducteur/document
inconnu, 422 paramètre invalide. Les endpoints existants (POST /api/payments,
GET /api/driver/{id}/receipts) restent dans main.py, contrat inchangé.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from routing_engine import get_network

from . import tax_engine
from .models import (
    EXPENSE_CATEGORIES,
    EXPENSE_CATEGORY_LABELS,
    SETTLEMENT_STATUSES,
    DriverExpense,
)
from .service import get_service

router = APIRouter()

DEFAULT_TAX_PERIOD_DAYS = 7


def _check_driver(driver_id: str) -> dict:
    net = get_network()
    driver = net.drivers.get(driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")
    return driver


def _driver_info(driver_id: str) -> dict:
    net = get_network()
    d = net.drivers[driver_id]
    line = net.lines.get(d["line_id"], {})
    return {"id": d["id"], "name": d["name"], "vehicle": d["vehicle"], "line": line.get("name")}


class ExpenseRequest(BaseModel):
    category: str
    amount: int = Field(gt=0, le=10_000_000)
    expense_date: date | None = None
    description: str = Field(default="", max_length=200)
    receipt_reference: str | None = Field(default=None, max_length=100)


class ClosureRequest(BaseModel):
    closure_date: date | None = None


# ------------------------------------------------------------------ règles fiscales


@router.get("/tax-rules")
def list_tax_rules():
    """Règles fiscales configurées (moteur versionné — aucune n'est officielle)."""
    rules = get_service().list_tax_rules()
    if rules is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return {
        "rules": rules,
        "category_labels": EXPENSE_CATEGORY_LABELS,
        "disclaimer": tax_engine.TAX_DISCLAIMER,
        "note": (
            "Toutes les règles livrées sont des règles de démonstration "
            "(is_official=false), désactivables ; aucun taux ivoirien officiel n'est codé en dur."
        ),
    }


# ------------------------------------------------------------------ documents clients


@router.get("/customer/documents/{document_id}")
def get_document(document_id: int):
    """Facture / reçu client complet (avec lignes fiscales et QR de vérification)."""
    doc = get_service().get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document inconnu")
    return doc


@router.get("/customer/documents/{document_id}/verify")
def verify_document(document_id: int, token: str = Query(min_length=8, max_length=64)):
    """Vérification d'un document par son jeton (contenu du QR AbidjanMob)."""
    result = get_service().verify_document(document_id, token)
    if result is None:
        raise HTTPException(status_code=404, detail="Document inconnu")
    return result


# ------------------------------------------------------------------ souches conducteur


@router.get("/driver/{driver_id}/stubs")
def list_stubs(
    driver_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
    line: str | None = None,
    provider: str | None = None,
    settlement_status: str | None = None,
):
    """Souches du conducteur, filtrables par date, ligne, opérateur, reversement."""
    _check_driver(driver_id)
    if settlement_status is not None and settlement_status not in SETTLEMENT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut de reversement invalide (valeurs : {' | '.join(SETTLEMENT_STATUSES)})",
        )
    result = get_service().list_stubs(
        driver_id, date_from, date_to, line, provider, settlement_status
    )
    if result is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    stubs, totals = result
    return {
        "driver": _driver_info(driver_id),
        "filters": {
            "date_from": date_from,
            "date_to": date_to,
            "line": line,
            "provider": provider,
            "settlement_status": settlement_status,
        },
        "count": totals.get("count", 0),
        "totals": totals,
        "stubs": stubs,
    }


@router.get("/driver/{driver_id}/stubs/{stub_id}")
def get_stub(driver_id: str, stub_id: int):
    """Détail d'une souche : décomposition nette + lignes fiscales."""
    _check_driver(driver_id)
    stub = get_service().get_stub_detail(driver_id, stub_id)
    if stub is None:
        raise HTTPException(status_code=404, detail="Souche inconnue")
    return stub


# ------------------------------------------------------------------ résumé financier


@router.get("/driver/{driver_id}/financial-summary")
def financial_summary(driver_id: str):
    """Vue d'ensemble « Ma caisse » : jour, semaine, dépenses, net estimé, solde."""
    _check_driver(driver_id)
    summary = get_service().financial_summary(driver_id)
    if summary is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return summary


# ------------------------------------------------------------------ dépenses


@router.get("/driver/{driver_id}/expenses")
def list_expenses(
    driver_id: str,
    category: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    _check_driver(driver_id)
    if category is not None and category not in EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Catégorie invalide (valeurs : {' | '.join(EXPENSE_CATEGORIES)})",
        )
    expenses = get_service().list_expenses(driver_id, category, date_from, date_to)
    if expenses is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return {
        "driver": _driver_info(driver_id),
        "category_labels": EXPENSE_CATEGORY_LABELS,
        "count": len(expenses),
        "total": sum(e["amount"] for e in expenses),
        "expenses": expenses,
    }


@router.post("/driver/{driver_id}/expenses", status_code=201)
def add_expense(driver_id: str, req: ExpenseRequest):
    _check_driver(driver_id)
    if req.category not in EXPENSE_CATEGORIES:
        raise HTTPException(
            status_code=422,
            detail=f"Catégorie invalide (valeurs : {' | '.join(EXPENSE_CATEGORIES)})",
        )
    expense = DriverExpense(
        driver_id=driver_id,
        expense_date=req.expense_date or date.today(),
        category=req.category,
        amount=req.amount,
        currency="XOF",
        description=req.description.strip(),
        receipt_reference=req.receipt_reference,
    )
    created = get_service().add_expense(expense)
    if created is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return created


@router.delete("/driver/{driver_id}/expenses/{expense_id}", status_code=204)
def delete_expense(driver_id: str, expense_id: int):
    _check_driver(driver_id)
    deleted = get_service().delete_expense(driver_id, expense_id)
    if deleted is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    if not deleted:
        raise HTTPException(status_code=404, detail="Dépense inconnue")
    return None


# ------------------------------------------------------------------ synthèse fiscale


@router.get("/driver/{driver_id}/tax-summary")
def tax_summary(
    driver_id: str,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Synthèse fiscale du conducteur par règle (période par défaut : 7 jours)."""
    _check_driver(driver_id)
    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=DEFAULT_TAX_PERIOD_DAYS - 1)
    if date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from doit précéder date_to")
    summary = get_service().tax_summary(driver_id, date_from, date_to)
    if summary is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return summary


# ------------------------------------------------------------------ clôtures journalières


@router.get("/driver/{driver_id}/daily-closures")
def list_closures(driver_id: str):
    _check_driver(driver_id)
    closures = get_service().list_closures(driver_id)
    if closures is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    return {
        "driver": _driver_info(driver_id),
        "count": len(closures),
        "closures": closures,
    }


@router.post("/driver/{driver_id}/daily-closures")
def close_day(driver_id: str, req: ClosureRequest):
    """Clôture la journée (idempotent : une seule clôture par conducteur et par date)."""
    _check_driver(driver_id)
    closure_date = req.closure_date or date.today()
    result = get_service().close_day(driver_id, closure_date)
    if result is None:
        raise HTTPException(status_code=503, detail="Module financier indisponible")
    closure, created = result
    payload = _jsonable(dict(closure))
    if created:
        return JSONResponse(status_code=201, content=payload)
    payload["already_closed"] = True
    payload["message"] = "Journée déjà clôturée. Aucune double clôture créée"
    return JSONResponse(status_code=200, content=payload)


def _jsonable(payload):
    """Conversion récursive date/datetime → ISO (JSONResponse ne le fait pas)."""
    if isinstance(payload, dict):
        return {k: _jsonable(v) for k, v in payload.items()}
    if isinstance(payload, list):
        return [_jsonable(v) for v in payload]
    if isinstance(payload, (datetime, date)):
        return payload.isoformat()
    return payload
