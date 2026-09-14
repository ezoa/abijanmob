#!/usr/bin/env python3
"""Met en cache les tuiles OpenStreetMap pour une démo hors-ligne.

Usage prototype (volume léger, une seule fois) — fond de carte © OpenStreetMap contributors.
"""
import math
import os
import sys
import time
import urllib.request

BBOX_CITY = (5.20, -4.10, 5.50, -3.85)  # lat_min, lon_min, lat_max, lon_max
BBOX_CORRIDOR = (5.28, -4.05, 5.43, -3.93)
ZOOMS_CITY = (10, 11, 12, 13, 14)
ZOOM_CORRIDOR = 15
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "tiles")
UA = "AbidjanMobDemo/0.1 (prototype educatif AIMD 2026)"


def deg2num(lat, lon, z):
    lat_r = math.radians(lat)
    n = 2.0**z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_r) + 1 / math.cos(lat_r)) / math.pi) / 2.0 * n)
    return x, y


def tiles_for(bbox, z):
    x0, y1 = deg2num(bbox[0], bbox[1], z)
    x1, y0 = deg2num(bbox[2], bbox[3], z)
    for x in range(min(x0, x1), max(x0, x1) + 1):
        for y in range(min(y0, y1), max(y0, y1) + 1):
            yield z, x, y


def fetch(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r, open(path, "wb") as f:
        f.write(r.read())


def main():
    jobs = [t for z in ZOOMS_CITY for t in tiles_for(BBOX_CITY, z)]
    jobs += list(tiles_for(BBOX_CORRIDOR, ZOOM_CORRIDOR))
    print(f"{len(jobs)} tuiles à récupérer…", flush=True)
    ok = skip = err = 0
    for i, (z, x, y) in enumerate(jobs, 1):
        d = os.path.join(OUT, str(z), str(x))
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{y}.png")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            skip += 1
            continue
        try:
            fetch(f"https://tile.openstreetmap.org/{z}/{x}/{y}.png", p)
            ok += 1
        except Exception as e:  # noqa: BLE001
            err += 1
            print(f"  echec {z}/{x}/{y}: {e}", file=sys.stderr, flush=True)
        if i % 50 == 0:
            print(f"  … {i}/{len(jobs)} ({ok} ok, {skip} deja la, {err} erreurs)", flush=True)
        time.sleep(0.15)
    print(f"Termine : {ok} recuperées, {skip} deja presentes, {err} erreurs.", flush=True)


if __name__ == "__main__":
    main()
