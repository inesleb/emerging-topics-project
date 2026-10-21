# Project data: sources, extraction and checks

Data for the project *How far is the EU new-car market from the CO₂ trajectory implied by IEA scenarios and EU standards to 2035, and how much of the gap comes from electrification versus more efficient combustion-engine cars?*

Everything here was retrieved on **21 October 2026**. The folder is small (about 2.3 MB) and safe to commit.

| File | What it is | Source |
|---|---|---|
| `eea/eea_summary.csv` | New cars registered 2010–2025: registrations and registration-weighted CO₂, mass and power, by year × country × fuel type × fuel mode | EEA CO₂ monitoring data (Regulation 2019/631) |
| `eea/fetch_eea.py` | Script that rebuilds `eea_summary.csv` (about 1 minute) | |
| `iea/iea_ev_cars.csv` | Electric car sales, stock and sales shares: Europe and EU history, and Europe projections to 2035 for both scenarios | IEA Global EV Outlook 2026, Global EV Data Explorer |
| `iea/fetch_iea.py` | Script that rebuilds `iea_ev_cars.csv` (a few seconds) | |
| `iea/iea_report_figures.csv` | Numbers taken by hand from the report text (EU 2030/2035 shares, carmaker targets, 11 g/km), with page numbers and the report's wording ("over", "nearly") in `qualifier` | IEA Global EV Outlook 2026 report |
| `iea/GEVO2026 Policy Explorer.pdf` | IEA list of EV policies by country, used for the EU CO₂ standards | IEA Global EV Outlook 2026, Policy Explorer |
| `eu/eu_targets.csv` | EU fleet-wide CO₂ targets for new cars (g/km, WLTP), in force and proposed | Regulation 2019/631; EEA; IEA GEVO 2026 |

To rebuild from the repository root: `python data/eea/fetch_eea.py` and `python data/iea/fetch_iea.py`. Both need `pandas` and `requests` and an internet connection. Running the EEA script on 21 October 2026 reproduced the stored file exactly (yearly totals identical).

---

## 1. EEA: CO₂ emissions from new passenger cars

### Why we did not download the files

The raw EEA data has one row per vehicle variant and country, and close to one row per car in recent years: about **30 million rows a year for 2018–2019**. That's tens of GB for 2010–2025. The EEA publishes the same data on **DISCODATA**, a public SQL service (`https://discodata.eea.europa.eu/sql`, database `CO2Emission`, schema `latest`), so we ran the aggregation on the EEA's server and downloaded only the result (about 4,000 rows).

### Which tables and versions

The EEA publishes a provisional (`P`) version and later a final (`F`) version of each year. Mixing them would count every car twice, so exactly one version is used per year:

| Years | DISCODATA table | Version |
|---|---|---|
| 2010–2021 | `co2cars` (combined table, which holds both versions) | filtered on `Status = 'F'` |
| 2022 | `co2cars_2022Fv26` | final |
| 2023 | `co2cars_2023Fv28` | final |
| 2024 | `co2cars_2024Fv30` | final |
| 2025 | `co2cars_2025Pv31` | **provisional** (no final version published yet) |

### What the query does

For each year, rows are grouped by country (`MS`), fuel type (`Ft`) and fuel mode (`Fm`), and summed with the registration count `R` as weight. For each variable *x* the file has two columns:

- `n_x`: registrations for which *x* is known
- `sum_x`: Σ R·x over those registrations

The weighted average is `sum_x / n_x`, and you can add up `n_x` and `sum_x` across rows before dividing (for example to get EU-27 totals).

| Column | Meaning |
|---|---|
| `year`, `country`, `ft`, `fm` | Registration year, member state (ISO-2), fuel type, fuel mode |
| `regs` | Number of new registrations |
| `n_wltp`, `sum_wltp` | CO₂ on the WLTP test (g/km). Available from 2019 (partly 2017–2018) |
| `n_nedc`, `sum_nedc` | CO₂ on the older NEDC test (g/km). Up to 2016 the EEA stores it in column `E (g/km)`, from 2017 in `Enedc (g/km)`; the query merges the two |
| `n_wltp_both`, `sum_wltp_both`, `n_nedc_both`, `sum_nedc_both` | The same two CO₂ values, restricted to cars that report **both**. Used to compute the NEDC→WLTP ratio (`sum_wltp_both / sum_nedc_both`) |
| `n_mass`, `sum_mass` | Mass in running order (kg) |
| `n_power`, `sum_power` | Engine power (kW). Not reported before 2011 |

