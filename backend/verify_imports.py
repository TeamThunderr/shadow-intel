import os
import sys

# Ensure backend root is in sys.path when running locally
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

def verify_all_imports():
    print("================================================================================")
    print("VERIFYING CANONICAL IMPORT GRAPH (OPTION B)")
    print("================================================================================")
    
    success = True
    
    try:
        import main
        print("  [OK] import main")
    except Exception as e:
        print(f"  [FAIL] import main: {e}")
        success = False

    try:
        from shared.logger import get_logger
        print("  [OK] from shared.logger import get_logger")
    except Exception as e:
        print(f"  [FAIL] from shared.logger import get_logger: {e}")
        success = False

    try:
        from shared.http_client import get_client
        print("  [OK] from shared.http_client import get_client")
    except Exception as e:
        print(f"  [FAIL] from shared.http_client import get_client: {e}")
        success = False

    try:
        from agents.dark_signal.agent import DarkSignalMonitor
        print("  [OK] from agents.dark_signal.agent import DarkSignalMonitor")
    except Exception as e:
        print(f"  [FAIL] from agents.dark_signal.agent import DarkSignalMonitor: {e}")
        success = False

    try:
        from agents.ownership_unwind.agent import OwnershipUnwindAgent
        print("  [OK] from agents.ownership_unwind.agent import OwnershipUnwindAgent")
    except Exception as e:
        print(f"  [FAIL] from agents.ownership_unwind.agent import OwnershipUnwindAgent: {e}")
        success = False

    try:
        from api.routes.investigate import router
        print("  [OK] from api.routes.investigate import router")
    except Exception as e:
        print(f"  [FAIL] from api.routes.investigate import router: {e}")
        success = False

    try:
        from fabric.pipeline import query_icij_by_name
        print("  [OK] from fabric.pipeline import query_icij_by_name")
    except Exception as e:
        print(f"  [FAIL] from fabric.pipeline import query_icij_by_name: {e}")
        success = False

    print("================================================================================")
    if success:
        print("IMPORT GRAPH VERIFICATION: PASS")
        sys.exit(0)
    else:
        print("IMPORT GRAPH VERIFICATION: FAIL")
        sys.exit(1)

if __name__ == "__main__":
    verify_all_imports()
