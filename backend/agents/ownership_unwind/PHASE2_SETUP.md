# Phase 2 Setup - Real Data Source Integration

## Overview

Phase 2 of the Ownership Unwind Agent integrates real-world data sources for beneficial ownership discovery. This document provides setup instructions and API key requirements.

## Required Environment Variables

Add these to your `.env` file in the project root:

### Companies House (UK Companies)
```bash
COMPANIES_HOUSE_API_KEY=your_api_key_here
```

**Obtaining API Key:**
1. Visit: https://developer.company-information.service.gov.uk/
2. Create a free developer account
3. Generate API key (no approval needed for free tier)
4. Supports searching UK companies and retrieving beneficial ownership data

**Features:**
- Company name search
- Officer/director retrieval
- Persons of Significant Control (PSC) lookup
- Free tier: 600 requests per 5 minutes

### SEC EDGAR (US Companies)
```bash
# No API key required for SEC EDGAR
# Uses public endpoint: https://data.sec.gov/
```

**Features:**
- Company search by name
- 13D/13G beneficial ownership filing retrieval
- Full-text search
- Public access (no authentication)

**CIK Lookup:**
```bash
# Query: https://www.sec.gov/cgi-bin/browse-edgar?company=<name>&action=getcompany
# Returns CIK (Central Index Key) for company
```

### OpenOwnership Register (International)
```bash
# API key optional for public data
# Visit: https://register.openownership.org/
```

**Features:**
- International beneficial ownership records
- Company search by name
- Beneficial owner tracing
- Free tier: Public data access

**Note:** OpenOwnership API documentation: https://docs.openownership.org/register/

## Complete .env File Example

```bash
# ─── Ownership Unwind Phase 2 APIs ─────────────────────────────────────

# Companies House (UK) - Free tier available
COMPANIES_HOUSE_API_KEY=your_companies_house_api_key

# SEC EDGAR (US) - No key needed, public API
# Uses: https://data.sec.gov/

# OpenOwnership Register (International) - Public access
# Uses: https://register.openownership.org/api

# ─── Other Configuration ──────────────────────────────────────────────

# App Settings
APP_ENV=production
APP_PORT=8000
CONFIDENCE_THRESHOLD=0.80

# Azure
AZURE_FOUNDRY_ENDPOINT=your_endpoint
AZURE_FOUNDRY_API_KEY=your_key
AZURE_FOUNDRY_DEPLOYMENT=gpt-4o

# Fabric
FABRIC_WORKSPACE_ID=your_id
FABRIC_LAKEHOUSE_ID=your_id
FABRIC_CLIENT_ID=your_id
FABRIC_CLIENT_SECRET=your_secret
FABRIC_TENANT_ID=your_id

# Graph API
GRAPH_CLIENT_ID=your_id
GRAPH_CLIENT_SECRET=your_secret
GRAPH_TENANT_ID=your_id

# Other APIs
OPENSANCTIONS_API_KEY=your_key
OPENCORPORATES_API_KEY=your_key
OCCRP_API_KEY=your_key
ETHERSCAN_API_KEY=your_key
NEWS_API_KEY=your_key
```

## Using Phase 2 with Real Data

### Option 1: Use Only Real Data (Recommended)

```python
from backend.agents.ownership_unwind import OwnershipAnalysisService
from backend.agents.ownership_unwind.sources import (
    companies_house,
    sec_edgar,
    openownership
)

# Query real data sources
company_name = "Apple Inc."

# Results are partial if one source fails
ch_companies = await companies_house.search_companies(company_name)
edgar_companies = await sec_edgar.search_companies(company_name)
oo_companies = await openownership.search_companies(company_name)
```

### Option 2: Automatic Source Selection

The service automatically selects the best source based on company jurisdiction:

```python
from backend.agents.ownership_unwind.service import OwnershipUnwindAgent
from backend.shared.schemas import EntityFingerprint

agent = OwnershipUnwindAgent()

fingerprint = EntityFingerprint(
    entity_id="entity_123",
    canonical_name="Apple Inc.",
    aliases=["AAPL"],
    jurisdictions=["US"]
)

# Automatically uses best source for jurisdiction
response = await agent.run(fingerprint)
```

### Option 3: Build Graph from Specific Source

```python
from backend.agents.ownership_unwind.service import OwnershipAnalysisService

service = OwnershipAnalysisService()

# Use real data if available
response = service.analyze_with_real_data(
    entity_name="BP plc",  # UK company
    sources=["companies_house", "sec_edgar"]
)
```

## Data Source Priority Matrix

| Jurisdiction | Primary | Secondary | Tertiary |
|-------------|---------|-----------|----------|
| UK, GB | Companies House | OpenOwnership | ICIJ |
| US | SEC EDGAR | Companies House | OpenOwnership |
| International | OpenOwnership | Companies House | Local Sources |
| EU | OpenOwnership | Companies House | National Registers |
| Offshore (BVI, KY, etc) | OpenOwnership | ICIJ | Leaked Databases |

