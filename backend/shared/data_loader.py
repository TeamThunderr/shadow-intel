"""
backend/shared/data_loader.py

Loads local parquet datasets once on FastAPI startup.
All agents query these DataFrames instead of hitting network APIs for static data.
This gives instant results for OFAC, OpenSanctions, ICIJ, FATF, and GLEIF lookups.
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path
from shared.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"

# ── Global DataFrames — populated once by load_all() ─────────────────────────
_ofac_df: pd.DataFrame | None = None
_un_df: pd.DataFrame | None = None
_opensanctions_df: pd.DataFrame | None = None
_icij_entities_df: pd.DataFrame | None = None
_icij_officers_df: pd.DataFrame | None = None
_icij_relationships_df: pd.DataFrame | None = None
_fatf_df: pd.DataFrame | None = None
_gleif_df: pd.DataFrame | None = None


def load_all() -> None:
    """Call once on FastAPI startup to pre-load all parquet datasets into memory."""
    global _ofac_df, _un_df, _opensanctions_df
    global _icij_entities_df, _icij_officers_df, _icij_relationships_df
    global _fatf_df, _gleif_df

    _datasets: dict[str, str] = {
        "ofac_sdn":           "_ofac_df",
        "un_sanctions":       "_un_df",
        "opensanctions":      "_opensanctions_df",
        "icij_entities":      "_icij_entities_df",
        "icij_officers":      "_icij_officers_df",
        "icij_relationships": "_icij_relationships_df",
        "fatf_jurisdictions": "_fatf_df",
        "gleif":              "_gleif_df",
    }

    for filename, var_name in _datasets.items():
        path = DATA_DIR / f"{filename}.parquet"
        if path.exists():
            try:
                df = pd.read_parquet(path)
                globals()[var_name] = df
                logger.info(f"data_loader: loaded '{filename}' → {len(df):,} rows")
            except Exception as exc:
                logger.error(f"data_loader: failed to load '{filename}': {exc}")
        else:
            logger.warning(f"data_loader: dataset not found — {path}")


# ── Query helpers ─────────────────────────────────────────────────────────────

def _first_name_col(df: pd.DataFrame) -> str | None:
    """Return the first column whose name contains 'name' (case-insensitive)."""
    for col in df.columns:
        if "name" in col.lower():
            return col
    return None


def search_ofac(name: str, threshold: float = 0.75) -> list[dict]:
    """
    Fuzzy search the OFAC SDN list from the local parquet.
    Returns up to 10 results sorted by confidence descending.
    """
    from rapidfuzz import fuzz

    if _ofac_df is None:
        return []

    name_col = _first_name_col(_ofac_df)
    if not name_col:
        return []

    results: list[dict] = []
    name_upper = name.upper()

    for _, row in _ofac_df.iterrows():
        candidate = str(row.get(name_col, "")).upper()
        if not candidate:
            continue
        score = fuzz.token_sort_ratio(name_upper, candidate) / 100.0
        if score >= threshold:
            results.append({
                "name":       str(row.get(name_col, "")),
                "confidence": round(score, 3),
                "source":     "OFAC SDN (local)",
                "data":       {k: str(v) for k, v in row.to_dict().items()},
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:10]


def search_opensanctions(name: str, threshold: float = 0.75) -> list[dict]:
    """
    Search the local OpenSanctions parquet snapshot.
    Caps iteration at 50 000 rows for speed on large files.
    """
    from rapidfuzz import fuzz

    if _opensanctions_df is None:
        return []

    name_col = _first_name_col(_opensanctions_df)
    if not name_col:
        return []

    results: list[dict] = []
    name_upper = name.upper()

    # Cap to 50 k rows so the search stays fast (< 1 s on typical hardware)
    df_slice = _opensanctions_df.head(50_000)

    for _, row in df_slice.iterrows():
        candidate = str(row.get(name_col, "")).upper()
        if not candidate:
            continue
        score = fuzz.token_sort_ratio(name_upper, candidate) / 100.0
        if score >= threshold:
            results.append({
                "name":       str(row.get(name_col, "")),
                "confidence": round(score, 3),
                "source":     "OpenSanctions (local)",
                "data":       {k: str(v) for k, v in row.to_dict().items()},
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:10]


def search_un_sanctions(name: str, threshold: float = 0.75) -> list[dict]:
    """Search UN Sanctions from local parquet."""
    from rapidfuzz import fuzz

    if _un_df is None:
        return []

    name_col = _first_name_col(_un_df)
    if not name_col:
        return []

    results: list[dict] = []
    name_upper = name.upper()

    for _, row in _un_df.iterrows():
        candidate = str(row.get(name_col, "")).upper()
        if not candidate:
            continue
        score = fuzz.token_sort_ratio(name_upper, candidate) / 100.0
        if score >= threshold:
            results.append({
                "name":       str(row.get(name_col, "")),
                "confidence": round(score, 3),
                "source":     "UN Sanctions (local)",
                "data":       {k: str(v) for k, v in row.to_dict().items()},
            })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:10]


def search_icij(name: str, threshold: float = 0.70) -> list[dict]:
    """
    Search ICIJ Offshore Leaks (entities + officers) from local parquet.
    Returns up to 10 results.
    """
    from rapidfuzz import fuzz

    results: list[dict] = []
    name_upper = name.upper()

    for df_label, df in [("entities", _icij_entities_df), ("officers", _icij_officers_df)]:
        if df is None:
            continue
        name_col = _first_name_col(df)
        if not name_col:
            continue

        for _, row in df.iterrows():
            candidate = str(row.get(name_col, "")).upper()
            if not candidate:
                continue

            ts = fuzz.token_sort_ratio(name_upper, candidate)
            tset = fuzz.token_set_ratio(name_upper, candidate)
            pr = fuzz.partial_ratio(name_upper, candidate)
            score = (0.5 * ts + 0.3 * tset + 0.2 * pr) / 100.0

            if score >= threshold:
                node_id = str(row.get("node_id", ""))
                countries = str(row.get("countries", row.get("jurisdiction", "")))
                source_id = str(row.get("sourceID", ""))
                results.append({
                    "name":         str(row.get(name_col, "")),
                    "confidence":   round(score, 3),
                    "source":       "ICIJ Offshore Leaks",
                    "node_id":      node_id,
                    "countries":    countries,
                    "dataset":      source_id,
                    "url":          f"https://offshoreleaks.icij.org/nodes/{node_id}" if node_id else None,
                    "data":         {k: str(v) for k, v in row.to_dict().items()},
                })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:10]


def get_fatf_risk(jurisdiction_code: str) -> float:
    """
    Return FATF risk score for a jurisdiction ISO code.
    0.0 = low risk, 0.6 = grey list, 1.0 = black list.
    """
    if _fatf_df is None:
        return 0.0

    code_col = next(
        (c for c in _fatf_df.columns if "code" in c.lower() or "iso" in c.lower()),
        None,
    )
    if not code_col:
        return 0.0

    match = _fatf_df[_fatf_df[code_col].astype(str).str.upper() == jurisdiction_code.upper()]
    if match.empty:
        return 0.0

    risk_col = next(
        (c for c in _fatf_df.columns if "risk" in c.lower() or "list" in c.lower() or "status" in c.lower()),
        None,
    )
    if not risk_col:
        return 0.0

    val = str(match.iloc[0][risk_col]).lower()
    if any(k in val for k in ("black", "high", "ncct")):
        return 1.0
    if any(k in val for k in ("grey", "monitor", "enhanced")):
        return 0.6
    return 0.0


def get_dataset_counts() -> dict[str, int]:
    """Return row counts for all loaded datasets (used by /health endpoint)."""
    return {
        "ofac":           len(_ofac_df)           if _ofac_df           is not None else 0,
        "un_sanctions":   len(_un_df)             if _un_df             is not None else 0,
        "opensanctions":  len(_opensanctions_df)  if _opensanctions_df  is not None else 0,
        "icij_entities":  len(_icij_entities_df)  if _icij_entities_df  is not None else 0,
        "icij_officers":  len(_icij_officers_df)  if _icij_officers_df  is not None else 0,
        "fatf":           len(_fatf_df)           if _fatf_df           is not None else 0,
        "gleif":          len(_gleif_df)           if _gleif_df          is not None else 0,
    }
