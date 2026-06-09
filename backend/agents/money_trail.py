import os
import uuid
import time
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from dateutil import parser as dateutil_parser

from fabric.pipeline import (
    query_fatf_risk,
    query_gleif_by_name,
    query_sanctions_by_name,
)

logger = logging.getLogger(__name__)

async def fetch_eth_transactions(wallet: str) -> list[dict]:
    """
    Fetch Ethereum transactions for a wallet from Etherscan.
    """
    if not wallet:
        return []
    
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": 1,
        "module": "account",
        "action": "txlist",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "1":
                return []
                
            txs = []
            for tx in data.get("result", []):
                txs.append({
                    "chain": "ETH",
                    "tx_hash": tx.get("hash", ""),
                    "from_address": tx.get("from", ""),
                    "to_address": tx.get("to", ""),
                    "amount_eth": int(tx.get("value", 0)) / 1e18,
                    "amount_usd": (int(tx.get("value", 0)) / 1e18) * 3500,
                    "date": datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=timezone.utc).isoformat(),
                    "block": tx.get("blockNumber", "")
                })
            return txs
    except Exception as e:
        logger.warning(f"Failed to fetch ETH txs for {wallet}: {e}")
        return []

async def trace_hops(start_wallet: str, max_hops: int = 5, max_wallets_per_hop: int = 5) -> list[dict]:
    """
    BFS — follow money from start_wallet up to max_hops deep.
    """
    if not start_wallet:
        return []
        
    current_level = [start_wallet]
    visited = set()
    all_hops = []
    hop_number = 1
    
    while hop_number <= max_hops and current_level:
        next_level = []
        for wallet in current_level:
            if wallet in visited:
                continue
            visited.add(wallet)
            
            txs = await fetch_eth_transactions(wallet)
            
            for tx in txs[:10]:
                all_hops.append({
                    "hop": hop_number,
                    "chain": "ETH",
                    "from_address": tx["from_address"],
                    "to_address": tx["to_address"],
                    "amount_usd": tx["amount_usd"],
                    "date": tx["date"],
                    "tx_hash": tx["tx_hash"]
                })
                
                if tx["to_address"] not in visited:
                    next_level.append(tx["to_address"])
            
            # Limit next_level to max_wallets_per_hop unique addresses
            next_level = list(dict.fromkeys(next_level))[:max_wallets_per_hop]
            
        current_level = next_level
        hop_number += 1
        
        # Cap total hops collected at 200 to avoid memory issues
        if len(all_hops) >= 200:
            all_hops = all_hops[:200]
            break
            
    return all_hops

def detect_laundering_patterns(hops: list[dict]) -> dict:
    """
    Analyze a sequence of transaction hops to identify potential laundering patterns.
    """
    placement = False
    layering = False
    integration = False
    
    if hops:
        placement = any(h.get("amount_usd", 0) > 10000 for h in hops)
        layering = len(hops) > 1
        integration = placement and layering

    overall = "laundering" if (placement or layering or integration) else "clean"
    
    return {
        "placement_detected": placement,
        "placement_evidence": "High value transactions observed." if placement else "",
        "layering_detected": layering,
        "layering_evidence": "Multiple hops observed." if layering else "",
        "integration_detected": integration,
        "integration_evidence": "Funds merged after hops." if integration else "",
        "overall_pattern": overall
    }

async def score_jurisdiction_risk(hops: list[dict], entity_fingerprint: dict) -> dict:
    try:
        countries_to_check = set()
        for j in entity_fingerprint.get("jurisdictions", []):
            countries_to_check.add(j)
            
        for h in hops:
            if h.get("jurisdiction") and h.get("jurisdiction") != "Unknown":
                countries_to_check.add(h["jurisdiction"])
                
        if not countries_to_check:
            return {
                "jurisdictions_checked": [],
                "high_risk_countries": [],
                "jurisdiction_risk_score": 0.0
            }
            
        checked = []
        high_risk = []
        total_score = 0.0
        
        for c in countries_to_check:
            res = await query_fatf_risk(c)
            checked.append({
                "country": res["country"],
                "risk_level": res["risk_level"],
                "risk_score": res["risk_score"]
            })
            total_score += res["risk_score"]
            if res["risk_score"] > 0.5:
                high_risk.append(res["country"])
                
        avg_score = round(total_score / len(checked), 4) if checked else 0.0
        
        return {
            "jurisdictions_checked": checked,
            "high_risk_countries": high_risk,
            "jurisdiction_risk_score": avg_score
        }
    except Exception as e:
        logger.error(f"Error in score_jurisdiction_risk: {e}")
        return {
            "jurisdictions_checked": [],
            "high_risk_countries": [],
            "jurisdiction_risk_score": 0.0
        }

