# Problem Statement: SIH 2026 · PS 26006

| Field | Value |
|---|---|
| Problem Statement ID | 26006 |
| Title | Development of an Intelligent Freight Forecasting Model for Optimized Vessel Chartering and Bulk Cargo Procurement from overseas to East Coast of India |
| Organization | Ministry of Steel |
| Department | SAIL (Steel Authority of India Ltd.) |

## Background

The current approach to vessel chartering for bulk cargo procurement to India's East Coast ports often involves daily market exploration. This leads to reactive decision-making and likely missed opportunities for cost savings and efficiency. Global freight markets are highly volatile, and supply and demand vary across key origins such as Australia, the US, Mozambique, Russia and Indonesia. This makes it hard to identify optimal entry points for short-term or mid-term charter contracts. Without a robust forecasting mechanism, choosing the most suitable vessel type (e.g., Handysize, Supramax, Panamax, Capesize) for specific cargo parcels and routes is also difficult, especially while accounting for port infrastructure limits at both origin and destination. The result is suboptimal utilization and increased idle time. This manual, market-dependent approach needs analytics to mitigate the risks of freight fluctuations and port-specific constraints, which directly affect overall logistics costs and supply chain reliability.

## Detailed description

The problem statement addresses the need for a sophisticated freight forecasting model for vessel chartering and bulk cargo procurement for East Coast Indian ports. Operations currently rely heavily on daily engagement with the freight market. This traditional method has several inefficiencies:
- there is no predictive insight into future freight rates, which makes it difficult to secure favorable short-term or mid-term charter contracts;
- the organization cannot proactively identify the optimal time to enter the market for specific vessel types and cargo sizes;
- vessel idle time is hard to minimize because planning around port-specific infrastructure restrictions is inadequate.

For instance, procuring bulk cargo (such as coal) from Australia, the US, Mozambique and Indonesia presents unique logistical challenges. Each origin-destination pair has distinct sailing distances, trade lane dynamics and, crucially, varying port capabilities. East Coast Indian ports such as Paradip, Vizag, Gangavaram, Gopalpur, Dhamra, Sagar-Sandheads and Haldia each have specific draft restrictions, berthing limitations and cargo handling capacities. These dictate the maximum permissible vessel size and the turnaround time.

The proposed system should therefore integrate multiple data points for comprehensive analysis:
- historical freight rate data for various vessel sizes across relevant trade routes;
- global economic indicators;
- commodity price trends;
- seasonal variations in demand and supply;
- real-time port congestion information for both origin and destination ports.

It must also incorporate detailed infrastructure constraints of Indian East Coast ports, such as maximum LOA (Length Overall), beam, draft and cargo handling rates, along with similar data for the loading ports in Australia, the US, Mozambique and Indonesia.

## Expected solution

An intelligent, data-driven Freight Forecasting Model. It should use advanced analytical techniques, potentially including machine learning (e.g., time series forecasting, regression models) and artificial intelligence, to predict future freight rates with a high degree of accuracy for various vessel types and trade routes. It should give actionable recommendations on:

- **a. Optimal Market Entry Timing:** Identify ideal windows to secure short-term or mid-term vessel charter contracts for specific cargo requirements, minimizing freight costs.
- **b. Vessel Type Optimization:** Recommend the most suitable vessel type (e.g., Handysize, Supramax, Panamax, Capesize) for a given cargo volume and origin-destination pair. This must consider all known port infrastructure limits at both loading and discharge ports on India's East Coast, including draft restrictions, LOA and cargo handling capabilities, to prevent idle time and ensure efficient turnaround.
- **c. Idle Scenario Management:** Propose strategies for minimizing vessel idle time by forecasting periods of low demand and suggesting alternative employment opportunities or optimized positioning to reduce deadheading.
- **d. Risk Mitigation:** Provide early warnings for potential market volatility, port congestion or other disruptions that could impact chartering decisions.

The model should be user-friendly, for example a dashboard where logistics managers input cargo details, origin/destination ports and desired contract duration, and receive comprehensive freight forecasts and actionable recommendations. The ultimate goal is to move from a reactive, daily-market approach to a proactive, predictive chartering strategy. This should lead to significant cost reductions, improved supply chain efficiency and better decision-making.

## Objective

Develop a model that helps move from the multiple single spot contracts entered into today to short-term / medium-term multi-voyage contracts.

---

## Task brief used to build this solution (from the team)

- SAIL buys bulk cargo (mainly coal) from Australia, the US, Mozambique, Russia and Indonesia for India's East Coast ports.
- The system must:
  - (a) forecast freight rates by vessel type and route, 1-12 weeks ahead;
  - (b) recommend optimal market-entry timing for short/medium-term charters;
  - (c) recommend vessel type and parcel size while respecting port limits (draft, LOA, beam, handling rate) at both ends;
  - (d) minimize idle time and ballast legs;
  - (e) give early warnings on volatility, congestion and disruptions;
  - (f) compare spot vs multi-voyage / time-charter cost;
  - (g) deliver all of this through a user-friendly dashboard.
- **Data:** where real data is licensed or unavailable, use public proxies or clearly labelled synthetic data. Do not invent port specifications without flagging them as assumptions.
- **Deliverables:**
  - at least 5 candidate approaches compared and combined into one design;
  - architecture, modules, data sources (real/proxy/synthetic), model choices, optimizer logic, dashboard design and a phased build plan;
  - one route (Australia → Paradip) built end to end on synthetic/proxy data, with a demonstration of how it generalizes;
  - a rolling backtest with metrics that prove savings vs the daily-spot baseline;
  - a justification for each choice, plus assumptions and limitations;
  - distinctive, novel features.
- **Follow-up request:** a fully working web application with a dynamic, animated, project-themed landing page (motion, scroll effects, text reveals) that leads into the available endpoints/modules.
