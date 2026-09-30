"""Market-data ingestion: validate an uploaded weekly CSV and turn it into the pipeline's DataFrame.

CSV format (weekly rows, one per week; download a filled example from GET /api/data/template):
    date, tce_Handysize, tce_Supramax, tce_Panamax, tce_Capesize          <- REQUIRED ($/day)
    bunker_usd_t, coal_usd_t, china_pmi, ballast_cape, ballast_pmx,       <- optional drivers
    wait_PARADIP, wait_DHAMRA, ... (any East-Coast port code)             <- optional waiting days
Any optional column that is missing is filled from the synthetic proxy world on the same dates,
and the fill is reported (and shown in the UI data label) so nobody mistakes proxy for real data.
"""
import hashlib
import io
import os
from pathlib import Path

import numpy as np
import pandas as pd

from .config import CLASSES, DISCHARGE, ROOT
from .synth import generate, BETA

DATA_DIR = Path(os.environ.get("FREIGHTSAARTHI_DATA", ROOT / "data"))   # env override used by tests
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD = DATA_DIR / "uploaded_market.csv"
REQUIRED = [f"tce_{c}" for c in CLASSES]
OPTIONAL = ["bunker_usd_t", "coal_usd_t", "china_pmi", "ballast_cape", "ballast_pmx"] + [f"wait_{p}" for p in DISCHARGE]
MIN_WEEKS = 300


class DataError(ValueError):
    pass


def _parse(text):
    try:
        df = pd.read_csv(io.StringIO(text))
    except Exception as e:  # noqa
        raise DataError(f"could not parse CSV: {e}")
    df.columns = [c.strip() for c in df.columns]
    if "date" not in df.columns:
        raise DataError("missing required column 'date'")
    miss = [c for c in REQUIRED if c not in df.columns]
    if miss:
        raise DataError(f"missing required columns: {', '.join(miss)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise DataError(f"{int(df['date'].isna().sum())} rows have an unparseable date")
    keep = ["date"] + [c for c in REQUIRED + OPTIONAL if c in df.columns]
    df = df[keep].set_index("date").sort_index()
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    # weekly Friday grid, small gaps forward-filled
    df = df.resample("W-FRI").last().ffill(limit=2)
    return df


def validate(text):
    """Returns (df, report). Raises DataError with a human-readable message."""
    df = _parse(text)
    warnings = []
    if len(df) < MIN_WEEKS:
        raise DataError(f"need at least {MIN_WEEKS} weekly rows (~6 years) for walk-forward training; got {len(df)}")
    for c in REQUIRED:
        bad = int(df[c].isna().sum())
        if bad:
            raise DataError(f"{c} has {bad} missing weeks after forward-fill (max gap 2 weeks)")
        if (df[c] <= 0).any():
            raise DataError(f"{c} must be positive ($/day)")
        if df[c].median() < 1000 or df[c].median() > 200000:
            warnings.append(f"{c} median {df[c].median():,.0f} looks unusual for $/day")
    provided = [c for c in OPTIONAL if c in df.columns]
    filled = [c for c in OPTIONAL if c not in df.columns]
    report = {"rows": len(df), "start": str(df.index[0].date()), "end": str(df.index[-1].date()),
              "required_ok": REQUIRED, "provided_optional": provided, "filled_from_proxy": filled, "warnings": warnings,
              "sha1": hashlib.sha1(text.encode()).hexdigest()[:10]}
    return df, report


def save(text):
    df, report = validate(text)
    UPLOAD.write_text(text, encoding="utf-8")
    return report


def status():
    if not UPLOAD.exists():
        return {"uploaded": False}
    try:
        _, rep = validate(UPLOAD.read_text(encoding="utf-8"))
        return {"uploaded": True, **rep}
    except DataError as e:
        return {"uploaded": True, "error": str(e)}


def reset():
    if UPLOAD.exists():
        UPLOAD.unlink()


def load_uploaded():
    """DataFrame + meta in the same shape as synth.generate(), plus a provenance dict."""
    text = UPLOAD.read_text(encoding="utf-8")
    df, rep = validate(text)
    proxy, _ = generate("structured", start=str(df.index[0].date()), end=str(df.index[-1].date()))
    proxy = proxy.reindex(df.index, method="nearest")
    for c in rep["filled_from_proxy"]:
        df[c] = proxy[c].values
    for c in OPTIONAL:
        df[c] = df[c].interpolate().bfill().ffill()
    df["woy"] = df.index.isocalendar().week.values.astype(int)
    df["regime"] = 0
    # market consensus forward: long-run mean + AR(1) persistence estimated from the uploaded Capesize series
    mu = {c: float(np.log(df[f"tce_{c}"]).mean()) for c in CLASSES}
    dev = np.log(df["tce_Capesize"]) - mu["Capesize"]
    phi = float(np.clip(dev.autocorr(1), 0.90, 0.995))
    meta = {"world": "uploaded", "phi_mkt": phi, "season_known": True, "mu": mu, "beta": BETA}
    return df, meta, rep


def template_csv(weeks=340):
    """A complete example CSV (synthetic values) in the exact upload format."""
    df, _ = generate("structured")
    cols = REQUIRED + OPTIONAL
    out = df[cols].iloc[-weeks:].copy().round(2)
    out.index.name = "date"
    return out.to_csv(date_format="%Y-%m-%d")


def windows(df):
    """Train / validation / test split for an arbitrary history (fractions of the length)."""
    n = len(df)
    idx = df.index
    fc_start = idx[int(n * 0.35)]
    val = (str(idx[int(n * 0.35) + 20].date()), str(idx[int(n * 0.58)].date()))
    test = (str(idx[int(n * 0.58) + 1].date()), str(idx[n - 30].date()))
    return str(fc_start.date()), val, test
