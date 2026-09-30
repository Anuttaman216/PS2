# FreightSaarthi: SIH 2026 video script (Team SINISTER SIX · 153339 · PS 26006)

**Format:** screen recording with voiceover. Part A plays the PPT; Part B records the live prototype.
**Runtime:** full version ≈ **7:55** (PPT ≈ 3:30 + prototype ≈ 4:25). Dropping the lines marked **[CUT]** gives a tight **≈ 7:10** version (PPT ≈ 3:15 + prototype ≈ 3:55).
**Speakers:** M1–M6 = team members 1–6. Reassign freely, but keep each speaker on a continuous block so the voice doesn't jump every sentence.
**Pace:** about 150 words a minute. The voiceover text below is written to be *spoken*, so read it naturally rather than word-perfect.

---

## Part A: Presentation (≈ 3:30)

| Time | Slide / on screen | Speaker | Voiceover |
|---|---|---|---|
| 0:00 – 0:14 | **Slide 1: Title** | M1 | Namaste. We are team **Sinister Six**, team ID 153339. Our problem statement is **26006** from the **Ministry of Steel and SAIL**: an intelligent freight forecasting model for vessel chartering and coal procurement to India's East Coast. Our solution is **FreightSaarthi**. |
| 0:14 – 0:33 | **Slide 2**: point to *"How it addresses the problem"* table | M1 | Today SAIL charters coal ships one cargo at a time, after checking the spot market every day. Freight is extremely volatile, and East Coast ports differ hugely: Haldia takes about eight metres of draft, Gangavaram almost twenty. The wrong ship, or the wrong week, costs real money. |
| 0:33 – 1:09 | Slide 2: *"Detailed explanation"* column | M1 | FreightSaarthi does four things. It **forecasts freight** for all four ship classes, one to twenty-six weeks ahead, as probability bands. It **checks every ship** against both ports and the straits on the way, to get the real parcel size. It turns that into a **landed cost per tonne** for any origin and East Coast port. And it **decides the contract mix**: how much to lock in COAs or time charters, how much to leave on spot, and *when*. That is the objective of this problem statement: from single spot fixtures to planned multi-voyage contracts. |
| 1:09 – 1:43 | Slide 2: the **six innovation tiles** (point at each) | M2 | What makes it different. **One**, we forecast just four class rates and derive any route through voyage physics, so new lanes work from day one. **Two**, the **Charter Ladder**, a risk-aware optimiser that locks cover in tranches of at most 35 percent a week. **Three**, a **draft, tide and monsoon** feasibility twin, including straits like Torres and Suez. **Four**, honest evidence: we tune on *money saved* and run a **placebo test**. **Five**, a **Broker Quote X-ray** and an idle-time manager. **Six**, an **audit ledger** and real-data upload. |
| 1:43 – 2:11 | **Slide 3**: follow the six boxes left → right | M2 | It runs in six stages. First, **data**. Then the **forecast**, an ensemble of LightGBM quantiles, a structural model and a random walk, calibrated with conformal prediction. Next, **150 market scenarios** and the **cargo-at-draft physics**. The **Charter Ladder** is a stochastic linear programme that minimises cost plus a CVaR risk penalty in about thirty milliseconds. Last comes the **cockpit** with its decision ledger. It's Python, FastAPI and SQLite with a plain JavaScript front end, running offline on a laptop. |
| 2:11 – 2:39 | **Slide 4**: chart, then risk table | M3 | It is feasible today. The prototype is built, with **35 API endpoints** and automated tests. The forecast beats a random walk by up to **twelve and a half percent** at four weeks, with calibrated bands. Every major risk has a mitigation, from licensed data to PSU audit rules. **[CUT]** When SAIL shares its history, the Data Hub retrains everything without code changes. |
| 2:39 – 3:15 | **Slide 5**: four stat cards, then bar chart | M4 | In a walk-forward backtest on Hay Point to Paradip, FreightSaarthi cut landed freight by **13.9 percent**, about **49.7 million dollars** over 22 quarters. Spot fixtures fell from **268 to 54**, with **73 percent** of volume on multi-voyage contracts, and the bad-quarter cost fell from 20.6 to 17.7 dollars a tonne. The data is **synthetic**, so this proves the *method*, not SAIL's actual savings. **[CUT]** Slow-steaming instead of idling also saves about **380 tonnes of fuel** per idle window. |
| 3:15 – 3:30 | **Slide 6**: point to placebo chart | M4 | Our methods come from published research, and our key check is the **placebo test**: in an unpredictable market, our timing edge disappears, so we know we are not fooling ourselves. Now, the live prototype. |

