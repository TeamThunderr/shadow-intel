import os
import sys
import pandas as pd
from pathlib import Path
from rapidfuzz import fuzz

# Ensure backend root is in sys.path
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from fabric.pipeline import LOCAL_DATA_DIR, load_local, normalize_entity_name

def verify_all():
    print("================================================================================")
    print("PARQUET FILE INTEGRITY & RESOLUTION VERIFICATION")
    print("================================================================================")
    
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"LOCAL_DATA_DIR configured in pipeline.py: {LOCAL_DATA_DIR}")
    print(f"LOCAL_DATA_DIR absolute path: {os.path.abspath(LOCAL_DATA_DIR)}")
    print(f"LOCAL_DATA_DIR exists: {os.path.exists(LOCAL_DATA_DIR)}")
    
    datasets = ["icij_entities", "icij_officers", "icij_relationships"]
    
    for ds in datasets:
        path = Path(LOCAL_DATA_DIR) / f"{ds}.parquet"
        print(f"\nDataset: {ds}")
        print(f"  Expected path: {path}")
        print(f"  Absolute path: {path.absolute()}")
        print(f"  File exists: {path.exists()}")
        
        if path.exists():
            size_bytes = path.stat().st_size
            print(f"  File size: {size_bytes} bytes")
            try:
                df = pd.read_parquet(path)
                print(f"  Row count: {len(df)}")
                print(f"  Columns: {list(df.columns)}")
                
                name_col = 'name' if 'name' in df.columns else None
                if name_col:
                    print(f"  First 20 names inside {ds}:")
                    for i, val in enumerate(df[name_col].head(20)):
                        print(f"    {i+1:2d}. {val} (normalized: {normalize_entity_name(str(val))})")
                else:
                    print("  No 'name' column found.")
            except Exception as e:
                print(f"  Error reading file: {e}")
        else:
            print("  [WARNING] Parquet file does not exist at this path!")
            
    # Fuzzy score breakdown for Apple
    print("\n================================================================================")
    print("FUZZY SCORE BREAKDOWN FOR QUERY 'Apple'")
    print("================================================================================")
    
    # Let's try loading the dataset using standard absolute path relative to backend root
    alt_data_dir = Path(backend_root) / "data"
    print(f"Alternative Data Directory (relative to script): {alt_data_dir}")
    
    entity_path = alt_data_dir / "icij_entities.parquet"
    if entity_path.exists():
        df = pd.read_parquet(entity_path)
        query = "Apple"
        query_norm = normalize_entity_name(query)
        print(f"Query: '{query}' -> Normalized: '{query_norm}'")
        
        for _, row in df.iterrows():
            row_name = str(row.get('name', ''))
            row_norm = normalize_entity_name(row_name)
            
            token_sort = fuzz.token_sort_ratio(query_norm, row_norm)
            token_set = fuzz.token_set_ratio(query_norm, row_norm)
            partial = fuzz.partial_ratio(query_norm, row_norm)
            confidence = 0.5 * token_sort + 0.3 * token_set + 0.2 * partial
            
            print(f"\nCandidate: '{row_name}' -> Normalized: '{row_norm}'")
            print(f"  fuzz.token_sort_ratio: {token_sort}")
            print(f"  fuzz.token_set_ratio: {token_set}")
            print(f"  fuzz.partial_ratio: {partial}")
            print(f"  Weighted Confidence Score: {confidence:.2f}")
    else:
        print("Alternative entities Parquet file does not exist!")

if __name__ == "__main__":
    verify_all()
