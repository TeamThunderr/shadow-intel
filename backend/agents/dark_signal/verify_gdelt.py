import os
import sys
import asyncio

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agents.dark_signal.sources.gdelt import search_gdelt

async def test_gdelt():
    print("Testing GDELT search...")
    query = "Tesla"
    
    try:
        articles = await search_gdelt(query)
        print(f"GDELT returned {len(articles)} articles for {query}.")
        for art in articles[:3]:
            print(f"  - Title: {art['title']}")
            print(f"    URL: {art['url']}")
            print(f"    Source: {art['source']} | Date: {art.get('published_date', 'unknown')} | Tone: {art['tone']}")
    except Exception as e:
        print(f"GDELT test FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    print("\nGDELT search test COMPLETED successfully!")

if __name__ == "__main__":
    asyncio.run(test_gdelt())
