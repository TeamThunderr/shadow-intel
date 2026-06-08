import os
import sys
import asyncio

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fabric.pipeline import query_icij_by_name

async def test_icij():
    print("Testing query_icij_by_name fuzzy matching...")
    test_cases = ["Shell", "Apple", "Tesla", "Gazprom", "Berkshire Hathaway"]
    
    for case in test_cases:
        print(f"\nQuery: {case}")
        try:
            results = await query_icij_by_name(case, threshold=70.0)
            print(f"  Matches found: {len(results)}")
            for r in results[:3]:
                print(f"    - Name: {r['name']} | Score: {r['match_score']:.3f} | Dataset: {r['dataset']} | Source: {r['source']}")
        except Exception as e:
            print(f"  FAILED to query for {case}: {e}")
            sys.exit(1)
            
    print("\nICIJ Search test COMPLETED successfully!")

if __name__ == "__main__":
    asyncio.run(test_icij())
