from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
import uuid
from datetime import datetime


class EntityType(str, Enum):
    company = "company"
    person = "person"
    unknown = "unknown"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AgentStatus(str, Enum):
    pending = "pending"
    running = "running"
    complete = "complete"
    failed = "failed"


class MatchType(str, Enum):
    exact = "exact"
    fuzzy = "fuzzy"
    director_overlap = "director_overlap"
    address_reuse = "address_reuse"


# ─── Core Evidence Item ───────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str
    type: str
    detail: str
    url: Optional[str] = None
    date: Optional[datetime] = None
    confidence: float = Field(ge=0.0, le=1.0)


# ─── Base Agent Response ──────────────────────────────────────────────────────

class AgentResponse(BaseModel):
    module: str
    entity_id: str
    status: AgentStatus = AgentStatus.complete
    processing_time_ms: int = 0
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = []
    data: dict = {}
    error: Optional[str] = None


# ─── Investigation Request / Response ─────────────────────────────────────────

class InvestigateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    entity_type: EntityType = EntityType.unknown
    country_hint: Optional[str] = Field(default=None, max_length=2)
    confidence_threshold: float = Field(default=0.80, ge=0.0, le=1.0)


class EntityFingerprint(BaseModel):
    entity_id: str
    canonical_name: str
    aliases: list[str] = []
    jurisdictions: list[str] = []
    directors: list[str] = []
    addresses: list[str] = []
    registration_numbers: list[str] = []
    sanctions_lists: list[str] = []


class AgentStatuses(BaseModel):
    ghost_tracker: AgentStatus = AgentStatus.pending
    money_trail: AgentStatus = AgentStatus.pending
    ownership_unwind: AgentStatus = AgentStatus.pending
    dark_signal: AgentStatus = AgentStatus.pending
    resurface_engine: AgentStatus = AgentStatus.pending
    orchestrator: AgentStatus = AgentStatus.pending


class InvestigationStatus(BaseModel):
    entity_id: str
    overall_status: str = "running"
    agents: AgentStatuses = AgentStatuses()
    elapsed_ms: int = 0


class EvidenceChainStep(BaseModel):
    step: int
    finding: str
    source_module: str
    sources: list[str] = []
    confidence: float


class InvestigationReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_id: str
    entity_name: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    unified_confidence: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.low
    narrative_summary: str = ""
    evidence_chain: list[EvidenceChainStep] = []
    ghost_tracker: Optional[AgentResponse] = None
    money_trail: Optional[AgentResponse] = None
    ownership_unwind: Optional[AgentResponse] = None
    dark_signal: Optional[AgentResponse] = None
    resurface_watch: Optional[AgentResponse] = None
    report_markdown: str = ""


# ─── Watchlist ────────────────────────────────────────────────────────────────

class WatchlistEntry(BaseModel):
    entity_id: str
    entity_name: str
    fingerprint: EntityFingerprint
    confidence_threshold: float = 0.80
    added_at: datetime = Field(default_factory=datetime.utcnow)
    last_checked: Optional[datetime] = None
    last_alert: Optional[datetime] = None


class WatchlistAddRequest(BaseModel):
    name: str
    entity_type: EntityType = EntityType.unknown
    confidence_threshold: float = 0.80


# ─── Alert ────────────────────────────────────────────────────────────────────

class AlertPayload(BaseModel):
    alert_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    alert_type: str = "resurface"
    entity_id: str
    entity_name: str
    confidence: float
    risk_level: RiskLevel
    match_event: str
    jurisdiction: Optional[str] = None
    top_evidence: list[str] = []
    report_url: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
