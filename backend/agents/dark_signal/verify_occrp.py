import os
import sys
import asyncio

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.dark_signal.sources.occrp import search_occrp

async def test_occrp():
    print("Testing OCCRP Aleph search...")
    query = "Tesla"
    
    try:
        results = await search_occrp(query)
        print(f"OCCRP returned {len(results)} results for {query}.")
        for res in results[:3]:
            print(f"  - Entity: {res.get('entity')}")
            print(f"    Title: {res.get('title')}")
            print(f"    URL: {res.get('url')}")
            print(f"    Country: {res.get('country')} | Summary: {res.get('summary')}")
    except Exception as e:
        print(f"OCCRP test FAILED: {e}")
        sys.exit(1)
        
    print("\nOCCRP search test COMPLETED successfully!")

if __name__ == "__main__":
    asyncio.run(test_occrp())
