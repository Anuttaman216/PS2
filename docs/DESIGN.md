# FreightSaarthi: Intelligent Freight Forecasting & Charter Decision System
**SIH 2026 · PS 26006 · Ministry of Steel / SAIL**: bulk cargo (coking coal) from Australia, the US, Mozambique, Russia and Indonesia to India's East Coast (Paradip, Vizag, Gangavaram, Gopalpur, Dhamra, Sagar/Sandheads, Haldia).

> **Pitch in one line.** FreightSaarthi does not stop at forecasting a freight rate. It turns a probabilistic freight forecast into an audit-ready charter decision: *which ship, how big a parcel, which contract (spot / COA / period TC), how much, and when*. It proves the value with an honest walk-forward backtest against SAIL's current daily-spot practice.

---

## 0. What makes this different (summary of the novelties)

| # | Novelty | Why a judge would not expect it | Where |
|---|---|---|---|
| N1 | **Physics-informed freight translator.** We forecast only the 4 class TCE indices + bunker, then derive $/t for *any* origin→port through explicit voyage economics | New lanes work from day one without route history. Explainable ("freight rose because Cape TCE rose 12% and bunkers 5%") | `saarthi/physics.py` |
| N2 | **Charter Ladder**: a two-stage stochastic LP with CVaR that decides *what share to lock this week* in COA/TC, with volume uncertainty and MOLCHOPT tolerance / dead-freight modelled | This is how a treasury desk hedges, not how a forecasting demo works. It directly delivers the PS objective: from many spot fixtures to multi-voyage contracts | `saarthi/optimizer.py` |
| N3 | **Decision-focused calibration.** Optimiser knobs (risk λ, stopping margin δ, ladder step) are chosen by *realised charter cost* on a validation period, not by forecast MAE | The judged metric is money saved, and the tuning targets money saved | `run_pipeline.py::tune` |
| N4 | **Honesty protocol**: placebo "martingale world", random-walk-forecast ablation, "COA-without-a-model" control, oracle-capture ratio, block-bootstrap CIs | Most submissions report in-sample MAPE. We show where the savings come from and that the model finds **no** edge where none exists | `backtest.py`, dashboard "Backtest proof" |
| N5 | **Draft-Tide-Monsoon Feasibility Twin**: port and chokepoint drafts (Torres Strait 12.2 m, Suez), monsoon draft/wait deltas, LOA/beam, berth DWT, stockyard, geared/gearless, lighterage at Sandheads, **draft-staged two-port discharge** (Dhamra → Paradip) | Turns "port constraints" into computed parcel sizes and names the binding constraint | `physics.check`, `two_port_discharge` |
| N6 | **Broker Quote X-ray**: type the broker's $/t and get its percentile in our fair-value band, plus a counter-offer | A negotiation copilot the chartering desk can use daily | Dashboard → Plan |
| N7 | **Idle & deadheading manager**: triangulation backhaul (East-Coast iron ore/pellets → China → ballast to Australia), short relets, JIT slow-steaming (cube-law fuel), laycan-spacing rule against self-queuing | Tackles PS item (c) with numbers, and adds a CII/emissions angle | `saarthi/idle.py` |
| N8 | **Event intelligence**: news/IMD/port notices → Claude structured extraction → lane graph → impacted SAIL lanes | Early warnings name the affected shipment and lane, not a generic headline | `saarthi/events.py` |
| N9 | **Freight-per-tonne-of-hot-metal KPI** and freight-adjusted FOB break-even across origins | Speaks the plant CFO's language and links freight to procurement | Dashboard KPIs, Network tab |
| N10 | **Offline, audit-ready, PSU-grade**: single-file dashboard (no server), every recommendation logged with inputs and forecast version for CVC/CAG audit, and every assumption tagged with a "verify_with" source | Fits government procurement reality: tenders, audit trails, data sovereignty | §11, §15 |

---

## 1. Framing the problem as decisions

SAIL does not buy "a forecast". Each quarter it has to make four linked decisions for every lane:

| Decision | Horizon | Cost driver it controls | PS item |
|---|---|---|---|
| D1 Vessel class and parcel size | per programme | economies of scale vs draft, LOA, stockyard, demurrage | (b) |
| D2 Contract structure: spot / COA / period TC (and optional FFA hedge) | 1-12 months | level **and variance** of freight | Objective, (a) |
| D3 Market entry timing: when to lock each tranche, when to fix each spot cargo | 1-12 weeks | buying low vs high in a mean-reverting, volatile market | (a) |
| D4 Operations: laycan spacing, idle-gap use, ballast positioning, port choice | days-weeks | demurrage, idle hire, deadheading | (c), (d) |

Every module exists to improve one of these decisions, and the backtest scores the decisions, not the forecast.

---

## 2. Candidate approaches compared

