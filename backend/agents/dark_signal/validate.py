import os
import sys
import asyncio
from pathlib import Path

# Ensure backend root is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

def check_imports():
    print("[1] Verifying library imports...")
    required_libraries = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pydantic", "pydantic"),
        ("pandas", "pandas"),
        ("rapidfuzz", "rapidfuzz"),
        ("pyarrow", "pyarrow"),
        ("lxml", "lxml"),
        ("bs4", "beautifulsoup4"),
        ("pycountry", "pycountry"),
        ("httpx", "httpx")
    ]
    
    all_ok = True
    for lib, pkg_name in required_libraries:
        try:
            __import__(lib)
            print(f"  [OK] {pkg_name} is installed and importable.")
        except ImportError as e:
            print(f"  [FAIL] {pkg_name} is NOT importable: {e}")
            all_ok = False
            
    if not all_ok:
        print("Dependency verification FAILED!")
        sys.exit(1)
    print("All required libraries are importable.\n")


def check_local_data():
    print("[2] Verifying local Parquet data files...")
    # Target path relative to backend root
    root_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    data_dir = root_dir / "data"
    
    required_files = [
        "icij_entities.parquet",
        "icij_officers.parquet",
        "icij_relationships.parquet"
    ]
    
    all_ok = True
    for file_name in required_files:
        file_path = data_dir / file_name
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  [OK] {file_name} exists ({size_mb:.2f} MB).")
        else:
            print(f"  [FAIL] {file_name} is MISSING at {file_path}.")
            all_ok = False
            
    if not all_ok:
        print("Data files check FAILED!")
        sys.exit(1)
    print("All required Parquet data files are present.\n")


async def check_source_queries():
    print("[3] Testing basic source query integration...")
    
    from fabric.pipeline import query_icij_by_name
    from agents.dark_signal.sources.gdelt import search_gdelt
    from agents.dark_signal.sources.occrp import search_occrp
    
    # Test ICIJ
    print("  Testing ICIJ query for 'Tesla'...")
    try:
        icij_results = await query_icij_by_name("Tesla", threshold=70.0)
        print(f"    [OK] ICIJ query success. Matches found: {len(icij_results)}")
    except Exception as e:
        print(f"    [FAIL] ICIJ query error: {e}")
        sys.exit(1)
        
    # Test GDELT
    print("  Testing GDELT query for 'Tesla'...")
    try:
        gdelt_results = await search_gdelt("Tesla", days=3)
        print(f"    [OK] GDELT query success. Articles found: {len(gdelt_results)}")
    except Exception as e:
        print(f"    [FAIL] GDELT query error: {e}")
        sys.exit(1)
        
    # Test OCCRP
    print("  Testing OCCRP query for 'Tesla'...")
    try:
        occrp_results = await search_occrp("Tesla")
        print(f"    [OK] OCCRP query success (graceful if disabled). Results found: {len(occrp_results)}")
    except Exception as e:
        print(f"    [FAIL] OCCRP query error: {e}")
        sys.exit(1)
        
    print("\nSource queries verification COMPLETED successfully!")

async def main():
    check_imports()
    check_local_data()
    await check_source_queries()
    print("\nDSM baseline validation PASSED successfully!")

if __name__ == "__main__":
    asyncio.run(main())
