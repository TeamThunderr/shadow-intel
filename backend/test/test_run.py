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

async def main():
    result = await run_money_trail(fingerprint)
    print(f"Status: {result['status']}")
    print(f"Risk score: {result['risk_score']}")
    print(f"Evidence items: {len(result['evidence'])}")
    print(f"Sanctions hits: {len(result['data']['sanctions_hits'])}")

if __name__ == "__main__":
    asyncio.run(main())