| # | Approach | Strengths | Weaknesses | Verdict |
|---|---|---|---|---|
| A1 | **Classical econometrics** (SARIMAX / VAR / VECM on Baltic indices + macro) | interpretable, needs little data, gives good baselines | linear, weak on regime shifts and fat tails; point forecasts | **Keep** as the *structural member* of the ensemble |
| A2 | **Gradient-boosted quantile regression** (LightGBM, global model pooled across classes and routes) | nonlinear, handles many leading signals, gives quantiles cheaply, transfers across classes | needs feature engineering; can overfit small samples | **Keep** as the ML member |
| A3 | **Deep sequence models** (TFT, N-BEATS, DeepAR) | multi-horizon, attention-based explanations | data-hungry (weekly freight has ~600 points per series), opaque, heavy | **Defer** to Phase 3, once AIS and daily data exist |
| A4 | **Time-series foundation models** (Chronos-Bolt, TimesFM, Moirai) zero-shot | strong zero-shot, probabilistic, no training | does not use SAIL's exogenous drivers natively; licensing and compute | **Plug-in member** (`FoundationMember` slot) weighted by trailing loss |
| A5 | **Structural supply-demand model** (tonne-miles vs fleet → utilisation → convex rate curve) | economic story, useful for scenarios | needs fleet/orderbook data, slow to react | **Use as scenario generator** for stress tests (Phase 2) |
| A6 | **Pure stochastic optimisation / simulation** (Monte Carlo + stochastic LP, no ML) | robust decisions under uncertainty | only as good as the scenarios | **Keep** as the decision layer, fed by A1+A2(+A4) |
| A7 | **Reinforcement learning chartering agent** | learns policies end to end | sample-inefficient, hard to audit, risky for a PSU | **Reject** for decisions. Use RL only as a policy-search benchmark offline |
| A8 | **Rule-based expert heuristics** (the current desk practice, formalised) | trusted, transparent | reactive, no forecast | **Keep** as the **baseline B0** that must be beaten |

**Final design.** Combine the forecasting strengths of A1 + A2 (+ A4 plug-in), calibrate them with conformal prediction, turn them into joint scenarios with a copula, and pass those scenarios to the A6 decision layer (Charter-Ladder LP). Add the physics translator (N1), the feasibility twin (N5), the idle manager and the event intelligence, and tune the whole chain on decision cost (N3).

---

## 3. System architecture

```
                         ┌────────────────────── DATA LAYER ───────────────────────┐
 Baltic/broker indices ─►│ Market store  (TCE by class, route $/t fixtures, FFA)   │
 Bunker, coal, PMI, FX ─►│ Macro/commodity store                                   │
 AIS (ballasters, ETAs)─►│ Fleet & AIS store  (ballaster counts, port queues)      │
 Port notices, IMD, news►│ Event store  (raw text → typed events via Claude)       │
 Port & vessel specs   ─►│ Constraint register (draft/LOA/beam/rates, verify_with) │
 SAIL ERP/SAP stems     ►│ Programme store (volumes, laycans, plant stocks)        │
                         └───────────────┬─────────────────────────────────────────┘
                                         │ causal feature builder (publication lags)
 ┌──────────────────── INTELLIGENCE LAYER ─┴──────────────────────────────────────────┐
 │ M1 Forecaster: GBM-quantile + structural + RW (+ Chronos/TimesFM) → weighted by     │
 │    trailing pinball → online CQR conformal bands (1-26 w, extrapolated to 52 w)     │
 │ M2 Scenario engine: Gaussian copula paths (Brownian across horizons, common factor  │
 │    across classes) + bunker + congestion + volume scenarios; stress scenarios       │
 │ M3 Physics translator + M4 Feasibility twin (ports, chokepoints, monsoon, stockyard)│
 │ M5 Congestion forecaster (climatology + AR anomaly + AIS queue, event-adjusted)     │
 │ M6 Early-warning engine (volatility regime, spike/crash prob., turning points,      │
 │    supply signal, congestion, event→lane impact)                                    │
 └──────────────────────────────────────┬─────────────────────────────────────────────┘
 ┌──────────────────── DECISION LAYER ──┴─────────────────────────────────────────────┐
 │ M7 Vessel & parcel optimiser  (min landed $/t = freight + demurrage + inventory +    │
 │    lighterage + inland)                                                             │
 │ M8 Charter Ladder: 2-stage stochastic LP, E+λ·CVaR, COA/TC/spot (+FFA), tolerance,  │
 │    dead-freight, ladder step cap, re-solved weekly                                  │
 │ M9 Spot timing: optimal-stopping rule on the forecast path                          │
 │ M10 Idle & deadheading manager (triangulation, relet, JIT, laycan spacing)          │
 └──────────────────────────────────────┬─────────────────────────────────────────────┘
 ┌──────────────────── EXPERIENCE & GOVERNANCE ─┴─────────────────────────────────────┐
 │ Cockpit dashboard (single offline HTML or React/FastAPI) · Quote X-ray · What-if    │
 │ Recommendation ledger (hash, inputs, model version, decision, outcome) → audit/CAG  │
 │ Rolling backtest & shadow mode · Model monitoring (coverage drift, regret drift)    │
 └────────────────────────────────────────────────────────────────────────────────────┘
```

