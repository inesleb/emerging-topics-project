"""Download the IEA Global EV Outlook 2026 car data (Global EV Data Explorer) to data/iea/iea_ev_cars.csv.

Uses the public API behind https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer
(licence: CC BY 4.0). Projections (Projection-CPS, Projection-STEPS) exist for Europe, not for the EU;
the EU only has historical data.

Run once:  python data/iea/fetch_iea.py
"""
from pathlib import Path

import pandas as pd
import requests

API = "https://api.iea.org/electric-vehicles"
OUT = Path(__file__).parent / "iea_ev_cars.csv"

if __name__ == "__main__":
    frames = []
    for region in ["Europe", "European Union"]:
        for category in ["Historical", "Projection-CPS", "Projection-STEPS"]:
            r = requests.get(API, params={"region": region, "mode": "Cars", "category": category}, timeout=60)
            r.raise_for_status()
            df = pd.DataFrame(r.json())
            print(f"{region:15} {category:17} {len(df):>4} rows")
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print("saved", OUT, out.shape)
