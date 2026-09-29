"""Idle-time & deadheading manager for period (TC) tonnage and COA nominations.

For a ship on time charter serving Australia -> East Coast India, evaluates what to do with idle
windows / the ballast leg:
  1. DIRECT     - ballast straight back to the load port (reference)
  2. TRIANGULATE- backhaul East-Coast-India iron ore / pellets to China, then ballast China->Australia
  3. SHORT-RELET- relet the gap at spot (e.g. Indonesia <-> India coal round) at forecast TCE x (1-haircut)
  4. JIT-SLOW   - slow-steam to arrive just-in-time for the laycan instead of idling at anchorage
Also: laycan spacing rule to avoid bunching (queue) at the discharge port.
"""
from .config import VESSELS, ROUTES, COMMERCIAL, DISCHARGE, BACKHAUL


def _days(nm, kn):
    return nm / (kn * 24)


def options(cls, hire, tce_fcst, bunker, cargo_t, idle_days, load="HAY_POINT", disch="PARADIP",
            backhaul_rate_usd_t=None):
    v = VESSELS[cls]
    base_nm = ROUTES[load]["nm"] + DISCHARGE[disch]["offset_nm"]
    res = []
    d_direct = _days(base_nm, v["speed_ballast_kn"])
    fuel_direct = d_direct * v["fuel_ballast_tpd"]
    res.append({"option": "Direct ballast to load port", "extra_days": 0.0, "net_usd": 0.0,
                "detail": f"{base_nm:,} nm ballast, {d_direct:.1f} d"})
    # triangulation
    bh = BACKHAUL
    l_nm, b_nm = bh["PARADIP->QINGDAO_ironore"]["nm"], bh["QINGDAO->HAY_POINT"]["nm"]
    d_tri = _days(l_nm, v["speed_laden_kn"]) + _days(b_nm, v["speed_ballast_kn"]) + 6.0
    fuel_tri = _days(l_nm, v["speed_laden_kn"]) * v["fuel_laden_tpd"] + _days(b_nm, v["speed_ballast_kn"]) * v["fuel_ballast_tpd"] + 6 * v["fuel_port_tpd"]
    ore_t = cargo_t * 1.05
    if backhaul_rate_usd_t is None:  # market backhaul rate proxy: breakeven at forecast TCE, backhaul discount 25%
        backhaul_rate_usd_t = 0.75 * (tce_fcst * (_days(l_nm, v["speed_laden_kn"]) + 6) + fuel_tri * bunker * 0.5) / ore_t
    extra = d_tri - d_direct
    net = backhaul_rate_usd_t * ore_t - extra * hire - (fuel_tri - fuel_direct) * bunker - 2 * v["port_cost_usd"]
    res.append({"option": "Triangulate: iron ore/pellets Paradip->China, ballast China->Australia",
                "extra_days": round(extra, 1), "net_usd": round(net), "detail":
                f"backhaul ~${backhaul_rate_usd_t:.1f}/t x {ore_t:,.0f} t; needs {extra:.0f} extra days before next laycan"})
    # short relet of idle window
    if idle_days > 0:
        earn = idle_days * tce_fcst * (1 - COMMERCIAL["relet_haircut"])
        res.append({"option": f"Relet idle {idle_days:.0f} d at spot (e.g. Indonesia-India coal)", "extra_days": 0.0,
                    "net_usd": round(earn - idle_days * 0.0), "detail": f"forecast TCE ${tce_fcst:,.0f}/d less {COMMERCIAL['relet_haircut']:.0%} haircut"})
        # JIT slow steaming across the laden leg to absorb idle days
        d_laden = _days(base_nm, v["speed_laden_kn"])
        new_speed = max(base_nm / ((d_laden + idle_days) * 24), 9.0)        # engine/charter-party floor
        absorbed = base_nm / (new_speed * 24) - d_laden
        new_fuel = v["fuel_laden_tpd"] * (new_speed / v["speed_laden_kn"]) ** 3 * (d_laden + absorbed)
        saving = (v["fuel_laden_tpd"] * d_laden + absorbed * v["fuel_port_tpd"] - new_fuel) * bunker
        res.append({"option": f"JIT slow-steam at {new_speed:.1f} kn instead of idling", "extra_days": 0.0,
                    "net_usd": round(saving), "detail": f"absorbs {absorbed:.1f} of {idle_days:.0f} idle days; cube-law fuel saving, lower CII"})
    return sorted(res, key=lambda r: -r["net_usd"])


def laycan_spacing(cls, disch="PARADIP", cargo_t=None, buffer_days=1.0):
    """Minimum spacing between SAIL arrivals so a ship is not queued behind SAIL's own previous ship."""
    from .physics import handling_rate
    v = VESSELS[cls]
    q = cargo_t or (v["dwt"] - v["constants_t"])
    service = q / handling_rate(DISCHARGE[disch], cls) + 0.5
    return round(service + buffer_days, 1)
