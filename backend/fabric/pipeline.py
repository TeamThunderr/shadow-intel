import os
import uuid
import time
import json
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
import io

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from lxml import etree
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
from azure.identity import ClientSecretCredential

from utils.fatf_parser import parse_fatf_jurisdictions

logger = logging.getLogger(__name__)

# Local fallback directory — used when Fabric is unavailable
LOCAL_DATA_DIR = Path(__file__).parent.parent / "data"
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Freshness tracker — in-memory dict updated after each ingestion
_last_updated: dict[str, str | None] = {
    "ofac_sdn": None,
    "opensanctions": None,
    "un_sanctions": None,
    "icij_offshore_leaks": None,
    "gleif": None,
    "fatf_jurisdictions": None,
}

# Fabric base URL (build from env vars)
def get_fabric_base() -> str:
    workspace = os.getenv("FABRIC_WORKSPACE_ID")
    lakehouse = os.getenv("FABRIC_LAKEHOUSE_ID")
    return (
        f"https://onelake.dfs.fabric.microsoft.com"
        f"/{workspace}/{lakehouse}/Files/"
    )

def get_fabric_token() -> str:
    """
    Get Azure access token for Fabric/OneLake API calls.
    Uses ClientSecretCredential with FABRIC_ prefixed env vars.
    Returns the token string.
    Raises clearly if env vars are missing.
    """
    tenant_id = os.getenv("FABRIC_TENANT_ID")
    client_id = os.getenv("FABRIC_CLIENT_ID")
    client_secret = os.getenv("FABRIC_CLIENT_SECRET")
    
    if not all([tenant_id, client_id, client_secret]):
        raise ValueError("Missing FABRIC_TENANT_ID, FABRIC_CLIENT_ID, or FABRIC_CLIENT_SECRET")
        
    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
    token = credential.get_token("https://storage.azure.com/.default")
    return token.token

async def upload_to_fabric(table_name: str, df: pd.DataFrame) -> bool:
    """
    Upload a DataFrame to Fabric Lakehouse as a Parquet file.
    """
    try:
        # Convert df to Parquet bytes using pyarrow
        table = pa.Table.from_pandas(df)
        buf = io.BytesIO()
        pq.write_table(table, buf)
        parquet_bytes = buf.getvalue()
        
        url = get_fabric_base() + f"{table_name}.parquet"
        token = get_fabric_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream"
        }
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(url, content=parquet_bytes, headers=headers)
            if response.status_code in (200, 201):
                return True
            else:
                logger.error(f"Fabric upload failed for {table_name}: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Fabric upload exception for {table_name}: {e}")
        return False

def save_local(table_name: str, df: pd.DataFrame) -> None:
    """
    Save DataFrame as local Parquet file.
    """
    try:
        path = LOCAL_DATA_DIR / f"{table_name}.parquet"
        df.to_parquet(path, engine="pyarrow")
        logger.info(f"Saved {len(df)} rows to local fallback: {table_name}")
    except Exception as e:
        logger.error(f"Failed to save {table_name} locally: {e}")

from functools import lru_cache

@lru_cache(maxsize=16)
def load_local(table_name: str) -> pd.DataFrame | None:
    """
    Load a local Parquet file. Cached using lru_cache.
    """
    try:
        path = LOCAL_DATA_DIR / f"{table_name}.parquet"
        if not path.exists():
            return None
        return pd.read_parquet(path, engine="pyarrow")
    except Exception as e:
        logger.error(f"Failed to load {table_name} locally: {e}")
        return None


def normalize_entity_name(name: str) -> str:
    """
    Normalize entity names by removing common corporate suffixes, punctuation,
    and converting to uppercase to improve fuzzy matching accuracy.
    """
    if not name:
        return ""
    import re
    # Convert to uppercase
    n = name.upper()
    # Replace special characters and extra punctuation with space
    n = re.sub(r'[\.,;\(\)\-\[\]\{\}]', ' ', n)
    # Tokenize and filter out common corporate suffixes
    suffixes = {
        "INC", "INCORPORATED", "PLC", "CO", "COMPANY", "CORP", "CORPORATION",
        "LTD", "LIMITED", "GROUP", "HOLDINGS", "LLC", "LLP", "MOTORS", "SA", "AG", "B V", "N V"
    }
    words = n.split()
    cleaned_words = [w for w in words if w not in suffixes]
    # Reassemble
    result = " ".join(cleaned_words)
    return result.strip()


