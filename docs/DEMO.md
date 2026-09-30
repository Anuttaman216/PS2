# SIH demo script: FreightSaarthi (about 8 minutes)

## Before you start (5 minutes before judging)

```bash
pip install -r requirements.txt
python tests/test_api.py      # expect 11/11 passed (checks all 35 endpoints)
python serve.py               # http://localhost:8000
```
- Open **http://localhost:8000** in full-screen Chrome, with zoom at 100%.
- Keep a second tab on **http://localhost:8000/docs**.
- To reset to a clean demo state, stop the server, delete `outputs/freightsaarthi.db`, and start it again. The four demo programmes are re-seeded automatically.
- If the top bar shows UPLOADED DATA, open **Data Hub → ↺ Restore synthetic demo**, which takes about 1 second.
- Internet is **not** required. Charts are served locally, and only the Google Fonts fall back to system fonts when offline.
- Have `freightsaarthi_market_template.csv` downloaded in advance (Data Hub → ①), ready to drag in during step 6.

## The walk-through

| # | Where | What to show | What to say |
|---|---|---|---|
| 1 | Landing `/` | Let the preloader run. Point at the ships sailing the real lanes into Paradip, Dhamra, Vizag and Haldia, and hover a port to show its draft. | "This is SAIL's coal trade: 5 origins, 7 East Coast ports, 4 ship classes." |
| 2 | Scroll the landing | The sticky story (volatility, then drafts from 8 m to 19.5 m, then 268 → 54 fixtures). "Will it fit?": click Haldia, then Gangavaram. | "The port decides the ship. Here is the physics, live." |
| 3 | Landing → Modules | Every card shows its own endpoint's latency. Click **Plan a Charter**. | "Every card is a live API endpoint." |
| 4 | `/app#/plan` | Pilot preset. Show the recommendation, mix bar, ladder and timing chart. Type broker quote **15.5** to X-ray it. Click **US → Haldia (avoid Suez)** and point out the Handysize choice, the Cape re-route and the "cheaper alternative port" hint. Click **Save to ledger**. | "The server runs a stochastic LP with CVaR on 150 scenarios in about 30 ms." |
| 5 | `#/ops` | Create a programme with **+ New programme** and click **Plan ▶**. Record a decision (Accepted, GM Shipping, actual rate). Open **Note ↗** for the printable charter note, then **Export CSV**. | "Every recommendation is logged with an input hash, a data version and the officer's decision. It is audit-ready for a PSU." |
| 6 | `#/data` | Drop the template CSV in. Show the validation report and the proxy-filled columns. Click **Run on uploaded data** and watch the live stages (about 35 s). The top bar switches to UPLOADED DATA. Then click **Restore synthetic demo**. | "Give us SAIL's real weekly history and the whole system retrains on it." |
| 7 | `#/risk` | Click the **Cyclone · Odisha** sample, then **Analyse & store**, and show the impacted lanes. | "News becomes a typed event, which is mapped to the SAIL lanes it hits." |
| 8 | `#/backtest` | Waterfall, placebo card, random-walk ablation, B3 control. | "It wins where there is signal and shows no fake edge where there isn't. We show both." |
| 9 | `#/compare` / `#/network` | Rank every origin into Paradip. | "This is freight-adjusted FOB break-even for procurement." |
| 10 | `/docs` | Swagger with 35 endpoints. | "It's a complete backend: REST, SQLite persistence, and a test suite." |

## Likely judge questions (short answers)

- **"Is the data real?"** No. It is synthetic and labelled as such everywhere, because Baltic indices are licensed. The Data Hub accepts real history today (step 6), and the pipeline re-splits into train, validation and test automatically.
- **"How accurate is the forecast?"** 3-13% better MAE than a random walk at 1-12 weeks, with calibrated 80% bands (79-85% coverage). It is significant mainly at 1-8 weeks. We do not overclaim, and the charter ladder limits how much is locked on any single week's signal.
- **"Where do the savings come from?"** Most of it is vessel choice (the port-draft physics). The rest comes from spot timing and the contract ladder, plus a large cut in bad-case cost (CVaR 19.8 → 17.7 $/t). The Paradip draft is an assumption to verify.
- **"Why not deep learning or reinforcement learning?"** There are only about 600 weekly points per series. An ensemble with conformal calibration is more robust and auditable. Foundation models (Chronos/TimesFM) plug in as an extra ensemble member, and RL was rejected for auditability.
- **"How does it help move from spot to multi-voyage contracts?"** The CVaR ladder locks COA and time-charter tranches when forecasts and risk justify it. The backtest shows spot fixtures falling from 268 to 54, with 73% of volume contracted.
- **"Does it fit PSU procurement rules?"** It outputs tender timing and specifications (vessel size, tenure, volume, laycan spacing) and does not bypass tenders. The ledger and charter notes give a CVC/CAG audit trail.
- **"What about port congestion and idle time?"** There is a congestion forecast per port, a demurrage-aware vessel choice, laycan-spacing rules, and the idle manager (triangulation backhaul, relet, JIT slow-steaming).
