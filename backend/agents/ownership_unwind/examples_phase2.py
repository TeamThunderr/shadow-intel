"""
Phase 2 Examples - Real Data Source Integration

Demonstrates how to use the Ownership Unwind Agent with real data sources:
- Companies House (UK companies)
- SEC EDGAR (US companies)
- OpenOwnership (International)

Requirements:
- Set COMPANIES_HOUSE_API_KEY in .env for UK company lookups
- SEC EDGAR requires no API key
- OpenOwnership is public

Run this script: python examples_phase2.py
"""

import asyncio
import sys
import os
from typing import List, Dict, Any

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents.ownership_unwind.sources import (
    companies_house,
    sec_edgar,
    openownership,
)
from agents.ownership_unwind.service import OwnershipAnalysisService
from shared.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Example 1: Companies House - UK Company Search
# ──────────────────────────────────────────────────────────────────────────────

async def example_companies_house_search():
    """
    Search for a UK company in Companies House and retrieve ownership details.
    
    This example demonstrates:
    - Company search by name
    - Officer/director retrieval
    - PSC (Person of Significant Control) lookup
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Companies House - UK Company Search & Officers")
    print("=" * 70)
    
    company_name = "Unilever"  # Large UK company
    
    # Step 1: Search for company
    print(f"\n📍 Searching Companies House for: {company_name}")
    companies = await companies_house.search_companies(company_name, limit=3)
    
    if not companies:
        print("❌ No companies found - ensure COMPANIES_HOUSE_API_KEY is set in .env")
        return
    
    print(f"✓ Found {len(companies)} companies:")
    for company in companies:
        print(f"  - {company['name']} (Number: {company['company_number']})")
    
    # Step 2: Get details for first company
    company = companies[0]
    company_number = company["company_number"]
    
    # Get officers
    print(f"\n👥 Fetching officers for {company['name']}...")
    officers = await companies_house.get_officers(company_number)
    
    print(f"✓ Found {len(officers)} active officers:")
    for officer in officers[:5]:  # Show first 5
        print(f"  - {officer['name']} ({officer['role']}) - Appointed: {officer['appointed_on']}")
    
    # Get PSCs (Persons of Significant Control)
    print(f"\n🔐 Fetching Persons of Significant Control (PSC)...")
    pscs = await companies_house.get_persons_of_significant_control(company_number)
    
    print(f"✓ Found {len(pscs)} active PSCs:")
    for psc in pscs[:5]:  # Show first 5
        ownership = psc.get("ownership_percentage")
        ownership_str = f" - Ownership: {ownership}%" if ownership else ""
        print(f"  - {psc['name']} ({psc['type']}){ownership_str}")
    
    # Step 3: Get shareholders
    print(f"\n💼 Fetching shareholders...")
    shareholders = await companies_house.get_shareholders(company_number)
    print(f"✓ Found {len(shareholders)} total shareholders/officers")
    
    return company, officers, pscs


# ──────────────────────────────────────────────────────────────────────────────
# Example 2: SEC EDGAR - US Company Beneficial Ownership
# ──────────────────────────────────────────────────────────────────────────────

async def example_sec_edgar_beneficial_owners():
    """
    Search for a US company in SEC EDGAR and retrieve beneficial owner filings.
    
    This example demonstrates:
    - Company search in SEC EDGAR
    - Schedule 13D filing retrieval (acquisitions, control changes)
    - Schedule 13G filing retrieval (passive investments)
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: SEC EDGAR - US Company & Beneficial Ownership Filings")
    print("=" * 70)
    
    company_name = input("Enter company name: ").strip()
    if not company_name:
        company_name = "Apple"
    
    # Step 1: Search for company
    print(f"\n🔍 Searching SEC EDGAR for: {company_name}")
    companies = await sec_edgar.search_companies(company_name, limit=3)
    
    if not companies:
        print("No matching company found")
        return None, [], []
        
    cik = companies[0]["cik"]
    resolved_name = companies[0]["name"]
    print(f"✓ Company search results: found {resolved_name} (CIK: {cik})")
    
    logger.info(f"Searching SEC EDGAR for: {company_name}")
    logger.info(f"Resolved CIK: {cik}")
    
    # Step 2: Fetch filings
    print(f"\n📋 Fetching SEC filings for CIK {cik}...")
    filings = await sec_edgar.search_company_filings(
        cik,
        form_types=["13D", "13G", "10-K"],
        limit=5
    )
    
    print(f"✓ Found {len(filings)} filings:")
    for filing in filings[:3]:
        print(f"  - {filing['form_type']} (Filed: {filing['filing_date']})")
        print(f"    Accession: {filing['accession_number']}")
    
    # Step 3: Get beneficial owners from 13D filings
    print(f"\n🏢 Extracting beneficial owners from Schedule 13D filings...")
    owners_13d = await sec_edgar.get_beneficial_owners_13d(cik)
    print(f"✓ Found {len(owners_13d)} beneficial owners in 13D filings")
    
    # Step 4: Get beneficial owners from 13G filings
    print(f"\n🏦 Extracting beneficial owners from Schedule 13G filings...")
    owners_13g = await sec_edgar.get_beneficial_owners_13g(cik)
    print(f"✓ Found {len(owners_13g)} beneficial owners in 13G filings")
    
    # Step 5: Get company facts
    print(f"\n📊 Fetching company facts and financials...")
    facts = await sec_edgar.get_company_facts(cik)
    if facts:
        print(f"✓ Retrieved company facts (entity info, CIK, tickers)")
    
    return filings, owners_13d, owners_13g


