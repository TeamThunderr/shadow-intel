import asyncio
from dotenv import load_dotenv
load_dotenv()

from backend.agents.money_trail import run_money_trail

fingerprint = {
    "entity_id": "test-uuid-001",
    "canonical_name": "Viktor Bout",
    "aliases": ["Viktor Anatolijevitch Bout", "Victor Bout"],
    "jurisdictions": ["RU", "ZA", "UA"],
    "known_wallet_addresses": []
}

result = asyncio.run(run_money_trail(fingerprint))

# Check exact schema
required_keys = [
    "module", "entity_id", "status",
    "processing_time_ms", "risk_score",
    "evidence", "data", "error"
]
print("=== SCHEMA CHECK ===")
for key in required_keys:
    print(f"{key}: {'[PASS]' if key in result else '[FAIL] MISSING'}")

# Check values
print("\n=== VALUES ===")
print(f"module: {result.get('module')}")
print(f"entity_id: {result.get('entity_id')}")
print(f"status: {result.get('status')}")
print(f"processing_time_ms: {result.get('processing_time_ms')}")
print(f"risk_score: {result.get('risk_score')}")
print(f"evidence items: {len(result.get('evidence', []))}")
print(f"sanctions_hits: {len(result.get('data', {}).get('sanctions_hits', []))}")
print(f"high_risk_jurisdictions: {result.get('data', {}).get('high_risk_jurisdictions')}")
print(f"error: {result.get('error')}")
