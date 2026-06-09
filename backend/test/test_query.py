import asyncio
from fabric.pipeline import query_sanctions_by_name

result = asyncio.run(query_sanctions_by_name("Viktor Bout"))
print(f"Matches found: {len(result)}")
print(result)
