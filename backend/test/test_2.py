from agents.money_trail import (
    detect_laundering_patterns,
    build_financial_flows,
    calculate_financial_risk_score
)

mock_hops = [
  {"hop": 1, "amount_usd": 75000,
   "date": "2024-01-01T00:00:00+00:00",
   "from_address": "0xAAA", "to_address": "0xBBB",
   "tx_hash": "0x1", "chain": "ETH"},
  {"hop": 2, "amount_usd": 30000,
   "date": "2024-01-01T12:00:00+00:00",
   "from_address": "0xBBB", "to_address": "0xCCC",
   "tx_hash": "0x2", "chain": "ETH"},
  {"hop": 3, "amount_usd": 30000,
   "date": "2024-01-02T06:00:00+00:00",
   "from_address": "0xCCC",
   "to_address": "0x3f5ce5fbfe3e9af3971dd833d26ba9b5c936f0be",
   "tx_hash": "0x3", "chain": "ETH"},
]

patterns = detect_laundering_patterns(mock_hops)
flows = build_financial_flows(mock_hops, patterns)

mock_jurisdiction = {
    "jurisdiction_risk_score": 0.65,
    "high_risk_countries": ["Russia"]
}
score = calculate_financial_risk_score(
    mock_hops, patterns, mock_jurisdiction, [{"name":"x"}]
)

print("=== PATTERN DETECTION ===")
print(f"placement_detected: {patterns['placement_detected']}")
print(f"layering_detected: {patterns['layering_detected']}")
print(f"integration_detected: {patterns['integration_detected']}")
print(f"overall_pattern: {patterns['overall_pattern']}")

print("\n=== FINANCIAL FLOWS ===")
for f in flows:
    print(f"hop {f['hop_number']}: {f['risk_flag']} — "
          f"${f['amount_usd']:,.0f}")

print(f"\n=== RISK SCORE ===")
print(f"score: {score}")
