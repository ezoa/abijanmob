"""Moteur d'itinéraires AbidjanMob — prototype corridor Cocody–Plateau–Adjamé.

Graphe léger : correspondances à pied entre arrêts proches, lignes bidirectionnelles
(gbaka / woro / SOTRA / bateau), attente estimée = fréquence / 2.
Dijkstra multi-passes (rapide / économique / formel / informel), puis comparaison taxi
et marche. Les données proviennent de data/corpus/network.json (indicatives).
"""

from __future__ import annotations

import heapq
import json
import math
from collections import defaultdict
from itertools import count
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parents[2] / "data" / "corpus" / "network.json"

MODES = {
    "gbaka": {"label": "Gbaka", "speed_kmh": 18.0, "color": "#E63946", "formal": False},
    "woro": {"label": "Woro-woro", "speed_kmh": 24.0, "color": "#F4A261", "formal": False},
    "sotra": {"label": "Bus SOTRA", "speed_kmh": 20.0, "color": "#2A9D8F", "formal": True},
    "bateau": {"label": "Bateau-bus", "speed_kmh": 14.0, "color": "#457B9D", "formal": True},
    "taxi": {"label": "Taxi", "speed_kmh": 26.0, "color": "#6D597A", "formal": False},
}
WALK_KMH = 4.5
DETOUR = 1.15
WALK_EDGE_MAX_M = 900
FARE_WEIGHT = 0.06
TAXI_BASE_FARE = 500
TAXI_FARE_PER_KM = 150
WALK_ONLY_MAX_M = 2500
CO2_TAXI_G_PER_KM = 130.0
CO2_TRANSIT_G_PER_KM = 35.0
MAX_TRANSIT_ITINERARIES = 4


def haversine_m(a: dict, b: dict) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def walk_min(m: float) -> float:
    return m / 1000.0 / WALK_KMH * 60.0


def _round(x: float, nd: int = 0) -> float:
    return round(x, nd)


