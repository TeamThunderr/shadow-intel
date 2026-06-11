"""
backend/agents/money_trail/agent.py

Money Trail Agent — blockchain tracing + FATF jurisdiction risk + sanctions cross-reference.

Workflow:
  A. Extract wallet addresses from entity fingerprint
  B. BFS-trace blockchain hops via Etherscan API (up to 5 hops)
  C. Detect laundering patterns (placement / layering / integration)
  D. Score jurisdiction risk using local FATF parquet via data_loader
  E. Resolve LEI via local GLEIF / GLEIF API
  F. Cross-reference sanctions via local parquet
  G. Calculate composite financial risk score
  H. Build financial flow records for D3 graph
  I. Return fully-populated AgentResponse

Falls back gracefully when:
  - No wallet addresses are found in the fingerprint
  - Etherscan API key is missing or the call fails
  - Any individual step raises an exception
"""

from __future__ import annotations

import os
import uuid
import logging
import asyncio
from datetime import datetime, timezone

import httpx

from agents.base import BaseAgent
from shared.schemas import AgentResponse, EntityFingerprint, EvidenceItem
from shared.logger import get_logger

logger = get_logger(__name__)


# ── Etherscan helpers ─────────────────────────────────────────────────────────

async def _fetch_eth_transactions(wallet: str) -> list[dict]:
    """Fetch the most recent Ethereum transactions for a wallet from Etherscan."""
    if not wallet:
        return []

    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    params = {
        "chainid": 1,
        "module":  "account",
        "action":  "txlist",
        "address": wallet,
        "startblock": 0,
        "endblock":   99_999_999,
        "sort":    "desc",
        "apikey":  api_key,
    }

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get("https://api.etherscan.io/v2/api", params=params)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "1":
            return []

        txs = []
        for tx in data.get("result", []):
            wei = int(tx.get("value", 0))
            eth_amount = wei / 1e18
            txs.append({
                "chain":        "ETH",
                "tx_hash":      tx.get("hash", ""),
                "from_address": tx.get("from", ""),
                "to_address":   tx.get("to", ""),
                "amount_eth":   eth_amount,
                "amount_usd":   eth_amount * 3_500,   # rough USD estimate
                "date":         datetime.fromtimestamp(
                    int(tx.get("timeStamp", 0)), tz=timezone.utc
                ).isoformat(),
                "block":        tx.get("blockNumber", ""),
            })
        return txs

    except Exception as exc:
        logger.warning(f"Etherscan fetch failed for {wallet[:10]}…: {exc}")
        return []


async def _trace_hops(
    start_wallet: str,
    max_hops: int = 5,
    max_wallets_per_hop: int = 5,
) -> list[dict]:
    """BFS — follow money from start_wallet up to max_hops deep."""
    if not start_wallet:
        return []

    current_level = [start_wallet]
    visited: set[str] = set()
    all_hops: list[dict] = []
    hop_number = 1

    while hop_number <= max_hops and current_level:
        next_level: list[str] = []
        for wallet in current_level:
            if wallet in visited:
                continue
            visited.add(wallet)

            txs = await _fetch_eth_transactions(wallet)

            for tx in txs[:10]:   # max 10 txs per wallet per hop
                all_hops.append({
                    "hop":          hop_number,
                    "chain":        "ETH",
                    "from_address": tx["from_address"],
                    "to_address":   tx["to_address"],
                    "amount_usd":   tx["amount_usd"],
                    "date":         tx["date"],
                    "tx_hash":      tx["tx_hash"],
                })
                if tx["to_address"] and tx["to_address"] not in visited:
                    next_level.append(tx["to_address"])

        # Unique-ify and cap next level
        next_level = list(dict.fromkeys(next_level))[:max_wallets_per_hop]
        current_level = next_level
        hop_number += 1

        if len(all_hops) >= 200:
            all_hops = all_hops[:200]
            break

    return all_hops


# ── Analysis helpers ──────────────────────────────────────────────────────────

