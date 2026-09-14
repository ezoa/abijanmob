"""API AbidjanMob — prototype de démonstration (jury AIMD, sept. 2026).

Paiements SIMULÉS (mock) : aucun argent réel, aucun appel PSP externe.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from routing_engine import CORPUS_PATH, MODES, get_network

app = FastAPI(title="AbidjanMob API — prototype de démo", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

net = get_network()

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
    ("07:05", 400, "wave"), ("07:12", 400, "orange"), ("07:19", 300, "wave"),
    ("07:26", 400, "wave"), ("07:41", 400, "mtn"), ("07:55", 300, "orange"),
    ("08:03", 400, "wave"), ("08:17", 400, "moov"), ("08:31", 300, "wave"),
    ("08:44", 400, "orange"), ("08:58", 400, "wave"), ("09:13", 300, "mtn"),
]
live_receipts: list[dict] = []


class PlanRequest(BaseModel):
    from_poi: str
    to_poi: str


class PaymentRequest(BaseModel):
    line_name: str
    mode: str
    fare: int
    provider: str
    driver_id: str = "drv_001"


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "abidjanmob-demo", "time": datetime.now().isoformat(timespec="seconds")}


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
    try:
        return net.plan(req.from_poi, req.to_poi)
    except KeyError:
        raise HTTPException(status_code=404, detail="POI inconnu")


@app.post("/api/payments")
def pay(req: PaymentRequest):
    if req.provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="PSP inconnu")
    if req.driver_id not in net.drivers:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")
    ticket = {
        "ticket_id": f"ABJ-{uuid.uuid4().hex[:6].upper()}",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "time_hm": datetime.now().strftime("%H:%M"),
        "line_name": req.line_name,
        "mode": req.mode,
        "fare": req.fare,
        "provider": PROVIDERS[req.provider],
        "driver_id": req.driver_id,
        "status": "PAYÉ (simulation)",
    }
    live_receipts.append(ticket)
    return ticket


@app.get("/api/driver/{driver_id}/receipts")
def receipts(driver_id: str):
    if driver_id not in net.drivers:
        raise HTTPException(status_code=404, detail="Conducteur inconnu")
    d = net.drivers[driver_id]
    seeded = [
        {"time_hm": hm, "fare": fare, "provider": PROVIDERS[p], "line_name": driver_line["name"], "mode": driver_line["mode"]}
        for hm, fare, p in SEED_RECEIPTS
    ]
    live = [
        {"time_hm": r["time_hm"], "fare": r["fare"], "provider": r["provider"], "line_name": r["line_name"], "mode": r["mode"]}
        for r in live_receipts
        if r["driver_id"] == driver_id
    ]
    all_receipts = live + seeded
    total = sum(r["fare"] for r in all_receipts)
    by_provider: dict[str, int] = {}
    for r in all_receipts:
        by_provider[r["provider"]] = by_provider.get(r["provider"], 0) + r["fare"]
    return {
        "driver": {"id": d["id"], "name": d["name"], "vehicle": d["vehicle"], "line": driver_line["name"]},
        "date": datetime.now().strftime("%d/%m/%Y"),
        "count": len(all_receipts),
        "total": total,
        "by_provider": by_provider,
        "no_change_given": total,
        "receipts": all_receipts,
    }