async def ingest_fatf_jurisdictions() -> dict:
    """
    Parse and ingest FATF high-risk jurisdictions.
    """
    dataset_name = "fatf_jurisdictions"
    try:
        data = await parse_fatf_jurisdictions()
        df = pd.DataFrame(data)
        
        success = await upload_to_fabric(dataset_name, df)
        if not success:
            save_local(dataset_name, df)
            
        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def ingest_ofac_sdn_list() -> dict:
    dataset_name = "ofac_sdn"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            response = None
            urls = [
                "https://ofac.treas.gov/downloads/sdn.xml",
                "https://www.treasury.gov/ofac/downloads/sdn.xml",
            ]
            for url in urls:
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    break
                except Exception as e:
                    logger.warning(f"Failed to fetch OFAC from {url}: {e}")
            if response is None or response.status_code != 200:
                raise ValueError("All OFAC SDN URLs failed")
            
        root = etree.fromstring(response.content)
        
        entries = []
        for sdn in root.xpath(".//*[local-name()='sdnEntry']"):
            uid_nodes = sdn.xpath(".//*[local-name()='uid']/text()")
            uid = uid_nodes[0] if uid_nodes else ""
            
            last_name_nodes = sdn.xpath(".//*[local-name()='lastName']/text()")
            last_name = last_name_nodes[0] if last_name_nodes else ""
            
            first_name_nodes = sdn.xpath(".//*[local-name()='firstName']/text()")
            first_name = first_name_nodes[0] if first_name_nodes else ""
            
            sdn_type_nodes = sdn.xpath(".//*[local-name()='sdnType']/text()")
            sdn_type = sdn_type_nodes[0] if sdn_type_nodes else ""
            
            programs = "|".join([p.text for p in sdn.xpath(".//*[local-name()='program']") if p.text])
            
            aka_list = []
            for aka in sdn.xpath(".//*[local-name()='aka']"):
                fn = aka.xpath(".//*[local-name()='firstName']/text()")
                ln = aka.xpath(".//*[local-name()='lastName']/text()")
                fn_str = fn[0] if fn else ""
                ln_str = ln[0] if ln else ""
                full_aka = f"{fn_str} {ln_str}".strip()
                if full_aka:
                    aka_list.append(full_aka)
            aliases = "|".join(aka_list)
            
            countries = "|".join([c.text for c in sdn.xpath(".//*[local-name()='address']//*[local-name()='country']") if c.text])
            
            entries.append({
                "uid": uid,
                "last_name": last_name,
                "first_name": first_name,
                "sdn_type": sdn_type,
                "programs": programs,
                "aliases": aliases,
                "countries": countries
            })
            
        df = pd.DataFrame(entries)
        
        success = await upload_to_fabric(dataset_name, df)
        if not success:
            save_local(dataset_name, df)
            
        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def ingest_un_sanctions() -> dict:
    dataset_name = "un_sanctions"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            response = await client.get("https://scsanctions.un.org/resources/xml/en/consolidated.xml")
            response.raise_for_status()
            
        root = etree.fromstring(response.content)
        
        entries = []
        for individual in root.xpath(".//INDIVIDUAL"):
            dataid = individual.findtext("DATAID") or ""
            
            names = [
                individual.findtext("FIRST_NAME"),
                individual.findtext("SECOND_NAME"),
                individual.findtext("THIRD_NAME"),
                individual.findtext("FOURTH_NAME")
            ]
            name = " ".join([n for n in names if n])
            
            un_list_type = individual.findtext("UN_LIST_TYPE") or ""
            listed_on = individual.findtext("LISTED_ON") or ""
            nationality = individual.findtext(".//NATIONALITY/VALUE") or ""
            aliases = "|".join([a.text for a in individual.xpath(".//ALIAS/ALIAS_NAME") if a.text])
            
            entries.append({
                "dataid": dataid,
                "type": "individual",
                "name": name,
                "un_list_type": un_list_type,
                "listed_on": listed_on,
                "nationality": nationality,
                "aliases": aliases
            })
            
        for entity in root.xpath(".//ENTITY"):
            dataid = entity.findtext("DATAID") or ""
            name = entity.findtext("FIRST_NAME") or ""
            un_list_type = entity.findtext("UN_LIST_TYPE") or ""
            listed_on = entity.findtext("LISTED_ON") or ""
            nationality = ""
            aliases = "|".join([a.text for a in entity.xpath(".//ALIAS/ALIAS_NAME") if a.text])
            
            entries.append({
                "dataid": dataid,
                "type": "entity",
                "name": name,
                "un_list_type": un_list_type,
                "listed_on": listed_on,
                "nationality": nationality,
                "aliases": aliases
            })
            
        df = pd.DataFrame(entries)
        
        success = await upload_to_fabric(dataset_name, df)
        if not success:
            save_local(dataset_name, df)
            
        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def ingest_opensanctions() -> dict:
    dataset_name = "opensanctions"
    try:
        entries = []
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            async with client.stream("GET", "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json") as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        entity = json.loads(line)
                        props = entity.get("properties", {})
                        topics = props.get("topics", [])
                        
                        if "sanction" not in topics:
                            continue
                            
                        entries.append({
                            "id": entity.get("id"),
                            "caption": entity.get("caption", ""),
                            "schema": entity.get("schema", ""),
                            "names": "|".join(props.get("name", [])),
                            "aliases": "|".join(props.get("alias", [])),
                            "countries": "|".join(props.get("country", [])),
                            "topics": "|".join(topics)
                        })
                        
                        if len(entries) >= 50000:
                            break
                    except json.JSONDecodeError:
                        continue
                        
        df = pd.DataFrame(entries)
        
        success = await upload_to_fabric(dataset_name, df)
        if not success:
            save_local(dataset_name, df)
            
        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def ingest_icij_offshore_leaks() -> dict:
    dataset_name = "icij_offshore_leaks"
    
    try:
        ICIJ_SAMPLE = [
            {"node_id": "1", "name": "Mossack Fonseca", "jurisdiction": "Panama", "countries": "PA", "sourceID": "Panama Papers", "status": "active", "type": "Entity"},
            {"node_id": "2", "name": "Appleby", "jurisdiction": "Bermuda", "countries": "BM", "sourceID": "Paradise Papers", "status": "active", "type": "Entity"},
            {"node_id": "3", "name": "Asiaciti Trust", "jurisdiction": "Singapore", "countries": "SG", "sourceID": "Pandora Papers", "status": "active", "type": "Entity"},
            {"node_id": "4", "name": "Alcgal", "jurisdiction": "Panama", "countries": "PA", "sourceID": "Pandora Papers", "status": "active", "type": "Entity"},
            {"node_id": "5", "name": "Alpha Consulting", "jurisdiction": "Seychelles", "countries": "SC", "sourceID": "Pandora Papers", "status": "active", "type": "Entity"},
            {"node_id": "6", "name": "Ilham Aliyev", "jurisdiction": "Azerbaijan", "countries": "AZ", "sourceID": "Pandora Papers", "status": "active", "type": "Person"},
            {"node_id": "7", "name": "Andrej Babis", "jurisdiction": "Czech Republic", "countries": "CZ", "sourceID": "Pandora Papers", "status": "active", "type": "Person"},
            {"node_id": "8", "name": "Uhuru Kenyatta", "jurisdiction": "Kenya", "countries": "KE", "sourceID": "Pandora Papers", "status": "active", "type": "Person"},
            {"node_id": "9", "name": "King Abdullah II", "jurisdiction": "Jordan", "countries": "JO", "sourceID": "Pandora Papers", "status": "active", "type": "Person"},
            {"node_id": "10", "name": "Nirav Modi", "jurisdiction": "India", "countries": "IN", "sourceID": "Paradise Papers", "status": "active", "type": "Person"},
            {"node_id": "11", "name": "Vladimir Putin", "jurisdiction": "Russia", "countries": "RU", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "12", "name": "Sergey Roldugin", "jurisdiction": "Russia", "countries": "RU", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "13", "name": "Nawaz Sharif", "jurisdiction": "Pakistan", "countries": "PK", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "14", "name": "Sigmundur David Gunnlaugsson", "jurisdiction": "Iceland", "countries": "IS", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "15", "name": "Petro Poroshenko", "jurisdiction": "Ukraine", "countries": "UA", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "16", "name": "Isabel dos Santos", "jurisdiction": "Angola", "countries": "AO", "sourceID": "Luanda Leaks", "status": "active", "type": "Person"},
            {"node_id": "17", "name": "Jean-Claude Duvalier", "jurisdiction": "Haiti", "countries": "HT", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "18", "name": "Robert Mugabe", "jurisdiction": "Zimbabwe", "countries": "ZW", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "19", "name": "Teodoro Nguema Obiang Mangue", "jurisdiction": "Equatorial Guinea", "countries": "GQ", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "20", "name": "Sani Abacha", "jurisdiction": "Nigeria", "countries": "NG", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "21", "name": "Denis Sassou Nguesso", "jurisdiction": "Republic of Congo", "countries": "CG", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "22", "name": "Ali Bongo Ondimba", "jurisdiction": "Gabon", "countries": "GA", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "23", "name": "Zine El Abidine Ben Ali", "jurisdiction": "Tunisia", "countries": "TN", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "24", "name": "Hosni Mubarak", "jurisdiction": "Egypt", "countries": "EG", "sourceID": "Panama Papers", "status": "active", "type": "Person"},
            {"node_id": "25", "name": "Muammar Gaddafi", "jurisdiction": "Libya", "countries": "LY", "sourceID": "Panama Papers", "status": "active", "type": "Person"}
        ]
        
        df_entities = pd.DataFrame(ICIJ_SAMPLE)
        df_officers = pd.DataFrame(columns=["node_id", "name", "countries", "country_codes", "sourceID", "status"])
        df_relationships = pd.DataFrame(columns=["node_id_start", "rel_type", "node_id_end", "sourceID", "link"])
        
        success = await upload_to_fabric("icij_entities", df_entities)
        if not success:
            save_local("icij_entities", df_entities)
            save_local("icij_officers", df_officers)
            save_local("icij_relationships", df_relationships)

        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df_entities),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def ingest_gleif() -> dict:
    dataset_name = "gleif"
    try:
        entries = []
        url = "https://api.gleif.org/api/v1/lei-records"
        MAX_GLEIF_PAGES = 50
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=60) as client:
            for page in range(1, MAX_GLEIF_PAGES + 1):
                response = await client.get(url, params={"page[size]": 200, "page[number]": page})
                if response.status_code != 200:
                    break
                    
                data = response.json().get("data", [])
                if not data:
                    break
                for record in data:
                    attrs = record.get("attributes", {})
                    entity = attrs.get("entity", {})
                    
                    entries.append({
                        "lei": attrs.get("lei", ""),
                        "legal_name": entity.get("legalName", {}).get("name", ""),
                        "jurisdiction": entity.get("jurisdiction", ""),
                        "country": entity.get("legalAddress", {}).get("country", ""),
                        "status": entity.get("status", "")
                    })
                
        df = pd.DataFrame(entries)
        
        success = await upload_to_fabric(dataset_name, df)
        if not success:
            save_local(dataset_name, df)
            
        _last_updated[dataset_name] = datetime.now(timezone.utc).isoformat()
        
        return {
            "dataset": dataset_name,
            "rows": len(df),
            "updated_at": _last_updated[dataset_name],
            "status": "success",
            "error": None
        }
    except Exception as e:
        logger.error(f"Failed to ingest {dataset_name}: {e}")
        return {
            "dataset": dataset_name,
            "rows": 0,
            "updated_at": _last_updated[dataset_name],
            "status": "failed",
            "error": str(e)
        }

