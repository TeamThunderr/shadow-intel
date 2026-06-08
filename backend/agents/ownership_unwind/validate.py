"""
Ownership Unwind Agent - Validation Test
Checks code structure and imports without full dependency installation
"""

import ast
import sys
from pathlib import Path

def validate_python_syntax(filepath: str) -> tuple[bool, str]:
    """Validate Python file syntax."""
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        return True, f"✓ {Path(filepath).name}: Syntax OK"
    except SyntaxError as e:
        return False, f"✗ {Path(filepath).name}: Syntax Error - {e}"
    except Exception as e:
        return False, f"✗ {Path(filepath).name}: {e}"


def check_file_structure(base_path: str) -> dict:
    """Check if all required files exist."""
    required_files = [
        "graph_builder.py",
        "serializer.py",
        "ubo_detector.py",
        "risk.py",
        "service.py",
        "__init__.py",
        "examples.py",
        "README.md"
    ]
    
    results = {}
    for filename in required_files:
        filepath = Path(base_path) / filename
        exists = filepath.exists()
        results[filename] = exists
    
    return results


def validate_imports_structure(filepath: str) -> list[str]:
    """Extract import statements from a file."""
    imports = []
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"from {module} import {alias.name}")
    except:
        pass
    
    return imports


def check_class_definitions(filepath: str) -> list[str]:
    """Extract class and function definitions from a file."""
    classes = []
    try:
        with open(filepath, 'r') as f:
            tree = ast.parse(f.read())
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                classes.append(node.name)
    except:
        pass
    
    return classes


def main():
    """Run validation tests."""
    base_path = Path(__file__).parent
    
    print("\n" + "="*70)
    print("OWNERSHIP UNWIND AGENT - IMPLEMENTATION VALIDATION")
    print("="*70)
    
    # Check file structure
    print("\n📁 File Structure Check:")
    print("-" * 70)
    files = check_file_structure(str(base_path))
    all_exist = all(files.values())
    
    for filename, exists in files.items():
        status = "✓" if exists else "✗"
        print(f"  {status} {filename}")
    
    print(f"\n  Result: {'✓ All files present' if all_exist else '✗ Missing files'}")
    
    # Check syntax
    print("\n🔍 Syntax Validation:")
    print("-" * 70)
    
    python_files = [
        "graph_builder.py",
        "serializer.py",
        "ubo_detector.py",
        "risk.py",
        "service.py",
        "__init__.py",
    ]
    
    syntax_results = []
    for filename in python_files:
        filepath = base_path / filename
        if filepath.exists():
            valid, msg = validate_python_syntax(str(filepath))
            syntax_results.append(valid)
            print(f"  {msg}")
    
    all_valid = all(syntax_results)
    print(f"\n  Result: {'✓ All files valid' if all_valid else '✗ Syntax errors'}")
    
    # Check implementations
    print("\n📋 Implementation Coverage:")
    print("-" * 70)
    
    implementations = {
        "graph_builder.py": [
            "OwnershipEntity",
            "OwnershipLink",
            "OwnershipGraphBuilder",
            "create_mock_ownership_graph",
        ],
        "serializer.py": [
            "GraphNode",
            "GraphLink",
            "SerializedOwnershipGraph",
            "OwnershipGraphSerializer",
        ],
        "ubo_detector.py": [
            "UBOType",
            "OwnershipPath",
            "UBOEntity",
            "UBODetectionResult",
            "UBODetector",
        ],
        "risk.py": [
            "RiskFactor",
            "RiskFactorDetail",
            "OwnershipRiskProfile",
            "OwnershipRiskCalculator",
        ],
        "service.py": [
            "OwnershipUnwindResponse",
            "OwnershipUnwindAgent",
            "OwnershipAnalysisService",
        ],
    }
    
    total_classes = 0
    found_classes = 0
    
    for filename, expected_classes in implementations.items():
        filepath = base_path / filename
        if filepath.exists():
            classes = check_class_definitions(str(filepath))
            print(f"\n  {filename}:")
            for expected in expected_classes:
                total_classes += 1
                found = expected in classes
                found_classes += found
                status = "✓" if found else "✗"
                print(f"    {status} {expected}")
    
    print(f"\n  Result: {found_classes}/{total_classes} classes found")
    
    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    
    checks = {
        "File Structure": all_exist,
        "Python Syntax": all_valid,
        "Class Implementations": found_classes == total_classes,
    }
    
    for check, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {check}")
    
    all_passed = all(checks.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("✓ VALIDATION SUCCESSFUL - Implementation Ready")
        print("="*70)
        return 0
    else:
        print("✗ VALIDATION FAILED - Review errors above")
        print("="*70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