# ──────────────────────────────────────────────────────────────────────────────
# Example 3: OpenOwnership - International Beneficial Owners
# ──────────────────────────────────────────────────────────────────────────────

async def example_openownership_search():
    """
    Search OpenOwnership Register for international beneficial ownership data.
    
    This example demonstrates:
    - International company search
    - Beneficial owner traversal
    - Ownership chain tracing
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: OpenOwnership - International Beneficial Ownership")
    print("=" * 70)
    
    company_name = "Gazprom"  # International company
    
    # Step 1: Search companies
    print(f"\n🌍 Searching OpenOwnership Register for: {company_name}")
    companies = await openownership.search_companies(company_name, limit=5)
    
    if not companies:
        print("❌ No companies found in OpenOwnership Register")
        return
    
    print(f"✓ Found {len(companies)} companies:")
    for company in companies[:3]:
        print(f"  - {company['name']} (ID: {company['id']}) - {company['country']}")
    
    # Step 2: Get beneficial owners for first company
    company = companies[0]
    company_id = company["id"]
    
    print(f"\n👤 Fetching beneficial owners for {company['name']}...")
    owners = await openownership.get_beneficial_owners(company_id)
    
    print(f"✓ Found {len(owners)} beneficial owners:")
    for owner in owners[:5]:
        print(f"  - {owner['name']} ({owner['type']})")
        if owner.get("ownership_percentage"):
            print(f"    Ownership: {owner['ownership_percentage']}%")
    
    # Step 3: Trace ownership chain
    print(f"\n🔗 Tracing ownership chain (up to 5 levels deep)...")
    chains = await openownership.get_ownership_chain(company_id, max_depth=5)
    
    print(f"✓ Traced {len(chains)} ownership paths:")
    for i, chain in enumerate(chains[:3], 1):
        chain_str = " → ".join([e.get("name", "Unknown") for e in chain])
        print(f"  Path {i}: {chain_str}")
    
    return companies, owners, chains


# ──────────────────────────────────────────────────────────────────────────────
# Example 4: Multi-Source Analysis
# ──────────────────────────────────────────────────────────────────────────────

async def example_multi_source_analysis():
    """
    Demonstrate querying multiple sources for a single company.
    
    Shows how to handle:
    - Partial results when one source fails
    - Deduplication of results across sources
    - Confidence scoring based on multiple sources
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Multi-Source Analysis Pipeline")
    print("=" * 70)
    
    company_name = "Shell"  # Company present in multiple sources
    
    print(f"\n🔍 Searching for {company_name} across all sources...")
    
    # Query all sources in parallel
    ch_task = companies_house.search_companies(company_name, limit=3)
    edgar_task = sec_edgar.search_companies(company_name, limit=3)
    oo_task = openownership.search_companies(company_name, limit=3)
    
    ch_results = await ch_task
    edgar_results = await edgar_task
    oo_results = await oo_task
    
    # Aggregate results
    total_found = {
        "Companies House": len(ch_results),
        "SEC EDGAR": len(edgar_results),
        "OpenOwnership": len(oo_results),
    }
    
    print("\n📊 Results by Source:")
    for source, count in total_found.items():
        status = "✓" if count > 0 else "✗"
        print(f"  {status} {source}: {count} results")
    
    # Show aggregated data
    if ch_results:
        print(f"\n🇬🇧 Companies House Results:")
        for r in ch_results[:2]:
            print(f"  - {r['name']} (GB)")
    
    if edgar_results:
        print(f"\n🇺🇸 SEC EDGAR Results:")
        for r in edgar_results[:2]:
            print(f"  - {r['name']} (US)")
    
    if oo_results:
        print(f"\n🌍 OpenOwnership Results:")
        for r in oo_results[:2]:
            print(f"  - {r['name']} ({r['country']})")
    
    return total_found


