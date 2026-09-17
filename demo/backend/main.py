"""API AbidjanMob — prototype de démonstration (jury AIMD, sept. 2026).

Paiements SIMULÉS (mock) : aucun argent réel, aucun appel PSP externe.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import analytics
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from finance import build_payment_context, demo_day_contexts, get_service
from finance.api import router as finance_router
from live import LiveTracker
from pydantic import BaseModel, Field
from routing_engine import (  # noqa: F401 (CORPUS_PATH réexporté pour les tests)
    CORPUS_PATH,
    MODES,
    get_network,
)
from wallets import WalletError
from wallets import get_service as get_wallet_service
from wallets.api import router as wallets_router

app = FastAPI(title="AbidjanMob API — prototype de démo", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(finance_router, prefix="/api")
app.include_router(wallets_router, prefix="/api")

net = get_network()
tracker = LiveTracker(net)

PROVIDERS = {
    "wave": "Wave",
    "orange": "Orange Money",
    "mtn": "MTN MoMo",
    "moov": "Moov Money",
}

driver = net.drivers["drv_001"]
driver_line = net.lines[driver["line_id"]]

# Recettes du jour pré-remplies pour la démonstration (matinée du conducteur).
SEED_RECEIPTS = [
    ("07:05", 400, "wave"),
    ("07:12", 400, "orange"),
    ("07:19", 300, "wave"),
    ("07:26", 400, "wave"),
    ("07:41", 400, "mtn"),
    ("07:55", 300, "orange"),
    ("08:03", 400, "wave"),
    ("08:17", 400, "moov"),
    ("08:31", 300, "wave"),
    ("08:44", 400, "orange"),
    ("08:58", 400, "wave"),
    ("09:13", 300, "mtn"),
]
live_receipts: list[dict] = []


class PlanRequest(BaseModel):
    from_poi: str | None = None
    to_poi: str | None = None
    from_stop: str | None = None  # arrêt direct (ex. position actuelle géolocalisée)
    to_stop: str | None = None


class SplitRequest(BaseModel):
    provider: str
    amount: int = Field(gt=0)


class PaymentRequest(BaseModel):
    line_name: str
    mode: str
    fare: int
    provider: str | None = None  # opérateur unique (chemin historique)
    driver_id: str = "drv_001"
    line_id: str | None = None
    stop_id: str | None = None
    dest_stop_id: str | None = None  # arrêt de destination (documents financiers)
    splits: list[SplitRequest] | None = None  # répartition multi-portefeuilles


@app.on_event("startup")
def finance_startup() -> None:
    """Initialise le module financier (idempotent) : règles de démonstration,
    recettes du jour du conducteur (SEED_RECEIPTS → transactions complètes) et,
    avec PostgreSQL, backfill des documents/souches des 7 derniers jours seedés.
    Initialise aussi les portefeuilles du passager (soldes + historique démo)."""
    get_service().on_startup(
        demo_day_contexts=demo_day_contexts(driver, driver_line, SEED_RECEIPTS, PROVIDERS)
    )
    get_wallet_service().on_startup()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "abidjanmob-demo",
        "time": datetime.now().isoformat(timespec="seconds"),
        "analytics_db": analytics.db_url() is not None,
        "finance_store": "postgres" if analytics.db_url() else "memory",
    }


@app.get("/api/meta")
def meta():
    return {
        "modes": {k: v for k, v in MODES.items()},
        "providers": PROVIDERS,
        "disclaimer": net.meta["disclaimer"],
    }


@app.get("/api/network")
def network():
    return net.geojson()


@app.get("/api/pois")
def pois():
    return list(net.pois.values())


@app.post("/api/plan")
def plan(req: PlanRequest):
    if not (req.from_poi or req.from_stop) or not (req.to_poi or req.to_stop):
        raise HTTPException(status_code=422, detail="Départ et destination requis")
    try:
        return net.plan(req.from_poi, req.to_poi, from_stop=req.from_stop, to_stop=req.to_stop)
    except KeyError:
        raise HTTPException(status_code=404, detail="POI inconnu")


@app.post("/api/payments")
def pay(req: PaymentRequest):
    if req.driver_id not in net.drivers:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")
    # Répartition multi-portefeuilles (si fournie) : validation AVANT tout effet
    # de bord. Champ `provider` seul = comportement historique inchangé.
    splits: list[dict] | None = None
    if req.splits is not None:
        try:
            splits = get_wallet_service().prepare_split(req.fare, req.splits)
        except WalletError as e:
            raise HTTPException(status_code=400, detail=str(e))
        provider_label = " + ".join(PROVIDERS[s["provider"]] for s in splits)
        provider_key = splits[0]["provider"] if len(splits) == 1 else "multi"
    else:
        if not req.provider or req.provider not in PROVIDERS:
            raise HTTPException(status_code=400, detail="PSP inconnu")
        provider_label = PROVIDERS[req.provider]
        provider_key = req.provider
    now = datetime.now()
    ticket = {
        "ticket_id": f"ABJ-{uuid.uuid4().hex[:6].upper()}",
        "created_at": now.isoformat(timespec="seconds"),
        "time_hm": now.strftime("%H:%M"),
        "line_name": req.line_name,
        "mode": req.mode,
        "fare": req.fare,
        "provider": provider_label,
        "driver_id": req.driver_id,
        "status": "PAYÉ (simulation)",
    }
    wallet_extra: dict = {}
    if splits is not None:
        # Débit des portefeuilles simulés : refus métier (solde, cohérence) =
        # 400 ; panne d'infrastructure = best-effort, le paiement ne s'arrête pas.
        try:
            wallet_extra = (
                get_wallet_service().pay_split(ticket["ticket_id"], req.line_name, req.fare, splits)
                or {}
            )
        except WalletError as e:
            raise HTTPException(status_code=400, detail=str(e))
    live_receipts.append(ticket)
    # Chaque paiement devient une donnée de mobilité (best-effort, jamais bloquant).
    line = net.lines.get(req.line_id) if req.line_id else None
    stop = net.stops.get(req.stop_id) if req.stop_id else None
    dest_stop = net.stops.get(req.dest_stop_id) if req.dest_stop_id else None
    analytics.record_payment(ticket, now, line=line, stop=stop)
    # Module financier (best-effort lui aussi) : transaction comptable → facture/reçu
    # client + souche conducteur + calculs fiscaux + relevé. Ne lève jamais.
    ctx = build_payment_context(
        ticket=ticket,
        ts=now,
        provider_key=provider_key,
        provider_label=provider_label,
        driver=net.drivers[req.driver_id],
        line=line,
        stop=stop,
        dest_stop=dest_stop,
        line_id=req.line_id,
        stop_id=req.stop_id,
    )
    finance_info = get_service().process_payment(ctx) or {}
    # Contrat existant préservé : toutes les clés du billet sont inchangées,
    # les informations financières viennent en complément.
    return {**ticket, **wallet_extra, **finance_info}


@app.get("/api/drivers/live")
def drivers_live():
    return tracker.all_positions()


@app.get("/api/driver/{driver_id}/position")
def driver_position(driver_id: str):
    try:
        return tracker.driver_state(driver_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")


@app.get("/api/lines/{line_id}/eta")
def line_eta(line_id: str, stop_id: str):
    try:
        return tracker.line_eta(line_id, stop_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Ligne ou arrêt inconnu")


@app.get("/api/driver/{driver_id}/receipts")
def receipts(driver_id: str):
    if driver_id not in net.drivers:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")
    d = net.drivers[driver_id]
    seeded = [
        {
            "time_hm": hm,
            "fare": fare,
            "provider": PROVIDERS[p],
            "line_name": driver_line["name"],
            "mode": driver_line["mode"],
        }
        for hm, fare, p in SEED_RECEIPTS
    ]
    live = [
        {
            "time_hm": r["time_hm"],
            "fare": r["fare"],
            "provider": r["provider"],
            "line_name": r["line_name"],
            "mode": r["mode"],
        }
        for r in live_receipts
        if r["driver_id"] == driver_id
    ]
    all_receipts = live + seeded
    total = sum(r["fare"] for r in all_receipts)
    by_provider: dict[str, int] = {}
    for r in all_receipts:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + r["fare"]
    return {
        "driver": {
            "id": d["id"],
            "name": d["name"],
            "vehicle": d["vehicle"],
            "line": driver_line["name"],
        },
        "date": datetime.now().strftime("%d/%m/%Y"),
        "count": len(all_receipts),
        "total": total,
        "by_provider": by_provider,
        "no_change_given": total,
        "receipts": all_receipts,
    }