**Deployment.** Python (pandas, LightGBM, SciPy/HiGHS), a nightly batch job, and FastAPI to serve the React dashboard. The pilot ships as a **single self-contained HTML cockpit** that recomputes lane economics in the browser, so it runs offline and on-premise inside SAIL's network (data sovereignty, no cloud dependency). The LLM event extraction is optional and can run on a sovereign or on-premise endpoint.

---

## 4. Modules

### M1 Probabilistic forecaster (`saarthi/forecast.py`)
* **Target:** log-return of class TCE, `y(t+h) − y(t)`, for h ∈ {1,2,4,8,12,16,20,26} weeks (interpolated weekly, extrapolated to 52 with widening bands flagged "low confidence").
* **Members**
  1. **Global LightGBM quantile regression** (q10/q50/q90). One model per horizon × quantile, **pooled across the 4 classes** with a class feature. Pooling quadruples the sample and lets a new class or route borrow strength.
  2. **Structural ridge model:** mean reversion (deviation from long-run level), supply (ballaster z-score, 4-week change), demand (coal momentum, China PMI), seasonality of the *target* week. Every coefficient is readable, so this member also serves the explainability panel.
  3. **Random walk** with empirical h-step volatility. This is the benchmark that most freight models fail to beat, and we report skill against it.
  4. *(plug-in)* **Chronos-Bolt / TimesFM** zero-shot on the TCE series, added when the package is available.
* **Features** (all causal, with publication lags): returns r1/r4/r12/r26, deviation from the 52-week and expanding mean, 8-week volatility, Cape–class spread and Cape momentum (Capes lead smaller sizes), ballaster count level/z-score/change (AIS supply proxy), coal price momentum (1-week lag), China PMI (2-week lag), bunker momentum, week-of-year of now and of the target, stylised seasonality.
* **Combination:** quantile averaging with weights ∝ (1/trailing pinball loss)², computed per horizon from out-of-sample errors whose targets have already been realised.
* **Calibration:** **online conformalised quantile regression (CQR).** The 80% band is widened or narrowed by the empirical quantile of past non-conformity scores, `max(q10−y, y−q90)`, using only past realised targets. The result is honest coverage without distributional assumptions.
* **Why:** freight is fat-tailed and regime-switching, so decisions need calibrated *distributions*. An ensemble of a nonlinear learner and an interpretable structural model is robust on ~600 weekly points. Conformal calibration gives the coverage guarantee a risk committee can rely on.

### M2 Scenario engine
* Joint paths from marginal quantiles via a **Gaussian copula**. Horizons follow Brownian dependence, `corr(Z_h, Z_k) = √(min/max)`. Classes share a common factor (ρ≈0.7) so that Cape and Panamax move together, as they do in reality. Paths use a two-piece normal in log space to keep the skew implied by the q10/q50/q90 band.
* Adds bunker paths (random walk at empirical volatility), congestion (climatology + AR anomaly) and **programme-volume** uncertainty (lognormal, σ≈8%), because SAIL's own requirement is uncertain too.
* **Stress library** (Phase 2): 2021-style Cape spike, Red Sea closure (+tonne-miles), China steel curbs, cyclone at Paradip, Queensland flood.

### M3 Physics translator + M4 Feasibility twin (`saarthi/physics.py`)
* **Feasibility per class × (load, discharge):**
  * LOA/beam vs both ports' limits, and berth DWT limits (reported as a warning).
  * **Allowed draft** = min(load sailing draft, discharge arrival draft (+ monsoon delta), chokepoint drafts on the routing).
  * **Cargo at draft** = DWT − TPC·100·(T_design − T_allowed) − constants.
  * Stockyard cap (≤50% of free yard), stem-size cap, uneconomic part-cargo test (<45% of capacity).
  * Small ships reroute through Torres Strait when their laden draft is ≤ 12.2 m. Anchorage ports add lighterage.
  * The **binding constraint is named** in the output (e.g. "draft 15.0 m (discharge port)").
* **Voyage economics:** laden/ballast days (distance / speed), port days (cargo / handling rate capped by ship size + normal waits + manoeuvring), fuel (laden/ballast/port consumption), port costs, commission.
  `freight $/t = (TCE·days + fuel·bunker + port costs)/cargo · (1+comm) = A·TCE + B·bunker + C`.
  Because freight is linear in TCE, the scenario engine converts TCE paths to $/t exactly and cheaply.
* **Landed cost** to SAIL = freight + expected demurrage (congestion forecast, class-specific waiting multiplier, e.g. Capes wait longer at Paradip) + stockyard carrying cost (cargo value × WACC × parcel/draw-rate/2) + lighterage + optional inland differential.
* **Two-port discharge:** a Capesize discharges at a deep port (Dhamra or Gangavaram) until its draft fits the second port (Paradip or Vizag).

### M5 Congestion forecaster
Week-of-year climatology (SW-monsoon and cyclone seasons) + AR(1)-decaying current anomaly. In production, add AIS queue length at anchorage, the berth line-up and event shocks (cyclone ⇒ +2–3 days of port closure).