# ──────────────────────────────────────────────────────────────────────────────
# Example 5: Build Ownership Graph from Real Data
# ──────────────────────────────────────────────────────────────────────────────

async def example_build_graph_real_data():
    """
    Build complete ownership graph from real data and analyze.
    
    Demonstrates:
    - Graph construction from API results
    - UBO detection on real data
    - Risk scoring with real ownership structures
    - Opacity jurisdiction detection
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Build & Analyze Real Ownership Graph")
    print("=" * 70)
    
    from agents.ownership_unwind.service import OwnershipAnalysisService
    
    service = OwnershipAnalysisService()
    
    company_name = input("Enter company name: ").strip()
    if not company_name:
        company_name = "Apple Inc."
    
    print(f"\n🏗️  Building ownership graph for: {company_name}")
    print("   Sources: Companies House, SEC EDGAR, OpenOwnership")
    
    response = await service.analyze_with_real_data(
        entity_name=company_name,
        sources=["companies_house", "sec_edgar", "openownership"]
    )
    
    print(f"✓ Analysis complete!")
    print(f"  Entities count: {response.entities_count}")
    print(f"  Relationships count: {response.relationships_count}")
    print(f"  Complexity level: {response.complexity_level}")
    print(f"  Max chain depth: {response.max_chain_depth}")
    print(f"  Ownership risk score: {response.ownership_risk_score:.2f} ({response.risk_level})")
    
    print(f"\n👥 Extracted UBOs:")
    if response.ultimate_beneficial_owners:
        for ubo in response.ultimate_beneficial_owners:
            print(f"  - {ubo.entity_name} ({ubo.entity_type}) - Effective Ownership: {ubo.effective_ownership_percentage:.1f}%")
            print(f"    Source: {ubo.source_system} ({ubo.source_reference})")
    else:
        print("  None found")
        
    print(f"\n🔎 Discovered Evidence:")
    if response.evidence:
        for ev in response.evidence[:10]:  # Show first 10
            print(f"  - [{ev.get('source')}] {ev.get('type')}: {ev.get('detail')}")
            if ev.get('url'):
                print(f"    URL: {ev.get('url')}")
    else:
        print("  None generated")


# ──────────────────────────────────────────────────────────────────────────────
# Main: Run all examples
# ──────────────────────────────────────────────────────────────────────────────

async def run_all_phase2_examples():
    """Run all Phase 2 examples."""
    
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "  OWNERSHIP UNWIND AGENT - PHASE 2 EXAMPLES".center(68) + "█")
    print("█" + "  Real Data Source Integration".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    print("\n⚠️  SETUP REQUIRED:")
    print("  1. Ensure COMPANIES_HOUSE_API_KEY is set in .env")
    print("  2. SEC EDGAR requires no API key (public)")
    print("  3. OpenOwnership is public access")
    print("\n  See PHASE2_SETUP.md for detailed instructions")
    
    try:
        # Example 1: Companies House
        print("\n\n[1/5] Running Companies House example...")
        company_data = await example_companies_house_search()
        
        # Example 2: SEC EDGAR
        print("\n\n[2/5] Running SEC EDGAR example...")
        edgar_data = await example_sec_edgar_beneficial_owners()
        
        # Example 3: OpenOwnership
        print("\n\n[3/5] Running OpenOwnership example...")
        oo_data = await example_openownership_search()
        
        # Example 4: Multi-source
        print("\n\n[4/5] Running multi-source analysis...")
        multi_data = await example_multi_source_analysis()
        
        # Example 5: Graph building
        print("\n\n[5/5] Running graph building example...")
        await example_build_graph_real_data()
        
        print("\n" + "=" * 70)
        print("✅ ALL PHASE 2 EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
        print("\n📚 Next Steps:")
        print("  1. Review PHASE2_SETUP.md for API configuration")
        print("  2. Add required API keys to .env")
        print("  3. Integrate with orchestrator for full pipeline")
        print("  4. Deploy to production")
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_phase2_examples())