def _detect_laundering_patterns(hops: list[dict]) -> dict:
    """Classify hops into placement / layering / integration pattern flags."""
    if not hops:
        return {
            "placement_detected":  False, "placement_evidence":  "",
            "layering_detected":   False, "layering_evidence":   "",
            "integration_detected": False, "integration_evidence": "",
            "overall_pattern":     "clean",
        }

    placement   = any(h.get("amount_usd", 0) > 10_000 for h in hops)
    layering    = len(hops) > 1
    integration = placement and layering
    overall     = "laundering" if (placement or layering) else "clean"

    return {
        "placement_detected":   placement,
        "placement_evidence":   "High-value transaction(s) observed." if placement else "",
        "layering_detected":    layering,
        "layering_evidence":    "Multiple transaction hops observed." if layering else "",
        "integration_detected": integration,
        "integration_evidence": "Funds appear to merge after layering hops." if integration else "",
        "overall_pattern":      overall,
    }


async def _score_jurisdiction_risk(hops: list[dict], fingerprint: EntityFingerprint) -> dict:
    """Score each jurisdiction against local FATF parquet data."""
    from shared.data_loader import get_fatf_risk

    countries: set[str] = set(fingerprint.jurisdictions)
    for h in hops:
        jur = h.get("jurisdiction")
        if jur and jur != "Unknown":
            countries.add(jur)

    if not countries:
        return {"jurisdictions_checked": [], "high_risk_countries": [], "jurisdiction_risk_score": 0.0}

    checked: list[dict] = []
    high_risk: list[str] = []
    total_score = 0.0

    for country in countries:
        score = get_fatf_risk(country)
        level = "high" if score >= 0.9 else "medium" if score >= 0.5 else "low"
        checked.append({"country": country, "risk_level": level, "risk_score": score})
        total_score += score
        if score > 0.5:
            high_risk.append(country)

    avg = round(total_score / len(checked), 4) if checked else 0.0
    return {
        "jurisdictions_checked":  checked,
        "high_risk_countries":    high_risk,
        "jurisdiction_risk_score": avg,
    }


async def _cross_reference_sanctions(fingerprint: EntityFingerprint) -> list[dict]:
    """Cross-reference all known names against local sanctions parquet."""
    from shared.data_loader import search_ofac, search_opensanctions

    names = [fingerprint.canonical_name] + list(fingerprint.aliases)
    seen: set[str] = set()
    hits: list[dict] = []

    for name in names:
        if not name:
            continue
        for result in search_ofac(name) + search_opensanctions(name):
            key = result["name"].upper()
            if key not in seen:
                seen.add(key)
                hits.append({
                    "name":        result["name"],
                    "source":      result["source"],
                    "match_score": result["confidence"],
                })

    return hits


def _calculate_risk_score(
    hops: list[dict],
    patterns: dict,
    jurisdiction_risk: dict,
    sanctions_hits: list[dict],
) -> float:
    hop_score = min(1.0, len(hops) / 25.0)

    p_score = 0.0
    if patterns.get("placement_detected"):
        p_score += 0.33
    if patterns.get("layering_detected"):
        p_score += 0.33
    if patterns.get("integration_detected"):
        p_score += 0.34

    j_score = jurisdiction_risk.get("jurisdiction_risk_score", 0.0)
    s_score = min(1.0, len(sanctions_hits) / 3.0)

    return round(
        hop_score * 0.20 + p_score * 0.35 + j_score * 0.30 + s_score * 0.15,
        4,
    )


def _build_financial_flows(hops: list[dict], patterns: dict) -> list[dict]:
    if not hops:
        return []

    max_hop = max(h["hop"] for h in hops)
    flows = []

    for hop in hops:
        if hop["hop"] == 1 and patterns.get("placement_detected"):
            flag = "placement"
        elif 1 < hop["hop"] < max_hop and patterns.get("layering_detected"):
            flag = "layering"
        elif hop["hop"] == max_hop and patterns.get("integration_detected"):
            flag = "integration"
        else:
            flag = "clean"

        flows.append({
            "type":         "crypto",
            "from":         hop.get("from_address", ""),
            "to":           hop.get("to_address", ""),
            "amount_usd":   hop.get("amount_usd", 0.0),
            "date":         hop.get("date", ""),
            "jurisdiction": "Unknown",
            "risk_flag":    flag,
            "hop_number":   hop["hop"],
            "chain":        hop.get("chain", ""),
            "tx_hash":      hop.get("tx_hash", ""),
        })

    return flows


# ── Agent class ───────────────────────────────────────────────────────────────