## API Rate Limits & Throttling

### Companies House
- **Free Tier**: 600 requests per 5 minutes
- **Throttling**: Built-in retry logic with exponential backoff
- **Timeout**: 10 seconds per request

### SEC EDGAR
- **Public API**: No official rate limits
- **Best Practice**: 1 request per second
- **Timeout**: 10 seconds per request

### OpenOwnership
- **Free Tier**: No official limits
- **Best Practice**: 1 request per second
- **Timeout**: 10 seconds per request

## Error Handling & Partial Results

The service is designed to return partial results when individual sources fail:

```python
# Service continues if Companies House is down
# Returns data from SEC EDGAR and OpenOwnership
response = service.analyze_with_real_data("Any Company Ltd")

# Check evidence to see which sources provided data
print(response.evidence)
# [
#   {"source": "companies_house", "entities": 0},  # Failed
#   {"source": "sec_edgar", "entities": 5},         # Success
#   {"source": "openownership", "entities": 3},     # Success
# ]
```

## Opacity Jurisdiction Detection

Phase 2 automatically flags entities in opacity/high-risk jurisdictions:

**Automatically Detected:**
- British Virgin Islands (VG)
- Cayman Islands (KY)
- Panama (PA)
- Seychelles (SC)
- Marshall Islands (MH)
- Cook Islands (CK)
- Bermuda (BM)
- Mauritius (MU)
- Singapore (SG)
- Hong Kong (HK)
- UAE (AE)

**Risk Scoring:**
- Single opacity jurisdiction: +0.30 risk
- Multiple opacity jurisdictions: +0.65 risk
- 3+ opacity jurisdictions: +0.85 risk (critical)

## Testing Phase 2

### Verify API Keys

```bash
# Test Companies House
curl -u "YOUR_API_KEY:" https://api.company-information.service.gov.uk/search/companies?q=apple

# Test SEC EDGAR
curl https://data.sec.gov/submissions/CIK0000320193.json

# Test OpenOwnership
curl https://register.openownership.org/api/releases
```

### Run Phase 2 Examples

```bash
# From project root
cd backend/agents/ownership_unwind

# Run with real data (requires API keys in .env)
python examples_phase2.py

# Run specific example
python -c "from examples_phase2 import example_real_data_companies_house; example_real_data_companies_house()"
```

## Troubleshooting

### "No Companies House API key configured"
- Add `COMPANIES_HOUSE_API_KEY` to `.env`
- Restart the application

### "Timeout on Companies House API"
- Check your internet connection
- Verify API key is valid
- Companies House API may be temporarily down
- Service will fall back to other sources

### "No results found"
- Company name may be spelled differently in source
- Try exact company registration number (for Companies House)
- Try CIK number (for SEC EDGAR)
- Try OOID (for OpenOwnership)

### Graph has 0 entities
- Company may not be registered in any available source
- Try different company name or jurisdiction
- Check error logs for source-specific failures

## Data Quality Notes

### Companies House
- **Pros**: Official UK registry, up-to-date officer lists
- **Cons**: UK-only, requires annual filings
- **Accuracy**: Very high for active companies

### SEC EDGAR
- **Pros**: Official US registry, 13D/13G beneficial ownership filings
- **Cons**: US-only, may lag real-time changes
- **Accuracy**: High for public company ownership

### OpenOwnership
- **Pros**: International, beneficial ownership focus
- **Cons**: Partial coverage, varying data quality by country
- **Accuracy**: Medium - depends on source jurisdiction

## Integration with Rest of System

Phase 2 maintains backward compatibility:

1. **Ghost Tracker Integration**
   - Receives entity fingerprint
   - Queries real sources
   - Returns risk assessment

2. **Dashboard Integration**
   - D3.js visualization shows real data
   - Risk factors include opacity jurisdiction flags
   - Evidence chain shows data sources

3. **Orchestrator Integration**
   - Runs as autonomous agent
   - Supports async execution
   - Returns standardized AgentResponse

## Future Enhancements

- ICIJ Leaks database integration
- Global Leaks database
- National company registers (50+ countries)
- Blockchain ownership lookup (ENS, UNSTOPPABLE)
- Real estate ownership (land registries)
- Cross-border beneficial owner validation
- AI-powered natural person disambiguation

## Support

For API-specific issues:
- **Companies House**: https://developer.company-information.service.gov.uk/support
- **SEC EDGAR**: https://www.sec.gov/edgar/faqs.htm
- **OpenOwnership**: https://docs.openownership.org/

For Shadow Intel issues:
- Check logs in `backend.logs/`
- Review evidence chain in responses
- Verify .env configuration