---

## Part B: Live prototype (≈ 4:25)

> Record in this order. The **Data Hub step is last on purpose**, because uploading data changes every page. Restore the synthetic demo after recording that step.

| Time | On screen / click path | Speaker | Voiceover |
|---|---|---|---|
| 0:00 – 0:18 | Open **localhost:8000**, let the preloader finish, rest on the hero map | M5 | This is FreightSaarthi running live. The map shows SAIL's coal lanes: Queensland, Mozambique, Indonesia, Russia and the US via Suez, sailing into Paradip, Dhamra, Vizag and Haldia. Ship colours are vessel classes, and the market wire at the bottom streams forecast rates and port waiting times from our API. |
| 0:18 – 0:35 | Scroll to **"Will it fit?"** and click **Haldia**, then **Gangavaram** | M5 | This is the port physics. At Haldia's eight-metre draft only a Handysize can call. At Gangavaram even a Capesize loads full. Watch the ships settle to the port's draft. |
| 0:35 – 0:45 | Scroll to **Modules** (show the latency dots) and click **Plan a Charter** | M5 | **[CUT]** Every card here pings its real endpoint, so these latencies are live. Let's plan a charter. |
| 0:45 – 1:20 | **Plan**: *Pilot* preset. Point at the recommendation, mix bar, alternative-port box and "Why" list | M5 | We need 900,000 tonnes over 13 weeks from Hay Point to Paradip. The server runs the optimiser instantly: **seven part-laden Capesizes of 137,000 tonnes**. The binding constraint is Paradip's 15-metre draft. The forecast is softening, so it locks only 17 percent on time charter this week and keeps the rest on timed spot. It also finds that **Gangavaram would be about $2.9 a tonne cheaper** if rail costs allow, and it explains *why* in plain words. |
| 1:20 – 1:35 | Type **15.5** in *Broker quote* and show the gauge | M6 | A broker quotes $15.50. The **Quote X-ray** puts it at the **93rd percentile** of fair value, so we counter near $14.20. |
| 1:35 – 1:55 | Drag **Freight shock** to **+30%** and watch the mix bar | M6 | Now a what-if: we expect freight to jump 30 percent. The ladder reacts. Cover goes from 17 percent to **85 percent**, split between COA and time charter, so we are locked in before the spike. |
| 1:55 – 2:15 | Click preset **US → Haldia (avoid Suez)** and point at the notes and alternative port | M6 | **[CUT]** A hard case: US coal to Haldia while avoiding the Red Sea. It reroutes via the Cape, adding 3,100 miles, drops to Handysize because of the river draft, and flags Gangavaram as the smarter port. Then we **save this to the ledger**. |
| 2:15 – 2:55 | Go to **Programmes & Ledger**. Click **Plan ▶** on *Mozambique PLV – Dhamra*, **Decide** → Accepted, "GM (Shipping)", then **Note ↗** | M6 | SAIL's cargo requirements live here as programmes. We plan the Mozambique programme, and it is logged instantly with an **input fingerprint and the data version**. The officer records the decision, accepted with a COA tender floated, and the programme moves to *contracted*. Every entry prints as a **charter note** for the tender file, and the ledger exports to CSV. That is the audit trail a public-sector company needs. |
| 2:55 – 3:15 | **Risk & Alerts**: click the *Cyclone · Odisha* sample, then **Analyse & store** | M1 | Early warnings: volatility, spike and crash odds, and port congestion. We paste an IMD cyclone bulletin, and it becomes a **typed event mapped to every SAIL lane** into Paradip and Dhamra. |
| 3:15 – 3:40 | **Backtest Proof**: waterfall, then the placebo card | M2 | The proof. The waterfall shows where the saving comes from: mostly right-sizing the vessel, then timing and the ladder. Signing contracts *without* the model saves nothing. And in the placebo market our edge vanishes, exactly as it should. |
| 3:40 – 3:52 | **Network View**: click **HALDIA**, then **PARADIP** | M2 | **[CUT]** The same engine ranks every origin into every port, which gives freight-adjusted FOB break-even for procurement. |
| 3:52 – 4:12 | **Data Hub**: drag the template CSV in, show the validation report, click **Run on uploaded data** (speed up the ~35 s wait in editing), then point at the **UPLOADED DATA** chip | M3 | And when SAIL gives us real history: download the template, drop the file in, and it is validated, with any missing columns clearly flagged. The **whole system retrains in about 35 seconds**, and every page now runs on SAIL's data. |
| 4:12 – 4:25 | Open **localhost:8000/docs** (Swagger) and scroll | M4 | Behind it is a documented API with 35 tested endpoints. FreightSaarthi turns daily spot chasing into a planned, risk-controlled and auditable chartering strategy. Thank you from team Sinister Six. |