### M6 Early-warning engine (`saarthi/alerts.py`, `saarthi/events.py`)
* **Market:** volatility-regime percentile (8-week realised vs history), P(+20% within 4 weeks) and P(−20%) from the scenarios, turning points (sign change between the 4- and 12-week medians), and the supply signal (ballaster z-score).
* **Ports:** expected waiting above the historical 80th percentile in the next 8 weeks. The alert suggests spreading laycans or an alternate port.
* **Events:** notice text → **Claude structured output** (JSON schema: type, locations, severity, duration, freight direction) → joined to the lane graph (port / chokepoint → lanes). A deterministic rule extractor is the offline fallback. Russian-origin lanes carry a sanctions/compliance screening flag.

### M7 Vessel & parcel optimiser
For each feasible class: n voyages = ⌈V / parcel⌉, laycans spread over the programme, landed-cost distribution over the scenarios. The recommended class is the one with the lowest median landed cost. P10–P90 is shown for every class so the manager sees the trade-off (e.g. a part-laden Capesize is cheaper per tonne but carries more demurrage risk at Paradip).

### M8 Charter Ladder (`saarthi/optimizer.py`)
Two-stage stochastic LP, re-solved every week while a block's contracting window is open:

```
decision now      a ≥ 0  (new COA share @ quote P_now),  b ≥ 0 (new TC share @ unit cost TC_s)
recourse (per s)  lift_prev_s, lift_s ∈ [0, (1+tol)·share]   (MOLCHOPT liftings)
                  dead_prev_s ≥ (1−tol)a_prev − lift_prev_s,  dead_s ≥ (1−tol)a − lift_s
                  spot_s = v_s − b_prev − b − lift_prev_s − lift_s ≥ 0
cost_s = b_prev·TCprev_s + b·TC_s + P_prev(lift_prev_s + δf·dead_prev_s) + P_now(lift_s + δf·dead_s) + Spot_s·spot_s
min  (1/S)Σ cost_s + λ·[u + Σ z_s /((1−α)S)],   z_s ≥ cost_s − u, z_s ≥ 0      (Rockafellar–Uryasev CVaR)
s.t. a_prev+b_prev+a+b ≤ max_lock (0.85);  a+b ≤ step_cap (ladder);  b_prev+b ≤ tc_cap·min v_s
```
* **Why an LP:** it is exact, fast (HiGHS in milliseconds), auditable and explainable (shadow prices show which constraint is costing money). It captures the real contract mechanics: tolerance, dead-freight and volume risk.
* **Ladder step cap:** no more than 35% of the volume is locked on a single week's signal. This diversifies entry timing, the way procurement desks average in.
* **FFA extension (Phase 2):** add a hedge variable h with payoff `h·(Index_s − F_now)` and a basis-risk term (C5/P3A vs the Aus–India lane). The LP stays linear.

### M9 Spot timing: optimal stopping
For each spot cargo with laycan L, the fixing window is [L−5, L−1]. At week f, fix if `TCE_f ≤ (1+δ)·min_k median_forecast(f+k)` over the rest of the window, otherwise wait; fixing is forced at L−1. δ is tuned on validation (N3).

### M10 Idle & deadheading manager (`saarthi/idle.py`)
For period tonnage it computes turnaround, voyages per period, unutilised days and ballast share, then ranks the options:
* direct ballast;
* **triangulation** (iron ore/pellet backhaul from East Coast India to China, then ballast China → Australia);
* short relet of the gap (e.g. an Indonesia–India coal round);
* **JIT slow-steaming** (cube-law fuel saving instead of idling at anchorage; also lowers CII);
* **laycan spacing** ≥ discharge time + buffer, so SAIL's own ships do not queue behind each other.

---

## 5. Data sources