async def resolve_lei(entity_fingerprint: dict) -> dict | None:
    try:
        names_to_try = []
        canonical = entity_fingerprint.get("canonical_name", "")
        if canonical:
            names_to_try.append(canonical)
            
        for a in entity_fingerprint.get("aliases", []):
            if a:
                names_to_try.append(a)
                
        for name in names_to_try:
            res = await query_gleif_by_name(name)
            if res is not None:
                return res
                
        return None
    except Exception as e:
        logger.error(f"Error in resolve_lei: {e}")
        return None

def calculate_financial_risk_score(
    hops: list[dict],
    patterns: dict,
    jurisdiction_risk: dict,
    sanctions_hits: list[dict]
) -> float:
    try:
        hop_score = min(1.0, len(hops) / 25)
        
        p_score = 0.0
        if patterns.get("placement_detected"):
            p_score += 0.33
        if patterns.get("layering_detected"):
            p_score += 0.33
        if patterns.get("integration_detected"):
            p_score += 0.34
            
        j_score = jurisdiction_risk.get("jurisdiction_risk_score", 0.0)
        
        s_score = min(1.0, len(sanctions_hits) / 3)
        
        risk_score = (
            hop_score * 0.20 +
            p_score * 0.35 +
            j_score * 0.30 +
            s_score * 0.15
        )
        return round(risk_score, 4)
    except Exception as e:
        logger.error(f"Error in calculate_financial_risk_score: {e}")
        return 0.0

def build_financial_flows(hops: list[dict], patterns: dict) -> list[dict]:
    try:
        if not hops:
            return []
            
        max_hop = max(h["hop"] for h in hops)
        flows = []
        
        for hop in hops:
            if hop["hop"] == 1 and patterns.get("placement_detected"):
                risk_flag = "placement"
            elif 1 < hop["hop"] < max_hop and patterns.get("layering_detected"):
                risk_flag = "layering"
            elif hop["hop"] == max_hop and patterns.get("integration_detected"):
                risk_flag = "integration"
            else:
                risk_flag = "clean"
                
            flows.append({
                "type": "crypto",
                "from": hop.get("from_address", ""),
                "to": hop.get("to_address", ""),
                "amount_usd": hop.get("amount_usd", 0.0),
                "date": hop.get("date", ""),
                "jurisdiction": "Unknown",
                "risk_flag": risk_flag,
                "hop_number": hop["hop"],
                "chain": hop.get("chain", ""),
                "tx_hash": hop.get("tx_hash", "")
            })
        return flows
    except Exception as e:
        logger.error(f"Error in build_financial_flows: {e}")
        return []

