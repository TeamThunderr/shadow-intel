import asyncio
from typing import List
from shared.schemas import EntityFingerprint
from shared.logger import get_logger

logger = get_logger(__name__)

class OpenCorporatesMonitor:
    async def check_new_registrations(self, fingerprint: EntityFingerprint) -> List[dict]:
        """
        MOCK: Simulates checking OpenCorporates for new company registrations
        matching the entity's fingerprint (name, alias, or director).
        """
        logger.info(f"OpenCorporatesMonitor checking for {fingerprint.canonical_name}")
        await asyncio.sleep(1) # Simulate API latency
        
        # Mocking a hit! Let's pretend we found a new shell company registered yesterday
        # We use one of the entity's aliases if available, otherwise just use their name
        match_name = fingerprint.aliases[0] if fingerprint.aliases else fingerprint.canonical_name
        
        mock_hit = {
            "source": "OpenCorporates",
            "name": f"{match_name} Global Holdings",
            "jurisdiction": "Panama",
            "directors": [fingerprint.canonical_name],
            "registration_date": "2026-06-07"
        }
        
        return [mock_hit]


class WhoisMonitor:
    async def check_new_domains(self, fingerprint: EntityFingerprint) -> List[dict]:
        """
        MOCK: Simulates checking WHOIS databases for newly registered domains
        that look like typosquatting or alias matches.
        """
        logger.info(f"WhoisMonitor checking for {fingerprint.canonical_name}")
        await asyncio.sleep(0.5) # Simulate API latency
        
        base_name = fingerprint.canonical_name.lower().replace(" ", "")
        
        mock_hit = {
            "source": "WHOIS",
            "domains": [f"{base_name}-holdings.com", f"{base_name}global.net"],
            "registration_date": "2026-06-08",
            "registrar": "Namecheap"
        }
        
        return [mock_hit]
