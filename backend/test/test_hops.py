import asyncio
from dotenv import load_dotenv
load_dotenv()  # make sure .env is loaded

from agents.money_trail import trace_hops

result = asyncio.run(
    trace_hops("0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE")
)
print(f"Hops traced: {len(result)}")
print(result[0] if result else "No hops")