| Data | Use | Real source (production) | Pilot status |
|---|---|---|---|
| Class TCE indices (BCI 5TC, BPI 82, BSI 63, BHSI 38) | M1 target | Baltic Exchange (licensed); broker assessments | **SYNTHETIC** (stylised facts, `synth.py`) |
| Route fixtures $/t (Aus–India coal, EC India) | route basis calibration | SAIL's own fixture history (ERP/SAP), broker fixture lists | not used (translator is zero-shot) |
| BDI | public proxy | Investing.com / Trading Economics / news | proxy option |
| FFA curves | market forward, hedge | Baltic Forward Assessments, SGX/EEX | **SYNTHETIC**: semi-efficient forward (mean reversion + public seasonality) |
| Bunker VLSFO (Singapore, Fujairah) | voyage cost | Ship & Bunker, port indices | **SYNTHETIC** |
| Coking coal price (Aus PLV HCC), thermal coal | demand signal | World Bank Pink Sheet (free, monthly), Platts/Argus (licensed) | **SYNTHETIC** |
| China PMI / steel output, India steel production | demand | NBS/Caixin, worldsteel, JPC India | **SYNTHETIC** |
| AIS: ballaster counts, ETAs, anchorage queues | supply signal, congestion | Spire / MarineTraffic / Kpler (licensed); **UN Global Platform AIS** (government access); IMF PortWatch | **SYNTHETIC** ballaster index |
| Port calls & disruptions | congestion, chokepoints | **IMF PortWatch** (free, AIS-derived) | proxy (Phase 1) |
| East-Coast port waiting days, berth line-ups | congestion | Paradip PA / Vizag PA / SMP Kolkata daily reports, Indian Ports Association | **SYNTHETIC** with monsoon/cyclone seasonality |
| Port limits (draft, LOA, beam, DWT, rates) | M4 | Port authority draft notices & handbooks | **ASSUMPTIONS**, each tagged `confidence` + `verify_with` (`config/ports.json`) |
| Chokepoint drafts (Torres, Suez, Malacca) | M4 | AMSA, SCA, MPA | **ASSUMPTIONS** |
| Distances | M3 | searoute / Netpas / BlueWater | **APPROX** (±5%) |
| Vessel particulars | M3/M4 | Q88, Equasis (free), owners | **ASSUMPTIONS** (standard eco ship per class) |
| Weather / cyclones / monsoon | M5/M6 | IMD RSMC New Delhi bulletins (free), BoM (Australia) | synthetic events in demo |
| News / notices | M6 | GDELT, shipping news RSS, port circulars | synthetic headlines (`events.py`) |
| SAIL programme: volumes, laycans, plant stock | all decisions | SAIL ERP / SAP MM, coal import plan | synthetic 900 kt/quarter pilot |

**Rule:** the pilot invents no port specification without tagging it. Every figure in `config/*.json` carries a confidence level and the document to verify it against.

---

## 6. Pilot lane end to end: Hay Point (QLD) → Paradip

1. **World:** `synth.generate("structured")` produces 2014-01 → 2026-09 weekly data for 4 class TCEs, ballaster indices, coal, PMI, bunker and waiting days at 7 East-Coast ports.
2. **Forecasts:** walk-forward from 2017-06, refit every 13 weeks, ~37 refits × 24 LightGBM models + structural + RW, online weights and CQR.
3. **Feasibility** (assumed limits): Paradip 15.0 m arrival draft ⇒ Capesize part-laden ~137 kt (binding: discharge draft); Panamax full ~80 kt; Supramax ~56 kt; Handysize ~34 kt (Torres routing).
4. **Economics:** at base rates a part-laden Capesize costs ≈ $15.0/t and a Panamax ≈ $17.6/t. The Capesize, however, carries higher demurrage risk at Paradip, and the class choice switches when Cape rates spike.
5. **Programme:** 900 kt per quarter (volume σ 8%), laycans spread over each 13-week block, COA/TC window [s−13, s−6], spot windows [L−5, L−1].
6. **Decision-focused calibration** on 2018H2–2020: grid over λ ∈ {0, 0.5, 1.5}, δ ∈ {0, 0.03}, step ∈ {0.2, 0.35}; the score is mean cost + 0.25·CVaR90.
7. **Test** 2021–2026H1 (22 quarters, ~20 Mt), with strategies B0, B1, B2, B3, FS and the oracle.
8. **Today's recommendation**, alerts, events, the network table and the dashboard are generated.

Results are in §8 and in `outputs/`.

---

## 7. Generalising to the other origins and ports

The same code runs for every lane. Only the configuration rows (port, distance, chokepoints) change, because the forecaster works on class TCEs and the translator handles the lane.

| Origin | What changes | Typical outcome (pilot assumptions) |
|---|---|---|
| **Australia**: Hay Point, Gladstone, Newcastle | Newcastle's 15.6 m draft makes Capes part-laden at load; Torres Strait open only to shallow small ships | Capes to Dhamra/Gangavaram (full), part-laden to Paradip/Vizag; COA-friendly (steady programme) |
| **USA**: Hampton Roads | 8,700 nm via Suez or 11,800 via the Cape; 15.2 m draft makes Capes part-laden; **Red Sea toggle** | Long voyages make hire the dominant cost, so period TC is relatively more attractive; the route-risk alert matters |
| **Mozambique**: Nacala, Beira | Nacala deep (Capes); Beira ~10 m (Handy/Supra only) | Class depends on the port; Indian Ocean monsoon affects waits |
| **Russia**: Vostochny, Ust-Luga | Far East via Malacca, Baltic via Suez/Cape; **sanctions/compliance flag**; winter ice at Ust-Luga | Recommendations are gated by compliance screening; insurance and payment risk shown as a separate penalty |
| **Indonesia**: Muara Berau (anchorage), Tanjung Bara | 2,800 nm short haul, anchorage floating-crane rates (~18 kt/d), barge supply | Frequent short voyages give very high COA/TC utilisation; geared Supramax/Panamax favoured at anchorages |

