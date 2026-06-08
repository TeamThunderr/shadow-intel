# Environment Variables Reference - Phase 2

## Quick Setup

Add these to your `.env` file in the project root directory.

## Required Variables

### Phase 2 APIs

```bash
# ─── REQUIRED: Companies House (UK) ───────────────────────────────────
COMPANIES_HOUSE_API_KEY=your_api_key_here

# Why: Enables UK company lookups, officer retrieval, PSC discovery
# Get key: https://developer.company-information.service.gov.uk/
# Free tier: 600 requests per 5 minutes
# Without this: UK companies will be skipped, other sources used
```

## Optional Variables (Public APIs)

```bash
# SEC EDGAR (US) - Public API, no key needed
# Uses: https://data.sec.gov/

# OpenOwnership (International) - Public API, no key needed
# Uses: https://register.openownership.org/api/
```

## Complete .env Template

```bash
# ═══════════════════════════════════════════════════════════════════════
# PHASE 2 - REAL DATA SOURCES
# ═══════════════════════════════════════════════════════════════════════

# Companies House (UK) - REQUIRED for UK lookups
# Get API key: https://developer.company-information.service.gov.uk/
# Free tier: 600 requests per 5 minutes
COMPANIES_HOUSE_API_KEY=your_companies_house_api_key

# SEC EDGAR (US) - Public API, no authentication required
# No action needed - automatically uses public endpoint

# OpenOwnership (International) - Public API, no authentication required  
# No action needed - automatically uses public endpoint


# ═══════════════════════════════════════════════════════════════════════
# EXISTING CONFIGURATION (from Phase 1)
# ═══════════════════════════════════════════════════════════════════════

# Azure Foundry
AZURE_FOUNDRY_ENDPOINT=your_endpoint
AZURE_FOUNDRY_API_KEY=your_api_key
AZURE_FOUNDRY_DEPLOYMENT=gpt-4o

# Fabric
FABRIC_WORKSPACE_ID=your_workspace_id
FABRIC_LAKEHOUSE_ID=your_lakehouse_id
FABRIC_CLIENT_ID=your_client_id
FABRIC_CLIENT_SECRET=your_client_secret
FABRIC_TENANT_ID=your_tenant_id

# Graph API (Microsoft)
GRAPH_CLIENT_ID=your_client_id
GRAPH_CLIENT_SECRET=your_client_secret
GRAPH_TENANT_ID=your_tenant_id
GRAPH_TEAMS_CHANNEL_ID=your_channel_id
GRAPH_TEAMS_TEAM_ID=your_team_id

# Other APIs
OPENSANCTIONS_API_KEY=your_api_key
OPENCORPORATES_API_KEY=your_api_key
OCCRP_API_KEY=your_api_key
ETHERSCAN_API_KEY=your_api_key
NEWS_API_KEY=your_api_key

# Application Settings
APP_ENV=production
APP_PORT=8000
CONFIDENCE_THRESHOLD=0.80
```

## Step-by-Step Setup

### 1. Get Companies House API Key (2 minutes)

**Steps:**
1. Go to: https://developer.company-information.service.gov.uk/
2. Click "Create an Account" in top right
3. Enter email and password
4. Verify your email address
5. Log in to your account
6. Go to "Applications" 
7. Click "Create an Application"
8. Name it "Shadow-Intel"
9. Accept terms
10. Copy your API key
11. Add to .env: `COMPANIES_HOUSE_API_KEY=your_key_here`

**Free Tier Details:**
- Cost: Free
- Requests: 600 per 5 minutes (unlimited per day)
- Features: All endpoints available
- Renewal: No

### 2. SEC EDGAR (No Setup Needed)
- Public API, no registration required
- No API key needed
- Start using immediately
- Recommendation: 1 request per second for politeness

### 3. OpenOwnership (No Setup Needed)
- Public API, no registration required
- No API key needed
- Start using immediately
- All beneficial ownership data available

## Verification

### Test Companies House

```bash
# On Linux/Mac
curl -u "YOUR_API_KEY:" https://api.company-information.service.gov.uk/search/companies?q=apple

# In PowerShell
$auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("YOUR_API_KEY:"))
Invoke-WebRequest -Uri "https://api.company-information.service.gov.uk/search/companies?q=apple" `
  -Headers @{Authorization="Basic $auth"}
```

Expected response: JSON with company list

### Test SEC EDGAR

```bash
# Works without authentication
curl https://data.sec.gov/submissions/CIK0000320193.json

