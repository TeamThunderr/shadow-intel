import asyncio
from fabric.pipeline import run_all_ingestion

result = asyncio.run(run_all_ingestion())
for d in result["datasets"]:
    print(f"{d['dataset']}: {d['status']} — {d.get('rows', 0)} rows")
print(f"\nTotal rows: {result['total_rows']}")
