"""Build data/eea/eea_summary.csv from the EEA new-car CO2 monitoring data.

The raw EEA data has up to ~30 million rows per year, so instead of downloading it we
aggregate on the EEA's public SQL service (DISCODATA) and only download the result:
one row per year x member state x fuel type x fuel mode.

Sources (DISCODATA, database CO2Emission, schema `latest`):
  * 2010-2021: table co2cars, Status = 'F' (final; the table also holds provisional rows)
  * 2022, 2023, 2024: tables co2cars_2022Fv26, co2cars_2023Fv28, co2cars_2024Fv30 (final)
  * 2025: table co2cars_2025Pv31 (provisional, the only version published so far)

Run once:  python data/eea/fetch_eea.py
"""
import time
from pathlib import Path

import pandas as pd
import requests

URL = "https://discodata.eea.europa.eu/sql"
OUT = Path(__file__).parent / "eea_summary.csv"

SOURCES = {y: ("co2cars", "F") for y in range(2010, 2022)}
SOURCES.update({2022: ("co2cars_2022Fv26", None), 2023: ("co2cars_2023Fv28", None),
                2024: ("co2cars_2024Fv30", None), 2025: ("co2cars_2025Pv31", None)})

# Registration-weighted sums; each average is later sum_x / n_x (only rows where x is known).
# NEDC CO2 is in column "E (g/km)" up to 2016 and "Enedc (g/km)" from 2017.
# R is cast to FLOAT because R * mass overflows the integer type on the server.
NEDC = "COALESCE(c.[Enedc (g/km)], c.[E (g/km)])"
WLTP = "c.[Ewltp (g/km)]"


def wsum(name, expr, cond=None):
    cond = cond or f"{expr} IS NOT NULL"
    return (f"SUM(CASE WHEN {cond} THEN CAST(c.R AS FLOAT) ELSE 0 END) AS n_{name}, "
            f"SUM(CASE WHEN {cond} THEN CAST(c.R AS FLOAT) * {expr} ELSE 0 END) AS sum_{name}")


both = f"{WLTP} IS NOT NULL AND {NEDC} IS NOT NULL"
QUERY = f"""
SELECT c.Year AS year, c.MS AS country, c.Ft AS ft, c.Fm AS fm, SUM(c.R) AS regs,
       {wsum("wltp", WLTP)}, {wsum("nedc", NEDC)},
       {wsum("wltp_both", WLTP, both)}, {wsum("nedc_both", NEDC, both)},
       {wsum("mass", "c.[M (kg)]")}, {wsum("power", "c.[Ep (KW)]")}
FROM [CO2Emission].[latest].[{{table}}] c
WHERE c.Year = {{year}} {{status}}
GROUP BY c.Year, c.MS, c.Ft, c.Fm
"""


def run(query, page_size=5000):
    rows, page = [], 1
    while True:
        for attempt in range(3):
            r = requests.post(URL, data={"query": query, "p": page, "nrOfHits": page_size}, timeout=900)
            body = r.json()
            if "results" in body:
                break
            print("  retrying:", body)
            time.sleep(10)
        else:
            raise RuntimeError(body)
        rows += body["results"]
        if len(body["results"]) < page_size:
            return rows
        page += 1


if __name__ == "__main__":
    frames = []
    for year, (table, status) in SOURCES.items():
        t0 = time.time()
        q = QUERY.format(table=table, year=year, status=f"AND c.Status = '{status}'" if status else "")
        df = pd.DataFrame(run(q))
        if df.empty:
            raise RuntimeError(f"{year}: query returned no rows")
        print(f"{year}: {len(df):>5} groups, {df.regs.sum():>12,.0f} registrations ({time.time() - t0:.0f}s)")
        frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    OUT.parent.mkdir(exist_ok=True)
    out.to_csv(OUT, index=False)
    print("saved", OUT, out.shape)