| East-Coast port | Constraint that dominates | Consequence |
|---|---|---|
| **Paradip** | ~15 m arrival draft, berth DWT | part-laden Cape vs full Panamax trade-off; Cape waiting multiplier |
| **Dhamra** | 18 m | full Capesize; the "first port" of a two-port discharge |
| **Gangavaram** | ~19.5 m | full Capesize, fast discharge |
| **Vizag OH** | ~16 m | part-laden Capes |
| **Gopalpur** | ~13.5 m, 230 m LOA, swell in the SW monsoon | Panamax part-laden / Supramax; monsoon downtime |
| **Haldia** | ~8 m tidal Hooghly draft, 230 m LOA | Handysize or part-laden Supramax only |
| **Sagar/Sandheads** | anchorage, lighterage +$5.5/t, weather downtime | Cape/Panamax with transloading to Haldia/Kolkata; compared against Handysize direct to Haldia |

The **Network tab** shows the best class and landed $/t for every origin × port pair, computed live. That also gives a **freight-adjusted FOB break-even**: US coal must be cheaper FOB by at least its freight premium over Australia to compete.

---

## 8. Rolling backtest design & results

### 8.1 Protocol (no leakage)
* **Walk-forward:** every forecast at week t uses models fitted on data ≤ t, refit every 13 weeks. Ensemble weights and conformal scores use only targets realised by t. Macro features carry publication lags.
* **Market quotes:** COA and TC are quoted from a *semi-efficient* market forward (owners know mean reversion and public seasonality, but not our leading signals) plus a +1% owner premium. We do **not** assume a COA discount.
* **Same world, same programme** for every strategy. Realised volume differs from plan (σ 8%), so over-locking is penalised through tolerance and dead-freight.
* **Split:** tuning on validation (2018H2–2020), headline on test (2021–2026H1); nothing is tuned on test.

### 8.2 Strategies
B0 daily spot with the Panamax habit (current practice) · B1 + optimal vessel · B2 + forecast-timed spot · B3 70% COA without a model (control) · **FS FreightSaarthi** · ORC perfect foresight (upper bound).

### 8.3 Metrics
* **Decision (primary):** average landed $/t; % and $M saving vs B0 and vs B1 with **90% block-bootstrap CI**; win-rate by quarter; **oracle-capture %**; quarterly cost std, **CVaR90** and worst quarter; number of spot fixtures (the PS objective); % volume under COA/TC; demurrage $/t.
* **Forecast (secondary):** MAPE, skill vs random walk, pinball loss, 80% coverage, directional accuracy, **Diebold-Mariano** test vs random walk, all by class × horizon.
* **Honesty checks:** placebo martingale world (timing/ladder savings should be ≈0), FS with random-walk forecasts (isolates the value of forecasting), B3 (isolates the value of *model-driven* contracting vs simply signing COAs).

### 8.4 Results (synthetic world; demonstrates the machinery, not a real-world claim)
| Strategy | avg $/t | saving vs B0 | 90% CI | $M saved | quarterly std | CVaR90 | worst qtr | win-rate | oracle capture | spot fixtures | contracted |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 Daily spot, Panamax habit | 17.50 | 0.0% | 0.0 to 0.0% | 0.0 | 1.93 | 20.59 | 20.94 | 0% | 0% | 268 | 0% |
| B1 + optimal vessel | 15.54 | 11.2% | 9.1 to 13.2% | 40.0 | 2.36 | 19.77 | 21.47 | 95% | 54% | 161 | 0% |
| B2 + timed spot | 15.29 | 12.6% | 10.4 to 14.7% | 45.0 | 2.26 | 19.50 | 21.39 | 95% | 61% | 161 | 0% |
| B3 70% COA, no model | 17.48 | 0.1% | -2.3 to 2.7% | 0.4 | 1.48 | 19.79 | 20.46 | 32% | 1% | 101 | 68% |
| **FS FreightSaarthi** | 15.06 | 13.9% | 11.4 to 16.3% | 49.7 | 1.56 | 17.73 | 18.69 | 100% | 67% | 54 | 73% |
| ORC perfect foresight | 13.87 | 20.8% | 19.0 to 22.7% | 74.0 | 1.39 | 16.17 | 16.29 | 100% | - | - | - |

Test period: 22 quarters, ~20.4 Mt. Selected knobs (validation): lambda=0.0, delta=0.03, step cap=0.35.

