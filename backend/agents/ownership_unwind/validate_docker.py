import sys
import os
import asyncio

# Setup PYTHONPATH root
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from agents.ownership_unwind.service import OwnershipAnalysisService

async def main():
    print("================================================================================")
    print("OWNERSHIP UNWIND AGENT - DOCKER VALIDATION RUN")
    print("================================================================================")
    
    # Allow dynamic input from command line arguments
    company_name = sys.argv[1] if len(sys.argv) > 1 else "Apple"
    print(f"Executing real lookup for company: {company_name}")
    
    service = OwnershipAnalysisService()
    
    try:
        response = await service.analyze_with_real_data(
            entity_name=company_name,
            sources=["companies_house", "sec_edgar", "openownership"]
        )
        
        print("\nValidation Results:")
        print(f"  Entities count: {response.entities_count}")
        print(f"  Relationships count: {response.relationships_count}")
        print(f"  Complexity level: {response.complexity_level}")
        print(f"  Max chain depth: {response.max_chain_depth}")
        print(f"  Risk score: {response.ownership_risk_score:.2f} ({response.risk_level})")
        print(f"  UBO count: {len(response.ultimate_beneficial_owners)}")
        print(f"  Evidence count: {len(response.evidence)}")
        
        # Verify response schema properties
        assert hasattr(response, "ownership_graph"), "Response missing 'ownership_graph'"
        assert hasattr(response, "ultimate_beneficial_owners"), "Response missing 'ultimate_beneficial_owners'"
        assert hasattr(response, "evidence"), "Response missing 'evidence'"
        
        # Check that we did not generate any mock files or mock indicators
        # Verify that UBOs and evidence items have real data references
        for ubo in response.ultimate_beneficial_owners:
            assert "mock" not in str(ubo.source_system).lower(), "Found mock UBO system reference!"
            print(f"    - UBO: {ubo.entity_name} ({ubo.effective_ownership_percentage}%) via {ubo.source_system}")
            
        print("\n================================================================================")
        print("DOCKER VALIDATION RUN: PASS")
        print("================================================================================")
        sys.exit(0)
    except AssertionError as ae:
        print(f"\nAssertion failed: {ae}")
        print("\n================================================================================")
        print("DOCKER VALIDATION RUN: FAIL")
        print("================================================================================")
        sys.exit(1)
    except Exception as e:
        print(f"\nExecution error: {e}")
        import traceback
        traceback.print_exc()
        print("\n================================================================================")
        print("DOCKER VALIDATION RUN: FAIL")
        print("================================================================================")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