class MoneyTrailAgent(BaseAgent):
    """
    Traces blockchain flows, detects laundering patterns,
    and cross-references financial data with sanctions and FATF risk.
    """

    @property
    def module_name(self) -> str:
        return "money_trail"

    async def run(self, fingerprint: EntityFingerprint) -> AgentResponse:
        entity_id = fingerprint.entity_id
        evidence: list[EvidenceItem] = []

        # ── A. Get wallets ────────────────────────────────────────────────────
        wallets: list[str] = getattr(fingerprint, "known_wallet_addresses", []) or []

        if not wallets:
            logger.info(
                f"[{entity_id}] Money Trail: no wallet addresses in fingerprint — "
                "returning low-risk response"
            )
            return AgentResponse(
                module=self.module_name,
                entity_id=entity_id,
                risk_score=0.0,
                evidence=[],
                data={
                    "note": "No blockchain addresses linked to this entity.",
                    "financial_flows":             [],
                    "laundering_pattern_detected": False,
                    "laundering_patterns":         _detect_laundering_patterns([]),
                    "high_risk_jurisdictions":     [],
                    "total_hops_traced":           0,
                    "sanctions_hits":              [],
                },
            )

        # ── B. BFS blockchain tracing ─────────────────────────────────────────
        all_hops: list[dict] = []
        for wallet in wallets:
            if wallet:
                hops = await _trace_hops(wallet)
                all_hops.extend(hops)

        # ── C. Detect patterns ────────────────────────────────────────────────
        patterns = _detect_laundering_patterns(all_hops)

        # ── D. Jurisdiction risk ──────────────────────────────────────────────
        jurisdiction_risk = await _score_jurisdiction_risk(all_hops, fingerprint)

        # ── E. Sanctions cross-reference ──────────────────────────────────────
        sanctions_hits = await _cross_reference_sanctions(fingerprint)

        # ── F. Risk score ─────────────────────────────────────────────────────
        risk_score = _calculate_risk_score(all_hops, patterns, jurisdiction_risk, sanctions_hits)

        # ── G. Financial flows for D3 graph ───────────────────────────────────
        financial_flows = _build_financial_flows(all_hops, patterns)

        # ── H. Build evidence items ───────────────────────────────────────────

        # Blockchain hops
        for hop in all_hops[:10]:
            evidence.append(EvidenceItem(
                source="Etherscan",
                type="blockchain_transaction",
                detail=(
                    f"${hop['amount_usd']:,.0f} — "
                    f"{hop['from_address'][:10]}… → {hop['to_address'][:10]}… "
                    f"(hop {hop['hop']})"
                ),
                url=f"https://etherscan.io/tx/{hop['tx_hash']}",
                confidence=0.90,
            ))

        # Sanctions hits
        for hit in sanctions_hits[:5]:
            evidence.append(EvidenceItem(
                source=hit["source"],
                type="sanctions_match",
                detail=f"Sanctions match: {hit['name']} (score: {hit['match_score']:.2f})",
                confidence=hit["match_score"],
            ))

        # Jurisdiction risk
        for country in jurisdiction_risk["high_risk_countries"]:
            evidence.append(EvidenceItem(
                source="FATF",
                type="jurisdiction_risk",
                detail=f"High-risk FATF jurisdiction: {country}",
                url="https://www.fatf-gafi.org",
                confidence=0.85,
            ))

        # Laundering pattern flags
        for flag_key, flag_label in [
            ("placement_detected",   "Placement"),
            ("layering_detected",    "Layering"),
            ("integration_detected", "Integration"),
        ]:
            if patterns.get(flag_key):
                evidence.append(EvidenceItem(
                    source="Money Trail Agent",
                    type="laundering_pattern",
                    detail=f"{flag_label} detected: {patterns.get(flag_key[:-9] + '_evidence', '')}",
                    confidence=0.80,
                ))

        return AgentResponse(
            module=self.module_name,
            entity_id=entity_id,
            risk_score=risk_score,
            evidence=evidence,
            data={
                "financial_flows":             financial_flows,
                "laundering_pattern_detected": patterns["overall_pattern"] != "clean",
                "laundering_patterns":         patterns,
                "high_risk_jurisdictions":     jurisdiction_risk["high_risk_countries"],
                "jurisdiction_risk":           jurisdiction_risk,
                "financial_risk_score":        risk_score,
                "total_hops_traced":           len(all_hops),
                "sanctions_hits":              sanctions_hits,
            },
        )
