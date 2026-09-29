"""Static configuration: vessels, ports, routes (all flagged assumptions, see config/*.json)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

CLASSES = ["Handysize", "Supramax", "Panamax", "Capesize"]


def _load(name):
    with open(CFG / name, encoding="utf-8") as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


VESSELS = _load("vessels.json")
_ports = _load("ports.json")
DISCHARGE = _ports["discharge"]
LOAD = _ports["load"]
CHOKEPOINTS = {k: v for k, v in _ports["chokepoints"].items() if not k.startswith("_")}
ROUTES = _load("routes.json")
with open(CFG / "routes.json", encoding="utf-8") as _f:
    BACKHAUL = {k: v for k, v in json.load(_f)["_backhaul"].items() if not k.startswith("_")}

# Commercial assumptions (all tunable, all ASSUMPTIONS)
COMMERCIAL = {
    "commission": 0.0375,        # address + brokerage
    "coa_premium": 0.01,         # owner charges +1% over its forward view for fixed-price multi-voyage COA
    "tc_premium": 0.00,          # period TC priced at owner's forward view of TCE
    "relet_haircut": 0.10,       # sub-letting spare TC days earns 90% of spot TCE
    "coa_tolerance": 0.10,       # +/-10% volume tolerance in charterer's option (MOLCHOPT)
    "deadfreight_frac": 0.60,    # penalty (share of COA freight) on unlifted volume beyond tolerance
    "cargo_value_usd_t": 230.0,  # coking coal CFR approx, for inventory carrying cost
    "wacc": 0.09,                # annual cost of capital
    "plant_draw_tpd": 10000,     # rail evacuation / plant consumption from port stockyard
    "laytime_allow_days": 1.0,   # free time beyond pure handling time before demurrage (per call)
    "dem_factor": 1.0,           # demurrage rate ~ 1.0 x prevailing TCE
    "coal_per_thm": 0.78,        # t coking coal per t hot metal (blend-dependent) -> freight impact per t steel
}

# Market 'consensus forward' used by owners/brokers to quote period business:
# log-TCE mean-reverts to its long-run level with weekly persistence PHI_MKT.
PHI_MKT = 0.975
