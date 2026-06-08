import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

async def test():
    wallet = "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE"
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    url = "https://api.etherscan.io/api"
    params = {
        "module": "account",
        "action": "txlist",
        "address": wallet,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "asc",
        "apikey": api_key
    }
    
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        response = await client.get(url, params=params)
        print(response.status_code)
        print(response.json())

if __name__ == "__main__":
    asyncio.run(test())
