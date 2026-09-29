"""Port-vessel feasibility engine + voyage economics ("physics-informed freight translator").

Key idea: we forecast the 4 *class* TCE indices ($/day) + bunker price, and translate them to any
origin->destination $/t freight through explicit voyage economics. A new route therefore works on
day one (zero-shot route generalisation); a learned route 'basis' corrects residual bias once
SAIL's own fixtures for that lane accumulate.
"""
import math
from dataclasses import dataclass, field

from .config import VESSELS, DISCHARGE, LOAD, ROUTES, CHOKEPOINTS, COMMERCIAL, CLASSES

CLASS_RATE_CAP = {"Handysize": 12000, "Supramax": 18000, "Panamax": 32000, "Capesize": 60000}


@dataclass
class Feasibility:
    cls: str
    feasible: bool
    cargo_t: float = 0.0
    binding: str = ""
    arrival_draft_m: float = 0.0
    notes: list = field(default_factory=list)
    nm: float = 0.0
    routing: list = field(default_factory=list)
    utilisation: float = 0.0


def handling_rate(port, cls):
    return min(port["rate_tpd"], CLASS_RATE_CAP[cls])


def laden_draft(v, cargo):
    return v["design_draft_m"] - max(0.0, v["dwt"] - v["constants_t"] - cargo) / (v["tpc"] * 100)


def check(cls, load_code, disch_code, monsoon=False, stem_t=None, avoid_chokepoints=()):
    """Max cargo for a class on a load->discharge pair, with the binding constraint."""
    v, lp, dp = VESSELS[cls], LOAD[load_code], DISCHARGE[disch_code]
    notes = []
    for port, tag in ((lp, "load"), (dp, "discharge")):
        if v["loa_m"] > port["max_loa_m"]:
            return Feasibility(cls, False, binding=f"LOA {v['loa_m']}m > {port['max_loa_m']}m at {tag} port")
        if v["beam_m"] > port["max_beam_m"]:
            return Feasibility(cls, False, binding=f"Beam {v['beam_m']}m > {port['max_beam_m']}m at {tag} port")
    # routing & chokepoints
    r = ROUTES[load_code]
    nm, routing = r["nm"], list(r["routing"])
    if any(c in avoid_chokepoints for c in routing) and r.get("alt"):
        nm, routing = r["alt"]["nm"], list(r["alt"]["routing"])
        notes.append("re-routed to avoid " + ",".join(avoid_chokepoints))
    nm += dp["offset_nm"]
    drafts = {"load port": lp["max_draft_m"],
              "discharge port": dp["max_draft_m"] + (dp["monsoon_draft_delta"] if monsoon else 0.0)}
    for c in routing:
        if c in CHOKEPOINTS:
            drafts[CHOKEPOINTS[c]["name"]] = CHOKEPOINTS[c]["max_draft_m"]
    binding_port = min(drafts, key=drafts.get)
    allowed = drafts[binding_port]
    dwt_at = v["dwt"] - v["tpc"] * 100 * max(0.0, v["design_draft_m"] - allowed)
    cargo = dwt_at - v["constants_t"]
    binding = f"draft {allowed:.1f}m ({binding_port})" if allowed < v["design_draft_m"] else "full deadweight"
    if dp.get("max_dwt") and v["dwt"] > dp["max_dwt"] * 1.02:
        # berth structural limit: port accepts only part-laden ships of this size if draft allows
        notes.append(f"berth DWT limit {dp['max_dwt']:,} t - confirm acceptance of part-laden {cls}")
    if dp.get("stockyard_t") and cargo > dp["stockyard_t"] * 0.5:
        cargo = dp["stockyard_t"] * 0.5
        binding = "stockyard space (50% of yard)"
    if stem_t is not None and cargo > stem_t:
        cargo, binding = stem_t, "cargo stem size"
    # small ships may take the shorter Torres Strait routing if laden draft allows
    if r.get("small_ship_nm") and laden_draft(v, cargo) <= CHOKEPOINTS["TORRES"]["max_draft_m"]:
        nm, routing = r["small_ship_nm"] + dp["offset_nm"], r["small_ship_routing"]
        notes.append("Torres Strait routing feasible (laden draft <= 12.2 m)")
    if dp["kind"] == "anchorage":
        notes.append(f"lighterage at anchorage (+${dp.get('lighterage_usd_t', 0)}/t, weather downtime)")
    feasible = cargo >= 0.45 * (v["dwt"] - v["constants_t"])
    if not feasible:
        binding = f"uneconomic part-cargo ({cargo:,.0f} t) - {binding}"
    return Feasibility(cls, feasible, max(cargo, 0), binding, round(laden_draft(v, max(cargo, 0)), 2),
                       notes, nm, routing, max(cargo, 0) / (v["dwt"] - v["constants_t"]))