**How to read this honestly**
* **Savings waterfall ($/t):** B0 17.50 → vessel optimisation -1.96 → timed spot -0.24 → charter ladder -0.23 → FS 15.06. The largest block, **vessel choice**, depends on the Paradip 15.0 m draft assumption (a part-laden Capesize beats a full Panamax). It needs no forecasting skill, and it is the first thing to verify with real berth data.
* **Beyond vessel choice** (FS vs B1): 3.1% cheaper, with a large **risk cut**: quarterly std 2.36 → 1.56, CVaR90 19.77 → 17.73, worst quarter 21.47 → 18.69. FS is cheaper than B0 in 100% of quarters.
* **PS objective met:** spot fixtures 268 (B0) / 161 (B1) → **54**, with 73% of volume under multi-voyage COA/TC.
* **Signing COAs is not enough:** B3 (70% COA locked mechanically) saves 0.1% (CI -2.3 to 2.7%), which is statistically zero. Contract structure pays only when it is timed and sized by the model.
* **Value of forecasting:** FS driven by random-walk forecasts costs $15.51/t vs $15.06/t with the ensemble.
* **Placebo (martingale world, levels unpredictable):** forecast skill ≈ 0 and coverage ≈ 80%. FS vs B1 = -0.3% and timed spot vs B1 = -0.2%, i.e. **no fake timing/contracting edge** (vessel-choice savings remain, as they should, because they are physics, not prediction). An earlier placebo that was a martingale in *log* rates showed a spurious ~2% edge from convexity drift; the corrected level-martingale version removed it. We report this because it is exactly the kind of error an honest protocol exists to catch.
* **Oracle capture:** FS captures 67% of the perfect-foresight saving.
* **Forecast accuracy** (test, walk-forward, `outputs/forecast_accuracy.csv`): MAE skill vs random walk is +3 to +13% across classes at 1–12 weeks, significant (DM p<0.05) mainly at 1–8 weeks. 80% band coverage is 79–85%. Skill decays with horizon, which is realistic for freight and is why the ladder limits how much is locked on any single week's signal.
* Validation tuning chose lambda = 0 (risk-neutral), because on this lane the ladder already cuts CVaR sharply. The cockpit lets the desk raise lambda to match SAIL's risk appetite.


---

## 9. Dashboard design (cockpit)

Personas: **chartering manager** (daily), **head of shipping/procurement** (weekly/quarterly), **finance/risk** (monthly), **auditor** (ex-post).

| Tab | Contents | Key interactions |
|---|---|---|
| **Plan a charter** | Inputs: origin, destination, volume, duration, first laycan, max stem, risk appetite λ. What-if levers: freight shock, bunker change, extra congestion, monsoon, avoid Suez. Output: recommendation sentence, COA/TC/spot bar, KPIs (expected $/t, P10–P90, CVaR, $M, saving vs daily-spot habit, freight per t hot metal), class table with binding constraints, entry-timing chart (quote-if-wait-w with P(cheaper)), cost distribution, **Broker Quote X-ray**, **charter ladder** tranches | Everything recomputes live in the browser over the scenario paths |
| **Market forecast** | Fan charts per class, ensemble weights, out-of-sample accuracy (skill, coverage, DM), **explainability** (GBM gain + structural coefficients), placebo accuracy | Class selector |
| **Feasibility & ports** | Lane feasibility with laden draft and binding constraint, max-cargo matrix across all ports, port constraint register with confidence, two-port discharge | Reacts to monsoon / stem / Suez toggles |
| **Risk & alerts** | Market and congestion alerts, event feed → impacted lanes, 52-week congestion outlook, spike/crash probabilities | |
| **Idle manager** | Triangulation, relet, JIT slow-steam, laycan spacing, TC utilisation | |
| **Backtest proof** | KPIs, **savings waterfall** (vessel → timing → ladder), quarterly realised cost vs oracle, scorecard with CIs, ablations, decision-focused tuning log | |
| **Network view** | Origin × port best class and landed $/t | |
| **Assumptions** | Data provenance (real/proxy/synthetic), commercial assumptions | |

Production additions: a login with roles, a **recommendation ledger** (each recommendation stored with an input hash, model version, forecast snapshot, the decision actually taken and the realised outcome), PDF export of a "charter note" for tender files, Hindi/English labels, and email/WhatsApp alerts.

---

## 10. Phased build plan