### Things to know when using the file

- **Country scope.** The file contains EU members plus the UK (2010–2020), Iceland (2018–) and Norway (2019–). The EU targets apply to the EU only, so **filter to EU-27**. Croatia is missing for 2010–2013, about 0.3% of the market.
- **Fuel-type spelling is inconsistent** (`PETROL`, `Petrol`, `petrol`; `petrol-electric` before 2017, `petrol/electric` after). Lower-case and strip `ft` first, then add up rows that share the same key. A handful of rows (a few thousand cars in total) have an empty fuel type or country.
- **Suggested powertrain classification** (applied after lower-casing):
  - `electric` or `hydrogen` → **zero-emission** (hydrogen is about 5,000 cars over all years)
  - `ft` contains `electric` (`petrol/electric`, `diesel-electric`, …) → **plug-in hybrid**
  - `fm == 'H'` → **regular hybrid**, not plug-in. This code is only used **from 2019**; before that, regular hybrids are counted inside petrol/diesel.
  - everything else → **combustion** (petrol, diesel, LPG, natural gas, E85, …)
- **Early plug-in hybrids (2013–2014)** coded `petrol-electric` average 70 g/km, which suggests some regular hybrids are mixed in. These are below 0.5% of sales.
- **Official test values**, as on the certificates of conformity. Eco-innovation savings and super-credits are not included, so manufacturers' compliance figures differ slightly. Plug-in hybrid values in particular are known to be far below real-world use.
- **2025 is provisional** and may still be revised.

### EU-27 results (computed from the file)

| Year | Registrations (M) | NEDC g/km | WLTP g/km | Electric share (zero-emission + plug-in) |
|---|---|---|---|---|
| 2010 | 11.1 | 139.6 | – | 0.0% |
| 2015 | 11.2 | 119.2 | – | 1.2% |
| 2019 | 13.0 | 122.1 | 147.2 | 3.0% |
| 2020 | 10.0 | 108.0 | 130.8 | 10.7% |
| 2021 | 9.7 | – | 115.8 | 18.0% |
| 2022 | 9.3 | – | 110.0 | 21.7% |
| 2023 | 10.6 | – | 107.7 | 22.5% |
| 2024 | 10.6 | – | 108.0 | 20.9% |
| 2025 | 10.6 | – | 98.5 | 27.5% |

For cars that report both tests (2019–2020), **WLTP ≈ 1.21 × NEDC**. Use this ratio to put 2010–2018 on the WLTP scale.

---

## 2. IEA: Global EV Outlook 2026

### Data explorer (`iea/iea_ev_cars.csv`)