# In PowerShell
Invoke-WebRequest -Uri "https://data.sec.gov/submissions/CIK0000320193.json"
```

Expected response: Apple Inc. company facts

### Test OpenOwnership

```bash
# Works without authentication
curl https://register.openownership.org/api/releases

# In PowerShell
Invoke-WebRequest -Uri "https://register.openownership.org/api/releases"
```

Expected response: JSON with beneficial ownership data

## Troubleshooting

### "No Companies House API key configured"

**Cause:** COMPANIES_HOUSE_API_KEY not set in .env

**Fix:**
1. Verify key is added to .env
2. Check for typos in key name (exact case)
3. Restart your application
4. Check logs for configuration loading

### "401 Unauthorized" from Companies House

**Cause:** Invalid API key

**Fix:**
1. Verify key is correct (copy/paste from dashboard)
2. Ensure no extra spaces before/after key
3. Regenerate key in Companies House dashboard
4. Update .env and restart

### "Rate limit exceeded"

**Cause:** Exceeded 600 requests per 5 minutes

**Fix:**
- This is automatic (service has retry logic)
- Wait 5 minutes
- Service will retry automatically
- Logs will show rate limit hits

### "Timeout errors"

**Cause:** Slow network or API response

**Fix:**
- Automatic retry logic (2 retries with backoff)
- Service falls back to mock data
- Check API status pages:
  - https://status.company-information.service.gov.uk/
  - https://www.sec.gov/edgar/
  - https://register.openownership.org/

## Security Best Practices

### 1. Protect Your API Key

❌ **DON'T:**
- Commit to version control
- Share in logs or error messages
- Store in public repositories
- Hardcode in source code

✅ **DO:**
- Keep in .env file only
- Use environment variables
- Rotate periodically (monthly recommended)
- Use in .gitignore

### 2. Example .gitignore

```bash
.env
.env.local
.env.*.local
*.key
secrets/
```

### 3. Rotate Keys

Companies House dashboard → Applications → Edit Application → Regenerate Key

Recommended: Monthly rotation

## Production Setup

### Docker/Kubernetes

```dockerfile
# In Dockerfile
ENV COMPANIES_HOUSE_API_KEY=${COMPANIES_HOUSE_API_KEY}
```

```yaml
# In docker-compose.yml
environment:
  COMPANIES_HOUSE_API_KEY: ${COMPANIES_HOUSE_API_KEY}
```

```yaml
# In Kubernetes secret
apiVersion: v1
kind: Secret
metadata:
  name: ownership-unwind-secrets
type: Opaque
stringData:
  COMPANIES_HOUSE_API_KEY: your_key_here
```

### AWS/Cloud

Use AWS Secrets Manager, Azure Key Vault, etc.

```bash
# Example: AWS Secrets Manager
aws secretsmanager create-secret --name ownership-unwind-keys \
  --secret-string '{"COMPANIES_HOUSE_API_KEY":"your_key"}'
```

## Minimal Setup

If you only want one data source:

```bash
# Minimum - Just UK companies
COMPANIES_HOUSE_API_KEY=your_api_key

# Result: UK companies enabled, US/International supported via public APIs
# Service will automatically use best source for company jurisdiction
```

## Testing Setup

```bash
# For testing/development
COMPANIES_HOUSE_API_KEY=test_api_key_123
APP_ENV=development
CONFIDENCE_THRESHOLD=0.75
```

## Monitoring

### Check API Key Status

```python
from backend.agents.ownership_unwind.sources import companies_house
from backend.shared.config import get_settings

settings = get_settings()
if settings.companies_house_api_key:
    print("✓ Companies House API key is configured")
else:
    print("✗ Companies House API key is NOT configured")
```

### Log Configuration

All Phase 2 modules log API key status:
- INFO: "Using Companies House API"
- WARNING: "No Companies House API key configured"

Check logs to verify setup.

## Summary

| Variable | Required? | Where to Get | Free Tier |
|----------|-----------|--------------|-----------|
| COMPANIES_HOUSE_API_KEY | ✅ Yes | https://developer.company-information.service.gov.uk/ | ✅ Yes (600 req/5min) |
| SEC EDGAR | ❌ No | Public API | ✅ Public |
| OpenOwnership | ❌ No | Public API | ✅ Public |

**Minimum Setup:** Add just one API key and you're ready to go!