| Phase | Duration | Deliverables | Exit criterion |
|---|---|---|---|
| **P0: Hackathon MVP** (this repo) | 36 h | synthetic world, forecaster + CQR, physics & feasibility, Charter-Ladder LP, walk-forward backtest with ablations and placebo, offline cockpit | end-to-end run ~15 min (cached reruns in seconds), honest backtest |
| **P1: Real-data pilot, Aus→Paradip** | 6–8 weeks | Baltic history + SAIL fixture history + PortWatch + World Bank coal; route-basis calibration; verified port register; **shadow mode** (recommend, don't act) | forecast skill > 0 at h=4–12 (DM p<0.1); shadow savings tracked weekly |
| **P2: All origins & ports** | 8–10 weeks | US / Mozambique / Russia / Indonesia lanes, AIS ballaster & queue feeds, Claude event pipeline, FFA hedge variable, stress library, two-port planning, React + FastAPI, ERP link for stems | coverage 75–85% on all lanes; ledger live |
| **P3: Decision-focused learning & scale** | 3 months | end-to-end DFL (SPO+/differentiable LP via cvxpylayers) fine-tuning the forecaster on regret; foundation-model member; fleet-level scheduling (MILP for laycan/berth co-scheduling); tender automation | realised savings vs B0 audited over 2 quarters |
| **P4: Institutionalise** | ongoing | model risk governance (monthly coverage/regret drift report), retraining SOP, CAG-ready audit trail, extension to limestone/iron-ore exports | adopted in quarterly chartering committee |

---

## 11. Key assumptions

1. All market data in the pilot is **synthetic** with stylised facts (volatility, regimes, seasonality, leading signals of *moderate* strength). The savings magnitudes are illustrations of the method, not forecasts of SAIL's savings.
2. Port and chokepoint limits are **public-knowledge approximations**, flagged with a confidence level and a verification source. The **Paradip 15.0 m** assumption drives the Capesize-vs-Panamax result and must be verified berth by berth.
3. The COA/TC counterparty prices off a semi-efficient forward plus a +1% premium, and volume tolerance is ±10% MOLCHOPT with dead-freight at 60% of freight beyond it.
4. Demurrage ≈ prevailing TCE; normal waiting is priced into the freight and only excess waiting is paid.
5. Vessel particulars are those of a standard eco ship; the ballast leg is 0.8 × the laden distance in owner pricing.
6. The market is price-taking: SAIL's own fixtures do not move the index. For Capesize COA tenders of several Mt/yr, a market-impact term should be added.

## 12. Limitations & mitigations

| Limitation | Mitigation |
|---|---|
| Real freight predictability is low beyond ~8–12 weeks; the synthetic world may flatter the signals | placebo + random-walk ablation; ladder step cap and CVaR limit damage when the forecasts are wrong; value comes also from vessel choice and risk reduction, which do not need forecasting skill |
| The two-stage LP is an open-loop approximation of an adaptive problem | re-solved weekly (rolling horizon); Phase 3: multistage scenario trees or policy search |
| COA/TC pricing and availability depend on counterparties (tender response) | model quotes as distributions, collect real tender responses in the ledger, learn the premium |
| Port data drift (dredging, new berths) | constraint register with `verify_with` and a review date; alerts when an actual draft notice differs |
| Coking-coal quality constraints limit origin switching | the Network view shows freight only; origin choice stays with the blend/quality team |
| LLM extraction errors | schema-constrained output, rule fallback, human confirmation for severity-3 events |
| PSU procurement rules (tenders, L1) | outputs are *timing and specification* for tenders (vessel size, laycan spread, tenure, volume), not bypasses of the process |

---

## 13. Repository map & how to run

```
config/ports.json vessels.json routes.json   # constraint register (assumptions flagged)
saarthi/synth.py        # synthetic structured world + placebo world + market forward
saarthi/forecast.py     # features, GBM/structural/RW ensemble, online CQR, copula scenarios
saarthi/physics.py      # feasibility twin, voyage economics, landed cost, two-port discharge
saarthi/optimizer.py    # Charter-Ladder CVaR LP, entry-timing distribution
saarthi/backtest.py     # walk-forward decision backtest, strategies B0..FS, oracle, metrics
saarthi/alerts.py       # volatility/spike/turning-point/supply/congestion warnings
saarthi/events.py       # news → structured events (Claude or rules) → impacted lanes
saarthi/idle.py         # triangulation, relet, JIT slow-steam, laycan spacing
run_pipeline.py         # end-to-end pipeline → outputs/results.json, dashboard.html
build_dashboard.py      # offline single-file cockpit
```
```
pip install numpy pandas scipy scikit-learn lightgbm plotly
python run_pipeline.py          # ~15 min first run, cached afterwards; --fast for a quicker demo
open outputs/dashboard.html     (self-contained ~5 MB, plotly inlined, works offline)
```

---

## 14. Implementation: the working prototype

The design is implemented as a full-stack application (see README.md for commands):

* **Backend:** FastAPI with **35 REST endpoints** (`webapp/server.py`, `webapp/ops.py`). Decisions are computed live per request: the physics feasibility check, 150-scenario landed cost, and the CVaR Charter-Ladder LP solved with HiGHS in about 30 ms.
* **Persistence:** SQLite (`webapp/store.py`) for cargo programmes, a **decision ledger** and ingested events. Each ledger entry stores an input hash, the data version and a full request/response snapshot, alongside the officer's decision and the actual fixed rate for ex-post regret tracking. The ledger produces a printable **charter note** and a CSV export. Together these form the audit trail described in §9 and §11.
* **Real-data path:** `GET /api/data/template` → `POST /api/data/upload` (validated; missing drivers proxy-filled and labelled) → `POST /api/pipeline/run?source=uploaded` retrains the forecaster, re-tunes on an automatic validation split, and re-runs the backtest and placebo, with a live stage log. Every page then reads the uploaded dataset.
* **Event intelligence:** `POST /api/events/ingest` turns free text into a typed event (rules, or Claude structured output) that is mapped to the impacted SAIL lanes and persisted.
* **Quality:** `tests/test_api.py` exercises every endpoint, including error paths, against a temporary DB. Results are 11/11 passing.
* **Frontend:** an animated landing page and a 12-page cockpit (plan, compare, forecast, feasibility, risk, idle, programmes & ledger, data hub, backtest, network, API explorer). It works offline.