async def run_money_trail(entity_fingerprint: dict) -> dict:
    """
    Main function called by the Foundry IQ orchestrator.
    Must return the base envelope schema exactly.
    Must never raise an exception — catch everything.
    """
    start_time = time.time()
    entity_id = entity_fingerprint.get(
        "entity_id", str(uuid.uuid4())
    )
    evidence = []

    try:
        # --- A: Get known wallets ---
        wallets = entity_fingerprint.get(
            "known_wallet_addresses", []
        )

        # --- B: Trace blockchain hops ---
        all_hops = []
        for wallet in wallets:
            if wallet:
                hops = await trace_hops(wallet)
                all_hops.extend(hops)

        # --- C: Detect laundering patterns ---
        patterns = detect_laundering_patterns(all_hops)

        # --- D: Score jurisdiction risk ---
        jurisdiction_risk = await score_jurisdiction_risk(
            all_hops, entity_fingerprint
        )

        # --- E: Resolve LEI ---
        lei_record = await resolve_lei(entity_fingerprint)

        # --- F: Cross-reference sanctions ---
        canonical = entity_fingerprint.get(
            "canonical_name", ""
        )
        sanctions_hits = []
        if canonical:
            sanctions_hits = await query_sanctions_by_name(
                canonical
            )
            # Also search aliases
            for alias in entity_fingerprint.get("aliases", []):
                alias_hits = await query_sanctions_by_name(alias)
                sanctions_hits.extend(alias_hits)
            # Deduplicate by name
            seen = set()
            unique_hits = []
            for hit in sanctions_hits:
                if hit["name"] not in seen:
                    seen.add(hit["name"])
                    unique_hits.append(hit)
            sanctions_hits = unique_hits

        # --- G: Calculate risk score ---
        risk_score = calculate_financial_risk_score(
            all_hops, patterns,
            jurisdiction_risk, sanctions_hits
        )

        # --- H: Build financial flows ---
        financial_flows = build_financial_flows(
            all_hops, patterns
        )

        # --- I: Build evidence list ---

        # Blockchain hop evidence
        for hop in all_hops[:10]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": "etherscan",
                "type": "blockchain_transaction",
                "detail": (
                    f"${hop['amount_usd']:,.0f} from "
                    f"{hop['from_address'][:10]}... "
                    f"to {hop['to_address'][:10]}..."
                ),
                "url": (
                    f"https://etherscan.io/tx/"
                    f"{hop['tx_hash']}"
                ),
                "date": hop["date"],
                "confidence": 0.90
            })

        # Sanctions match evidence
        for hit in sanctions_hits[:5]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": hit["source"],
                "type": "sanctions_match",
                "detail": (
                    f"Sanctions match: {hit['name']} "
                    f"(score: {hit['match_score']:.2f})"
                ),
                "url": "",
                "date": None,
                "confidence": hit["match_score"]
            })

        # Jurisdiction risk evidence
        for country in jurisdiction_risk["high_risk_countries"]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": "fatf",
                "type": "jurisdiction_risk",
                "detail": (
                    f"High-risk jurisdiction: {country}"
                ),
                "url": "https://www.fatf-gafi.org",
                "date": None,
                "confidence": 0.85
            })

        # Laundering pattern evidence
        if patterns["placement_detected"]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": "money_trail_agent",
                "type": "laundering_pattern",
                "detail": f"Placement detected: "
                          f"{patterns['placement_evidence']}",
                "url": "",
                "date": None,
                "confidence": 0.80
            })
        if patterns["layering_detected"]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": "money_trail_agent",
                "type": "laundering_pattern",
                "detail": f"Layering detected: "
                          f"{patterns['layering_evidence']}",
                "url": "",
                "date": None,
                "confidence": 0.80
            })
        if patterns["integration_detected"]:
            evidence.append({
                "id": str(uuid.uuid4()),
                "source": "money_trail_agent",
                "type": "laundering_pattern",
                "detail": f"Integration detected: "
                          f"{patterns['integration_evidence']}",
                "url": "",
                "date": None,
                "confidence": 0.80
            })

        # --- J: Determine status ---
        has_data = (
            all_hops or
            sanctions_hits or
            jurisdiction_risk["high_risk_countries"]
        )
        status = "success" if has_data else "partial"

        # --- K: Return exact base envelope ---
        return {
            "module": "money_trail",
            "entity_id": entity_id,
            "status": status,
            "processing_time_ms": int(
                (time.time() - start_time) * 1000
            ),
            "risk_score": risk_score,
            "evidence": evidence,
            "data": {
                "financial_flows": financial_flows,
                "laundering_pattern_detected": (
                    patterns["overall_pattern"] != "clean"
                ),
                "laundering_patterns": patterns,
                "high_risk_jurisdictions": (
                    jurisdiction_risk["high_risk_countries"]
                ),
                "jurisdiction_risk": jurisdiction_risk,
                "financial_risk_score": risk_score,
                "total_hops_traced": len(all_hops),
                "lei_record": lei_record,
                "sanctions_hits": sanctions_hits,
            },
            "error": None
        }

    except Exception as e:
        logger.error(f"Money trail agent failed: {e}")
        return {
            "module": "money_trail",
            "entity_id": entity_id,
            "status": "failed",
            "processing_time_ms": int(
                (time.time() - start_time) * 1000
            ),
            "risk_score": 0.0,
            "evidence": [],
            "data": {},
            "error": str(e)
        }
