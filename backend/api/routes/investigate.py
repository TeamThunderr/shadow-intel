from fastapi import APIRouter, HTTPException, BackgroundTasks
from shared.schemas import (
    InvestigateRequest, InvestigationReport, InvestigationStatus,
    AgentStatuses, AgentStatus
)
from agents.ghost_tracker.agent import GhostEntityTracker
from agents.ghost_tracker.fingerprint import build_fingerprint
from agents.money_trail.agent import MoneyTrailAgent
from agents.ownership_unwind.agent import OwnershipUnwindAgent
from agents.dark_signal.agent import DarkSignalMonitor
from agents.resurface.agent import ResurfaceAlertEngine
from orchestrator.foundry import FoundryOrchestrator
from orchestrator.merger import merge_agent_results
from orchestrator.report_builder import build_report
from shared.logger import get_logger
import asyncio

router = APIRouter(prefix="/investigate", tags=["investigate"])
logger = get_logger(__name__)

# In-memory session store (replace with Redis for production)
sessions: dict[str, dict] = {}


@router.post("", response_model=dict)
async def start_investigation(request: InvestigateRequest, background_tasks: BackgroundTasks):
    """Start a new investigation. Returns entity_id immediately."""
    fingerprint = build_fingerprint(request)
    entity_id = fingerprint.entity_id

    # Initialise session
    sessions[entity_id] = {
        "fingerprint": fingerprint,
        "status": InvestigationStatus(entity_id=entity_id),
        "report": None,
    }

    background_tasks.add_task(run_investigation, entity_id, fingerprint)
    logger.info(f"Investigation started: {entity_id} for '{request.name}'")

    return {"entity_id": entity_id, "status": "running"}


@router.get("/{entity_id}/status", response_model=InvestigationStatus)
async def get_status(entity_id: str):
    session = sessions.get(entity_id)
    if not session:
        raise HTTPException(status_code=404, detail="Investigation not found")
    return session["status"]


@router.get("/{entity_id}", response_model=InvestigationReport)
async def get_report(entity_id: str):
    session = sessions.get(entity_id)
    if not session:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if not session["report"]:
        raise HTTPException(status_code=202, detail="Investigation still running")
    return session["report"]


async def run_investigation(entity_id: str, fingerprint):
    """Background task — runs all agents and builds the report."""
    session = sessions[entity_id]
    status: InvestigationStatus = session["status"]

    try:
        # Step 1: Ghost Tracker (must run first — builds fingerprint)
        status.agents.ghost_tracker = AgentStatus.running
        ghost = await GhostEntityTracker().execute(fingerprint)
        status.agents.ghost_tracker = AgentStatus.complete

        # Step 2: All other agents in parallel
        status.agents.money_trail = AgentStatus.running
        status.agents.ownership_unwind = AgentStatus.running
        status.agents.dark_signal = AgentStatus.running
        status.agents.resurface_engine = AgentStatus.running

        money, ownership, signal, resurface = await asyncio.gather(
            MoneyTrailAgent().execute(fingerprint),
            OwnershipUnwindAgent().execute(fingerprint),
            DarkSignalMonitor().execute(fingerprint),
            ResurfaceAlertEngine().execute(fingerprint),
        )

        status.agents.money_trail = AgentStatus.complete
        status.agents.ownership_unwind = AgentStatus.complete
        status.agents.dark_signal = AgentStatus.complete
        status.agents.resurface_engine = AgentStatus.complete

        # Step 3: Orchestrate
        status.agents.orchestrator = AgentStatus.running
        evidence, confidence, risk = merge_agent_results(ghost, money, ownership, signal, resurface)
        narrative = await FoundryOrchestrator().generate_narrative(
            fingerprint.canonical_name,
            [e.model_dump() for e in evidence]
        )
        report = build_report(
            entity_id, fingerprint.canonical_name,
            ghost, money, ownership, signal, resurface,
            confidence, risk, narrative
        )
        status.agents.orchestrator = AgentStatus.complete
        status.overall_status = "complete"
        session["report"] = report
        logger.info(f"Investigation complete: {entity_id} | confidence={confidence:.2f} | risk={risk}")

    except Exception as e:
        status.overall_status = "failed"
        logger.error(f"Investigation failed for {entity_id}: {e}")