Downloaded from the public API behind the [Global EV Data Explorer](https://www.iea.org/data-and-statistics/data-tools/global-ev-data-explorer) (`https://api.iea.org/electric-vehicles`, `mode=Cars`) for the regions *Europe* and *European Union* and the three categories *Historical*, *Projection-CPS* and *Projection-STEPS*. Licence: **CC BY 4.0**, cite as "IEA (2026), Global EV Outlook 2026".

Columns: `region, category, parameter, mode, powertrain, year, unit, value`. Parameters include `EV sales share` (%), `EV sales` and `EV stock` (vehicles) by powertrain (BEV, PHEV, FCEV, and EV = their total).

What it does **not** contain:

- **No EU projections.** Only Europe has projections; the EU has history only (2010–2025).
- **No 2030 values.** Projections are given for **2035 only**. Europe's electric share in 2035 is 89% (Current Policies) and 85% (Stated Policies).

### The report: scenario definitions and EU figures

The [full report](https://www.iea.org/reports/global-ev-outlook-2026) (PDF, 295 pages, not stored here because of its size) gives what the data explorer lacks:

- **Scenario definitions** (p. 190):
  - **Current Policies (CPS)**: only policies already in force.
  - **Stated Policies (STEPS)**: also includes proposals that have been put forward but not yet adopted.

  For the EU this means CPS keeps the current 100%-zero-emission-in-2035 rule, while STEPS includes the **December 2025 Automotive Package**, which relaxes 2035 to −90% (p. 200). That is why Europe's electric share is *higher* in CPS than in STEPS.
- **EU electric light-duty vehicle share** (cars and vans together, p. 200): about 25% in 2025 → **over 90% in 2035 in STEPS** (battery-electric above 85%) and **nearly 100% in CPS**.
- **EU electric-car demand in 2030 under STEPS: about 7 million** (p. 233). Divided by about 10.6 million EU-27 registrations (EEA 2025), this gives **about 65% electric in 2030**. This share is our own calculation, not an IEA figure.
- **Carmaker targets for Europe**: 55–90% of car sales electric in 2030, about 65% to over 95% in 2035 (p. 232).
- **2035 proposal**: up to **11 g CO₂/km** for cars (−90% vs the 2021 baseline), with the rest offset by EU low-carbon steel and e-fuel/biofuel credits (Box 9.2, p. 198).

### Policy Explorer (`iea/GEVO2026 Policy Explorer.pdf`)

The IEA's list of 739 EV policies by country, provided by the group. It doesn't contain projections. Its EU car entries confirm the CO₂ standards (−15% by 2025, −55% by 2030, −100% by 2035 vs 2021), the proposed −90% for 2035, and the averaging of 2025–2027 compliance over three years. The PDF still lists that averaging as a proposal, but it was adopted on 17 June 2025 as Regulation (EU) 2025/1214.

---

## 3. EU CO₂ targets (`eu/eu_targets.csv`)

Entered by hand. All values are fleet-wide g/km on the WLTP test.

| Years | Target | Status |
|---|---|---|
| 2025–2029 | 93.6 | in force; 2025–2027 compliance averaged over three years (Regulation (EU) 2025/1214) |
| 2030–2034 | 49.5 | in force |
| 2035 on | 0 | in force |
| 2035 on | 11.0 | proposal (December 2025 Automotive Package) |

The in-force values are confirmed by the [EEA indicator page](https://www.eea.europa.eu/en/analysis/indicators/co2-performance-of-new-passenger) and by the IEA Policy Explorer. The 11 g/km is confirmed by IEA GEVO 2026, Box 9.2. Both 93.6/0.85 and 49.5/0.45 give the same 2021 baseline of about 110 g/km. The EEA also gives the earlier 2020–2024 target of 95 g/km NEDC as about 115.1 g/km WLTP.

---

## 4. Checks

| Check | Compared with | Result |
|---|---|---|
| EU electric share by year (EEA) | IEA EU historical sales share (independent source) | Within 0.7 percentage points in every year 2017–2025 (2025: 27.5% vs 27.0%). Electric and plug-in car counts within a few %. Larger relative gaps before 2016, when the share was below 1.5%. |
| Fall in average WLTP CO₂, 2019→2023 | EEA indicator page: −28%, flat in 2024 (EU + Norway + Iceland) | Same scope from our file: **−27.2%**, and 2023→2024 flat (106.5 → 106.8 g/km) |
| NEDC→WLTP ratio | EEA's 95 g/km NEDC ≈ 115.1 g/km WLTP (1.21) | **1.21** from cars reporting both values in 2019–2020 |
| Completeness | Totals computed directly on the EEA server | Every year 2010–2025 present; 2025 = 10,833,597 registrations |
| Reproducibility | Rerunning both scripts on 21 October 2026 | Identical files (EEA yearly totals identical; only fuel-type capitalisation changes between runs) |
| Regulation (EU) 2023/851 | [European Parliament legislative observatory](https://oeil.europarl.europa.eu/oeil/en/document-summary?id=1741896), [IEA policy entry](https://www.iea.org/policies/28356-regulation-eu-2023851-on-strengthening-the-co2-emission-performance-standards-for-new-passenger-cars-and-new-light-commercial-vehicles) | Confirmed: adopted 19 April 2023, amends 2019/631, cars −55% from 2030 and −100% from 2035 vs 2021 |
| 2025–2027 averaging | [EUR-Lex, Regulation (EU) 2025/1214](https://eur-lex.europa.eu/eli/reg/2025/1214/oj/eng) | Confirmed: adopted 17 June 2025, compliance for 2025, 2026 and 2027 calculated over the three years together |

## 5. Still open

- There is **no Current Policies 2030 value** anywhere; any 2030 path for that scenario is an assumption.
- The IEA's 2035 EU figures are rounded in the text ("over 90%", "nearly 100%").