---

## Novelty checklist (every item must be *said* at least once)

| # | Novelty | Where it is covered |
|---|---|---|
| 1 | Physics-informed translator: 4 class forecasts → any route | A 1:09 · B 0:45 |
| 2 | CVaR Charter Ladder, ≤35% tranches, moves spot → multi-voyage | A 1:09 · A 1:43 · B 1:35 |
| 3 | Draft–tide–monsoon twin incl. straits (Torres, Suez) | A 1:09 · B 0:18 · B 1:55 |
| 4 | Probabilistic, calibrated forecasts (conformal bands) | A 0:33 · A 1:43 · A 2:11 |
| 5 | Decision-focused tuning + **placebo test** (honest evidence) | A 1:09 · A 3:15 · B 3:15 |
| 6 | Broker Quote X-ray | A 1:09 · B 1:20 |
| 7 | Idle-time manager (relet, triangulation, JIT slow-steaming, laycan spacing) | A 1:09 · A 2:39 |
| 8 | Alternative-port / freight-adjusted FOB break-even | B 0:45 · B 3:40 |
| 9 | Event intelligence (news → typed event → impacted lanes) | B 2:55 |
| 10 | Audit ledger, input hash, charter note (PSU / CVC-CAG ready) | A 1:09 · B 2:15 |
| 11 | Real-data upload + full retrain in ~35 s | A 1:09 · B 3:52 |
| 12 | Offline, laptop-grade, 35 tested endpoints | A 1:43 · A 2:11 · B 4:12 |

If you use the short cut, every item is still covered: items 7 and 11 by the innovation tiles at A 1:09, item 8 at B 0:45.

## Numbers cheat-sheet (say them exactly like this)

| Figure | Say |
|---|---|
| Backtest saving | "13.9 percent" (90% CI 11.4–16.3) |
| Money | "about 49.7 million dollars over 22 quarters" |
| Spot fixtures | "268 to 54" |
| Contracted share | "73 percent on multi-voyage contracts" |
| Bad-case cost (CVaR90) | "20.6 to 17.7 dollars a tonne" |
| Forecast skill | "up to twelve and a half percent better than a random walk at four weeks" |
| Optimiser speed | "about thirty milliseconds" |
| Pilot plan | "seven part-laden Capesizes of 137,000 tonnes" |
| What-if +30% | "cover goes from 17 to 85 percent" |
| Quote X-ray | "$15.50 is at the 93rd percentile" |
| Retrain time | "about 35 seconds" |
| Fuel saving | "about 380 tonnes of fuel per idle window" |
| Always add | "the market data is synthetic, so this proves the method, not SAIL's actual savings" |

**Pronunciation:** FreightSaarthi = *Freight-SAAR-thee* · CVaR = *C-V-a-R* · COA = *C-O-A, contract of affreightment* · HiGHS = *highs*.

---

## Recording checklist

**Before recording**
1. Run `python tests/test_api.py` and expect 11/11 passed.
2. Reset the demo data: stop the server, delete `outputs/freightsaarthi.db`, then run `python serve.py`. The 4 demo programmes are re-seeded automatically.
3. Check the top bar says **SYNTHETIC DATA**. If not, open **Data Hub → ↺ Restore synthetic demo**.
4. Download `freightsaarthi_market_template.csv` from the Data Hub in advance.
5. Use Chrome in full screen at 1920×1080 and 100% zoom, with the bookmarks bar hidden and notifications muted.
6. Rehearse the Plan page once. The sliders recalculate as they move, so drag slowly.

**While recording**
- Record the PPT and the prototype as separate clips, then join them in the editor.
- Leave 1–2 seconds of silence at each click so the edit points are clean.
- Keep the mouse still while speaking about something on screen.

**After recording**
1. Speed up or cut the retrain wait in the Data Hub step.
2. Add captions for the key numbers if your editor supports it.
3. Restore synthetic data afterwards (Data Hub → ↺ Restore synthetic demo), so the app is ready for live judging.