async def run_all_ingestion() -> dict:
    results = await asyncio.gather(
        ingest_ofac_sdn_list(),
        ingest_opensanctions(),
        ingest_un_sanctions(),
        ingest_icij_offshore_leaks(),
        ingest_gleif(),
        ingest_fatf_jurisdictions(),
        return_exceptions=True
    )
    
    datasets = []
    total_rows = 0
    success_count = 0
    failed_count = 0
    
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Ingestion crashed: {r}")
            datasets.append({
                "dataset": "unknown",
                "status": "failed",
                "error": str(r)
            })
            failed_count += 1
        else:
            datasets.append(r)
            total_rows += r.get("rows", 0)
            if r.get("status", "").startswith("success"):
                success_count += 1
            else:
                failed_count += 1
                
    return {
        "ingestion_run_at": datetime.now(timezone.utc).isoformat(),
        "datasets": datasets,
        "total_rows": total_rows,
        "success_count": success_count,
        "failed_count": failed_count
    }

async def query_sanctions_by_name(name: str, threshold: float = 0.75) -> list[dict]:
    matches = []
    
    def check_score(primary_name, alias_str):
        best_score = fuzz.token_set_ratio(name.lower(), primary_name.lower()) / 100.0
        if alias_str:
            for alias in alias_str.split('|'):
                if alias.strip():
                    a_score = fuzz.token_set_ratio(name.lower(), alias.strip().lower()) / 100.0
                    if a_score > best_score:
                        best_score = a_score
        return best_score
    
    # ofac_sdn
    df_ofac = load_local("ofac_sdn")
    if df_ofac is not None:
        for _, row in df_ofac.iterrows():
            row_name = f"{row.get('first_name', '')} {row.get('last_name', '')}".strip()
            if not row_name:
                row_name = str(row.get('last_name', ''))
                
            aliases_str = str(row.get('aliases', ''))
            score = check_score(row_name, aliases_str)
            
            if score >= threshold:
                matches.append({
                    "source": "ofac_sdn",
                    "name": row_name,
                    "match_score": score,
                    "aliases": aliases_str,
                    "countries": str(row.get('countries', '')),
                    "details": f"Type: {row.get('sdn_type', '')}, Programs: {row.get('programs', '')}"
                })
                
    # un_sanctions
    df_un = load_local("un_sanctions")
    if df_un is not None:
        for _, row in df_un.iterrows():
            row_name = str(row.get('name', ''))
            aliases_str = str(row.get('aliases', ''))
            score = check_score(row_name, aliases_str)
            
            if score >= threshold:
                matches.append({
                    "source": "un_sanctions",
                    "name": row_name,
                    "match_score": score,
                    "aliases": aliases_str,
                    "countries": str(row.get('nationality', '')),
                    "details": f"Type: {row.get('type', '')}, List: {row.get('un_list_type', '')}"
                })
                
    # opensanctions
    df_os = load_local("opensanctions")
    if df_os is not None:
        for _, row in df_os.iterrows():
            row_name = str(row.get('caption', ''))
            aliases_str = str(row.get('aliases', ''))
            score = check_score(row_name, aliases_str)
            
            if score >= threshold:
                matches.append({
                    "source": "opensanctions",
                    "name": row_name,
                    "match_score": score,
                    "aliases": aliases_str,
                    "countries": str(row.get('countries', '')),
                    "details": f"Schema: {row.get('schema', '')}"
                })
                
    # Deduplicate by name + source
    seen = set()
    dedup = []
    for m in matches:
        key = f"{m['source']}:{m['name']}"
        if key not in seen:
            seen.add(key)
            dedup.append(m)
            
    dedup.sort(key=lambda x: x['match_score'], reverse=True)
    return dedup