def voyage_days(cls, f: Feasibility, load_code, disch_code, wait_load, wait_disch, ballast_factor=0.8):
    v, lp, dp = VESSELS[cls], LOAD[load_code], DISCHARGE[disch_code]
    laden = f.nm / (v["speed_laden_kn"] * 24)
    ballast = ballast_factor * f.nm / (v["speed_ballast_kn"] * 24)
    port = (f.cargo_t / handling_rate(lp, cls) + f.cargo_t / handling_rate(dp, cls)
            + wait_load + wait_disch + 1.0)
    return laden, ballast, port


def freight_per_t(cls, f: Feasibility, load_code, disch_code, tce, bunker, ballast_factor=0.8):
    """Owner's break-even voyage-charter freight ($/t) at a given TCE and bunker price,
    assuming *normal* port waiting (excess waiting is paid separately as demurrage)."""
    v, lp, dp = VESSELS[cls], LOAD[load_code], DISCHARGE[disch_code]
    la, ba, po = voyage_days(cls, f, load_code, disch_code, lp["base_wait_days"],
                             dp["base_wait_days"] * (dp["cape_wait_mult"] if cls == "Capesize" else 1.0),
                             ballast_factor)
    fuel = la * v["fuel_laden_tpd"] + ba * v["fuel_ballast_tpd"] + po * v["fuel_port_tpd"]
    cost = tce * (la + ba + po) + fuel * bunker + 2 * v["port_cost_usd"]
    return cost / f.cargo_t * (1 + COMMERCIAL["commission"])


def class_wait(cls, disch_code, wait):
    dp = DISCHARGE[disch_code]
    return wait * (dp["cape_wait_mult"] if cls == "Capesize" else {"Panamax": 1.0, "Supramax": 0.85, "Handysize": 0.75}[cls])


def demurrage_per_t(cls, f, disch_code, wait_realised, tce):
    """Charterer-paid demurrage for waiting above the 'normal' wait assumed in the freight."""
    dp = DISCHARGE[disch_code]
    normal = class_wait(cls, disch_code, dp["base_wait_days"]) + COMMERCIAL["laytime_allow_days"]
    excess = max(0.0, class_wait(cls, disch_code, wait_realised) - normal)
    return excess * tce * COMMERCIAL["dem_factor"] / f.cargo_t, excess


def inventory_per_t(cargo_t):
    """Carrying cost of a bigger parcel sitting in the stockyard."""
    days = cargo_t / COMMERCIAL["plant_draw_tpd"] / 2
    return COMMERCIAL["cargo_value_usd_t"] * COMMERCIAL["wacc"] / 365 * days


def landed_freight(cls, f, load_code, disch_code, tce, bunker, wait_disch, inland_diff=0.0):
    """Total charterer cost per tonne: freight + expected demurrage + inventory + lighterage + inland."""
    dp = DISCHARGE[disch_code]
    fr = freight_per_t(cls, f, load_code, disch_code, tce, bunker)
    dem, _ = demurrage_per_t(cls, f, disch_code, wait_disch, tce)
    return fr + dem + inventory_per_t(f.cargo_t) + dp.get("lighterage_usd_t", 0.0) + inland_diff


def feasibility_matrix(load_code, disch_code, monsoon=False, stem_t=None):
    return {c: check(c, load_code, disch_code, monsoon, stem_t) for c in CLASSES}


def two_port_discharge(cls, load_code, first, second):
    """Draft-staged discharge: deep port first, lighten enough to meet the second port's draft."""
    v = VESSELS[cls]
    f1 = check(cls, load_code, first)
    d2 = DISCHARGE[second]["max_draft_m"]
    cargo_at_second = v["dwt"] - v["tpc"] * 100 * max(0, v["design_draft_m"] - d2) - v["constants_t"]
    must_discharge_first = max(0.0, f1.cargo_t - cargo_at_second)
    return {"class": cls, "total_cargo_t": round(f1.cargo_t), "discharge_at_first_t": round(must_discharge_first),
            "max_at_second_t": round(max(cargo_at_second, 0)), "extra_port_call_days": 1.5,
            "extra_cost_usd": v["port_cost_usd"] * 0.6}
