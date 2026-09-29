"""Event intelligence: news/notice text -> structured disruption events -> impacted lanes.

Production: feeds = IMD cyclone bulletins, port-authority notices, IMF PortWatch disruption alerts,
GDELT / shipping-news RSS. Each item is converted to a typed event with Claude (structured JSON
output), then joined to the lane graph (location -> port / chokepoint -> SAIL routes & shipments).
Offline fallback: deterministic keyword extractor (used in the demo, no network needed).
The sample headlines below are SYNTHETIC examples, not real news.
"""
import json
import re

SAMPLE_FEED = [
    {"date": "2026-09-22", "source": "synthetic-demo",
     "text": "IMD: depression over north Bay of Bengal likely to intensify into cyclonic storm; "
             "north Odisha coast incl. Paradip and Dhamra may see port operations suspended for 48-72 hours."},
    {"date": "2026-09-20", "source": "synthetic-demo",
     "text": "Heavy rain in Bowen Basin disrupts coal rail to Dalrymple Bay / Hay Point; terminal queue rising."},
    {"date": "2026-09-18", "source": "synthetic-demo",
     "text": "Renewed attacks on merchant ships in the Red Sea; several bulk carriers divert via Cape of Good Hope."},
    {"date": "2026-09-15", "source": "synthetic-demo",
     "text": "China announces crude steel output curbs for Q4 in Hebei; iron ore and coking coal demand seen softer."},
    {"date": "2026-09-12", "source": "synthetic-demo",
     "text": "Hooghly draft at Haldia reduced to 7.4 m after siltation; SMP Kolkata advises lighter loading."},
]

LOC_MAP = {
    "paradip": ["PARADIP"], "dhamra": ["DHAMRA"], "odisha": ["PARADIP", "DHAMRA", "GOPALPUR"],
    "haldia": ["HALDIA"], "hooghly": ["HALDIA", "SANDHEADS"], "sandheads": ["SANDHEADS"],
    "vizag": ["VIZAG"], "visakhapatnam": ["VIZAG", "GANGAVARAM"], "gangavaram": ["GANGAVARAM"],
    "gopalpur": ["GOPALPUR"], "hay point": ["HAY_POINT"], "dalrymple": ["HAY_POINT"],
    "bowen basin": ["HAY_POINT", "GLADSTONE"], "gladstone": ["GLADSTONE"], "newcastle": ["NEWCASTLE"],
    "red sea": ["SUEZ"], "suez": ["SUEZ"], "mozambique": ["NACALA", "BEIRA"], "kalimantan": ["MUARA_BERAU", "TANJUNG_BARA"],
    "china": ["MARKET"], "hebei": ["MARKET"],
}
TYPE_RULES = [
    ("cyclone", r"cyclon|depression|storm"), ("congestion", r"queue|congest|waiting"),
    ("rail_disruption", r"rail|flood|heavy rain"), ("chokepoint", r"red sea|suez|divert"),
    ("draft_restriction", r"draft|silt|lighter loading"), ("demand_shock", r"output curbs|demand"),
    ("strike", r"strike|stoppage"), ("sanctions", r"sanction"),
]
SEVERITY = {"cyclone": 3, "chokepoint": 3, "rail_disruption": 2, "draft_restriction": 2,
            "congestion": 2, "demand_shock": 2, "strike": 2, "sanctions": 3}

EVENT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["event_type", "locations", "severity", "expected_duration_days", "freight_direction", "summary"],
    "properties": {
        "event_type": {"type": "string", "enum": [t for t, _ in TYPE_RULES] + ["other"]},
        "locations": {"type": "array", "items": {"type": "string"}},
        "severity": {"type": "integer", "minimum": 1, "maximum": 3},
        "expected_duration_days": {"type": "integer"},
        "freight_direction": {"type": "string", "enum": ["up", "down", "neutral"]},
        "summary": {"type": "string"},
    },
}


def extract_rule(item):
    t = item["text"].lower()
    etype = next((k for k, pat in TYPE_RULES if re.search(pat, t)), "other")
    locs = sorted({code for k, codes in LOC_MAP.items() if k in t for code in codes})
    dur = int(m.group(1)) // 24 if (m := re.search(r"(\d+)\s*-?\s*\d*\s*hours", t)) else 7
    direction = "down" if etype == "demand_shock" else ("up" if etype in ("chokepoint", "rail_disruption") else "neutral")
    return {"date": item["date"], "event_type": etype, "locations": locs, "severity": SEVERITY.get(etype, 1),
            "expected_duration_days": max(dur, 2), "freight_direction": direction,
            "summary": item["text"][:140], "extractor": "rule"}


def extract_llm(item):
    """Structured extraction with Claude (optional; requires `anthropic` + credentials)."""
    import anthropic
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model="claude-opus-5-5", max_tokens=2000,
        betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EVENT_SCHEMA}},
        messages=[{"role": "user", "content":
                   "Extract the maritime/port disruption event from this notice for a dry-bulk coal "
                   "chartering desk serving India's East Coast. Locations: port or strait names as written.\n\n"
                   + item["text"]}],
    )
    if resp.stop_reason == "refusal":
        return extract_rule(item)
    text = next(b.text for b in resp.content if b.type == "text")
    ev = json.loads(text)
    locs = sorted({code for k, codes in LOC_MAP.items() for l in ev["locations"] if k in l.lower() for code in codes})
    ev.update({"date": item["date"], "locations": locs or ev["locations"], "extractor": "claude"})
    return ev


def extract_all(feed=SAMPLE_FEED, use_llm=False):
    out = []
    for item in feed:
        try:
            out.append(extract_llm(item) if use_llm else extract_rule(item))
        except Exception:
            out.append(extract_rule(item))
    return out


def impacted(events, lanes):
    """lanes: list of dicts {load, disch, routing}. Returns event->lanes impact join."""
    res = []
    for e in events:
        hit = [f"{l['load']}->{l['disch']}" for l in lanes
               if set(e["locations"]) & ({l["load"], l["disch"]} | set(l.get("routing", [])))]
        if "MARKET" in e["locations"]:
            hit = ["ALL (market-wide demand)"]
        res.append({**e, "impacted_lanes": hit})
    return res