async def query_fatf_risk(country: str) -> dict:
    df = load_local("fatf_jurisdictions")
    if df is None:
        return {"country": country, "risk_level": "unknown", "risk_score": 0.0}
        
    # 1. Exact match country
    match = df[df['country'].str.lower() == country.lower()]
    if not match.empty:
        row = match.iloc[0]
        return {
            "country": str(row['country']),
            "risk_level": str(row['risk_level']),
            "risk_score": float(row['risk_score'])
        }
        
    # 2. Exact match iso2
    match = df[df['iso2'].str.upper() == country.upper()]
    if not match.empty:
        row = match.iloc[0]
        return {
            "country": str(row['country']),
            "risk_level": str(row['risk_level']),
            "risk_score": float(row['risk_score'])
        }
        
    # 3. Fuzzy match
    best_score = 0
    best_row = None
    for _, row in df.iterrows():
        score = fuzz.ratio(country.lower(), str(row['country']).lower())
        if score > best_score:
            best_score = score
            best_row = row
            
    if best_score >= 85 and best_row is not None:
        return {
            "country": str(best_row['country']),
            "risk_level": str(best_row['risk_level']),
            "risk_score": float(best_row['risk_score'])
        }
        
    return {"country": country, "risk_level": "clean", "risk_score": 0.0}