class Network:
    def __init__(self, path: Path):
        data = json.loads(path.read_text(encoding="utf-8"))
        self.meta = data["meta"]
        self.stops = {s["id"]: s for s in data["stops"]}
        self.lines = {ln["id"]: ln for ln in data["lines"]}
        self.pois = {p["id"]: p for p in data["pois"]}
        self.drivers = {d["id"]: d for d in data["drivers"]}

        self.stop_lines: dict[str, list[tuple[dict, int]]] = defaultdict(list)
        for ln in self.lines.values():
            for idx, sid in enumerate(ln["stops"]):
                self.stop_lines[sid].append((ln, idx))
            speed = MODES[ln["mode"]]["speed_kmh"]
            cum = [0.0]
            dist = [0.0]
            for a, b in zip(ln["stops"], ln["stops"][1:]):
                d = haversine_m(self.stops[a], self.stops[b]) * DETOUR
                dist.append(d)
                cum.append(cum[-1] + d / 1000.0 / speed * 60.0)
            ln["_cum_min"] = cum
            ln["_cum_m"] = [sum(dist[: i + 1]) for i in range(len(dist))]

        self.walk_edges: dict[str, list[tuple[str, float, float]]] = defaultdict(list)
        ids = list(self.stops)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                d = haversine_m(self.stops[a], self.stops[b])
                if d <= WALK_EDGE_MAX_M:
                    m = walk_min(d)
                    self.walk_edges[a].append((b, d, m))
                    self.walk_edges[b].append((a, d, m))

    # ------------------------------------------------------------------ routage

    def _dijkstra(
        self,
        origin_stop: str,
        dest_stops: set[str],
        allowed_modes: set[str] | None,
        fare_weight: float,
    ) -> list[dict] | None:
        tick = count()
        # (priority, seq, time_min, stop, legs, fare, used_lines)
        start_leg = {
            "type": "walk",
            "from": origin_stop,
            "to": origin_stop,
            "min": 0.0,
            "m": 0.0,
        }
        heap = [(0.0, next(tick), 0.0, origin_stop, (start_leg,), 0, frozenset())]
        best: dict[str, float] = {}
        while heap:
            pri, _, t, stop, legs, fare, used = heapq.heappop(heap)
            if stop in dest_stops:
                return [dict(leg) for leg in legs[1:]]  # drop fictitious start leg
            if pri > best.get(stop, math.inf):
                continue
            best[stop] = pri
            for ln, idx in self.stop_lines[stop]:
                if ln["id"] in used:
                    continue
                if allowed_modes is not None and ln["mode"] not in allowed_modes:
                    continue
                wait = max(2.0, ln["headway_min"] / 2.0)
                for j in range(len(ln["stops"])):
                    if j == idx:
                        continue
                    ride = abs(ln["_cum_min"][j] - ln["_cum_min"][idx])
                    ride_m = abs(ln["_cum_m"][j] - ln["_cum_m"][idx])
                    arr = t + wait + ride
                    new_fare = fare + ln["fare"]
                    leg = {
                        "type": "ride",
                        "mode": ln["mode"],
                        "mode_label": MODES[ln["mode"]]["label"],
                        "color": MODES[ln["mode"]]["color"],
                        "line_id": ln["id"],
                        "line_name": ln["name"],
                        "from": ln["stops"][idx],
                        "to": ln["stops"][j],
                        "wait_min": _round(wait, 1),
                        "ride_min": _round(ride, 1),
                        "m": _round(ride_m),
                        "fare": ln["fare"],
                        "headway_min": ln["headway_min"],
                    }
                    heapq.heappush(
                        heap,
                        (
                            arr + fare_weight * new_fare,
                            next(tick),
                            arr,
                            ln["stops"][j],
                            legs + (leg,),
                            new_fare,
                            used | {ln["id"]},
                        ),
                    )
            for b, d, m in self.walk_edges[stop]:
                arr = t + m
                leg = {"type": "walk", "from": stop, "to": b, "min": _round(m, 1), "m": _round(d)}
                heapq.heappush(
                    heap, (arr + fare_weight * fare, next(tick), arr, b, legs + (leg,), fare, used)
                )
        return None

    # ------------------------------------------------------------- assemblage

    def _merge_walks(self, legs: list[dict]) -> list[dict]:
        out: list[dict] = []
        for leg in legs:
            if leg["type"] == "walk" and leg["min"] == 0 and leg["m"] == 0:
                continue
            if (
                leg["type"] == "walk"
                and out
                and out[-1]["type"] == "walk"
                and out[-1]["to"] == leg["from"]
            ):
                out[-1]["to"] = leg["to"]
                out[-1]["min"] = _round(out[-1]["min"] + leg["min"], 1)
                out[-1]["m"] = _round(out[-1]["m"] + leg["m"])
            else:
                out.append(leg)
        return out

    def _summarize(self, o_poi: dict, d_poi: dict, legs: list[dict]) -> dict:
        rides = [leg for leg in legs if leg["type"] == "ride"]
        walk_m = sum(leg["m"] for leg in legs if leg["type"] == "walk")
        total = sum(
            (leg["wait_min"] + leg["ride_min"]) if leg["type"] == "ride" else leg["min"]
            for leg in legs
        )
        fare = sum(leg["fare"] for leg in rides)
        transit_km = sum(leg["m"] for leg in rides) / 1000.0
        names = " · ".join(leg["line_name"] for leg in rides) or "À pied"
        return {
            "legs": legs,
            "total_min": _round(total, 1),
            "fare": fare,
            "walk_m": _round(walk_m),
            "transfers": max(0, len(rides) - 1),
            "co2_saved_g": _round(
                max(0.0, transit_km * (CO2_TAXI_G_PER_KM - CO2_TRANSIT_G_PER_KM))
            ),
            "summary": f"{names} — {_round(total)} min · {fare} FCFA",
        }

    def _taxi_itinerary(self, o_stop: dict, d_stop: dict) -> dict:
        dist_m = haversine_m(o_stop, d_stop) * DETOUR
        dur = dist_m / 1000.0 / MODES["taxi"]["speed_kmh"] * 60.0
        fare = int(_round(TAXI_BASE_FARE + TAXI_FARE_PER_KM * dist_m / 1000.0) / 50) * 50
        leg = {
            "type": "ride",
            "mode": "taxi",
            "mode_label": MODES["taxi"]["label"],
            "color": MODES["taxi"]["color"],
            "line_id": "taxi",
            "line_name": "Taxi individuel (tarif estimé, marchandage)",
            "from": o_stop["id"],
            "to": d_stop["id"],
            "wait_min": 3.0,
            "ride_min": _round(dur, 1),
            "m": _round(dist_m),
            "fare": fare,
            "headway_min": 0,
        }
        return {
            "legs": [leg],
            "total_min": _round(3.0 + dur, 1),
            "fare": fare,
            "walk_m": 0,
            "transfers": 0,
            "co2_saved_g": 0,
            "summary": f"Taxi — {_round(3.0 + dur)} min · ~{fare} FCFA",
        }

    def _walk_itinerary(self, o_stop: dict, d_stop: dict) -> dict | None:
        dist_m = haversine_m(o_stop, d_stop) * DETOUR
        if dist_m > WALK_ONLY_MAX_M:
            return None
        leg = {
            "type": "walk",
            "from": o_stop["id"],
            "to": d_stop["id"],
            "min": _round(walk_min(dist_m), 1),
            "m": _round(dist_m),
        }
        return {
            "legs": [leg],
            "total_min": _round(walk_min(dist_m), 1),
            "fare": 0,
            "walk_m": _round(dist_m),
            "transfers": 0,
            "co2_saved_g": _round(dist_m / 1000.0 * CO2_TAXI_G_PER_KM),
            "summary": f"À pied — {_round(walk_min(dist_m))} min · 0 FCFA",
        }

    # ------------------------------------------------------------------ public

    def plan(self, from_poi: str, to_poi: str) -> dict:
        if from_poi not in self.pois or to_poi not in self.pois:
            raise KeyError("POI inconnu")
        o_poi, d_poi = self.pois[from_poi], self.pois[to_poi]
        o_stop_id, d_stop_id = o_poi["stop_id"], d_poi["stop_id"]
        o_stop, d_stop = self.stops[o_stop_id], self.stops[d_stop_id]

        runs = [
            ("rapide", None, 0.0),
            ("economique", None, FARE_WEIGHT),
            ("formel", {"sotra", "bateau"}, 0.0),
            ("informel", {"gbaka", "woro"}, 0.0),
        ]
        candidates: list[dict] = []
        seen: set[tuple] = set()
        for label, modes, fw in runs:
            legs = self._dijkstra(o_stop_id, {d_stop_id}, modes, fw)
            if not legs:
                continue
            it = self._summarize(o_poi, d_poi, self._merge_walks(legs))
            sig = tuple(leg.get("line_id") for leg in it["legs"] if leg["type"] == "ride")
            if sig in seen:
                continue
            seen.add(sig)
            it["kind"] = label
            candidates.append(it)

        # Une option par réseau (formel / informel / mixte) : un filtre de dominance
        # stricte masquerait le réseau informel, cœur de la proposition AbidjanMob.
        kept = sorted(candidates, key=lambda x: x["total_min"])[:MAX_TRANSIT_ITINERARIES]

        if kept:
            kept[0]["tag"] = "Le plus rapide"
            cheapest = min(kept, key=lambda x: x["fare"])
            if cheapest is not kept[0]:
                cheapest["tag"] = "Le moins cher"
        for it in kept:
            rides = [leg for leg in it["legs"] if leg["type"] == "ride"]
            if rides and all(MODES[leg["mode"]]["formal"] for leg in rides):
                it.setdefault("tag", "Réseau formel")
            elif rides and all(not MODES[leg["mode"]]["formal"] for leg in rides):
                it.setdefault("tag", "Réseau informel")

        extras = [self._taxi_itinerary(o_stop, d_stop)]
        walk = self._walk_itinerary(o_stop, d_stop)
        if walk:
            walk["tag"] = "À pied"
            extras.append(walk)

        out = kept + extras
        for i, it in enumerate(out):
            it["id"] = f"it_{i}"
        return {
            "from": {**o_poi, "stop": o_stop},
            "to": {**d_poi, "stop": d_stop},
            "itineraries": out,
        }

    def geojson(self) -> dict:
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": {
                    "id": s["id"],
                    "name": s["name"],
                    "commune": s["commune"],
                    "kind": s["kind"],
                },
            }
            for s in self.stops.values()
        ]
        lines = [
            {
                "id": ln["id"],
                "name": ln["name"],
                "mode": ln["mode"],
                "mode_label": MODES[ln["mode"]]["label"],
                "color": MODES[ln["mode"]]["color"],
                "fare": ln["fare"],
                "headway_min": ln["headway_min"],
                "stops": ln["stops"],
                "coords": [[self.stops[sid]["lat"], self.stops[sid]["lon"]] for sid in ln["stops"]],
            }
            for ln in self.lines.values()
        ]
        return {"stops": {"type": "FeatureCollection", "features": features}, "lines": lines}


_NETWORK: Network | None = None


def get_network() -> Network:
    global _NETWORK
    if _NETWORK is None:
        _NETWORK = Network(CORPUS_PATH)
    return _NETWORK
