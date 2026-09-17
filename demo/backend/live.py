"""Suivi en direct des véhicules (prototype) — simulation déterministe sur l'horloge.

Pas de thread : chaque position est une fonction pure du temps (époque fixe), donc
continue et robuste aux redémarrages. Le temps est accéléré (SIM_FACTOR) pour que le
mouvement soit visible pendant la démonstration — mention affichée à l'écran.

Modèle : une petite flotte par ligne informelle (2–3 véhicules espacés régulièrement,
cohérent avec la fréquence annoncée du corpus). Les conducteurs du corpus sont rattachés
au véhicule n°0 de leur ligne (leur « position partagée »).
"""

from __future__ import annotations

from datetime import datetime

SIM_FACTOR = 4  # accélération temporelle (démo)
TERMINAL_WAIT_MIN = 2.0  # pause à chaque terminus, en minutes simulées
FLEET_MIN, FLEET_MAX = 2, 3
EPOCH = datetime(2026, 9, 14, 6, 0, 0)  # époque fixe => trajectoires continues


class LiveTracker:
    def __init__(self, network):
        self.net = network
        self.fleet: dict[str, list[float]] = {}  # line_id -> décalages de phase (min)
        self.line_driver: dict[str, dict] = {}  # line_id -> conducteur (véhicule n°0)
        for d in network.drivers.values():
            self.line_driver[d["line_id"]] = d
        for ln in network.lines.values():
            if ln["mode"] in ("sotra", "bateau", "taxi", "taxi_communal"):
                continue  # suivi en direct : gbakas et woros (prototype)
            total = ln["_cum_min"][-1]
            cycle = 2 * (total + TERMINAL_WAIT_MIN)
            count = max(FLEET_MIN, min(FLEET_MAX, round(cycle / (2 * ln["headway_min"]))))
            self.fleet[ln["id"]] = [i * cycle / count for i in range(count)]

    # ------------------------------------------------------------------ interne

    def _phase(self, line_id: str, offset_min: float):
        """(forward, dist_min, cycle) — sens et avancement depuis l'arrêt 0."""
        cum = self.net.lines[line_id]["_cum_min"]
        total = cum[-1]
        cycle = 2 * (total + TERMINAL_WAIT_MIN)
        elapsed = (datetime.now() - EPOCH).total_seconds() / 60.0 * SIM_FACTOR
        t = (elapsed - offset_min) % cycle
        if t <= total:
            return True, t, cycle
        if t <= total + TERMINAL_WAIT_MIN:
            return True, total, cycle
        if t <= 2 * total + TERMINAL_WAIT_MIN:
            return False, 2 * total + TERMINAL_WAIT_MIN - t, cycle
        return False, 0.0, cycle

    def _position_on(self, line_id: str, dist: float):
        cum = self.net.lines[line_id]["_cum_min"]
        stops = self.net.lines[line_id]["stops"]
        i = 0
        while i < len(stops) - 2 and dist > cum[i + 1]:
            i += 1
        seg = cum[i + 1] - cum[i]
        f = 0.0 if seg <= 0 else min(1.0, max(0.0, (dist - cum[i]) / seg))
        a, b = self.net.stops[stops[i]], self.net.stops[stops[i + 1]]
        return a["lat"] + (b["lat"] - a["lat"]) * f, a["lon"] + (b["lon"] - a["lon"]) * f

    def _vehicle_state(self, line_id: str, offset: float, index: int):
        ln = self.net.lines[line_id]
        forward, dist, _ = self._phase(line_id, offset)
        lat, lon = self._position_on(line_id, dist)
        dest = ln["stops"][-1] if forward else ln["stops"][0]
        driver = self.line_driver.get(line_id) if index == 0 else None
        return {
            "vehicle_id": f"{line_id}#{index}",
            "line_id": ln["id"],
            "line_name": ln["name"],
            "mode": ln["mode"],
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "dir_label": f"vers {self.net.stops[dest]['name']}",
            "sim_factor": SIM_FACTOR,
            "driver_id": driver["id"] if driver else None,
            "driver_name": driver["name"] if driver else None,
        }

    def _eta_vehicle(self, line_id: str, k: int, offset: float):
        cum = self.net.lines[line_id]["_cum_min"]
        total = cum[-1]
        forward, dist, _ = self._phase(line_id, offset)
        if forward:
            if cum[k] >= dist:
                return cum[k] - dist
            return (total - dist) + TERMINAL_WAIT_MIN + (total - cum[k])
        if cum[k] <= dist:
            return dist - cum[k]
        return dist + TERMINAL_WAIT_MIN + cum[k]

    # ------------------------------------------------------------------ public

    def all_positions(self):
        out = []
        for line_id, offsets in self.fleet.items():
            for i, off in enumerate(offsets):
                out.append(self._vehicle_state(line_id, off, i))
        return out

    def driver_state(self, driver_id: str):
        d = self.net.drivers.get(driver_id)
        if d is None or d["line_id"] not in self.fleet:
            raise KeyError("conducteur inconnu")
        return self._vehicle_state(d["line_id"], self.fleet[d["line_id"]][0], 0)

    def line_eta(self, line_id: str, stop_id: str):
        if line_id not in self.fleet:
            raise KeyError("ligne sans suivi")
        ln = self.net.lines[line_id]
        if stop_id not in ln["stops"]:
            raise KeyError("arrêt inconnu")
        k = ln["stops"].index(stop_id)
        etas = sorted(self._eta_vehicle(line_id, k, off) for off in self.fleet[line_id])
        return {
            "line_id": line_id,
            "line_name": ln["name"],
            "stop_id": stop_id,
            "stop_name": self.net.stops[stop_id]["name"],
            "eta_min": round(etas[0], 1),
            "eta2_min": round(etas[1], 1),
            "sim_factor": SIM_FACTOR,
        }