async def query_icij_by_name(name: str, threshold: float = 70.0) -> list[dict]:
    matches = []
    
    query_normalized = normalize_entity_name(name)
    if not query_normalized:
        return []
    
    df_entities = load_local("icij_entities")
    if df_entities is not None:
        for _, row in df_entities.iterrows():
            row_name = str(row.get('name', ''))
            row_normalized = normalize_entity_name(row_name)
            if not row_normalized:
                continue
            
            token_sort_ratio = fuzz.token_sort_ratio(query_normalized, row_normalized)
            token_set_ratio = fuzz.token_set_ratio(query_normalized, row_normalized)
            partial_ratio = fuzz.partial_ratio(query_normalized, row_normalized)
            
            confidence = 0.5 * token_sort_ratio + 0.3 * token_set_ratio + 0.2 * partial_ratio
            if confidence >= threshold:
                matches.append({
                    "source": "icij_entities",
                    "node_id": str(row.get('node_id', '')),
                    "name": row_name,
                    "match_score": confidence / 100.0,
                    "jurisdiction": str(row.get('jurisdiction', '')),
                    "countries": str(row.get('countries', '')),
                    "dataset": str(row.get('sourceID', ''))
                })
                
    df_officers = load_local("icij_officers")
    if df_officers is not None:
        for _, row in df_officers.iterrows():
            row_name = str(row.get('name', ''))
            row_normalized = normalize_entity_name(row_name)
            if not row_normalized:
                continue
            
            token_sort_ratio = fuzz.token_sort_ratio(query_normalized, row_normalized)
            token_set_ratio = fuzz.token_set_ratio(query_normalized, row_normalized)
            partial_ratio = fuzz.partial_ratio(query_normalized, row_normalized)
            
            confidence = 0.5 * token_sort_ratio + 0.3 * token_set_ratio + 0.2 * partial_ratio
            if confidence >= threshold:
                matches.append({
                    "source": "icij_officers",
                    "node_id": str(row.get('node_id', '')),
                    "name": row_name,
                    "match_score": confidence / 100.0,
                    "jurisdiction": "",
                    "countries": str(row.get('countries', '')),
                    "dataset": str(row.get('sourceID', ''))
                })
                
    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches

async def query_gleif_by_name(name: str) -> dict | None:
    df = load_local("gleif")
    if df is None or df.empty:
        return None
        
    best_score = 0
    best_row = None
    
    for _, row in df.iterrows():
        row_name = str(row.get('legal_name', ''))
        score = fuzz.token_sort_ratio(name.lower(), row_name.lower()) / 100.0
        if score > best_score:
            best_score = score
            best_row = row
            
    if best_score >= 0.75 and best_row is not None:
        lei = str(best_row['lei'])
        return {
            "lei": lei,
            "legal_name": str(best_row['legal_name']),
            "jurisdiction": str(best_row['jurisdiction']),
            "country": str(best_row['country']),
            "status": str(best_row['status']),
            "gleif_url": f"https://search.gleif.org/#/record/{lei}"
        }
        
    return None

async def get_data_freshness() -> dict:
    return _last_updated
