"""
Investigation API routes.
Manages the full Shadow Intel investigation pipeline:
  POST /investigate              → start (returns immediately, runs in background)
  GET  /investigate/{id}/status  → real-time agent-level progress
  GET  /investigate/{id}         → completed InvestigationReport (JSON)
  GET  /investigate/{id}/report/markdown → download as .md file
"""

import asyncio

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response

from shared.schemas import (
    InvestigateRequest, InvestigationReport,
    InvestigationStatus, AgentStatus,
)
from shared.session import store
from shared.logger import get_logger

from agents.ghost_tracker.agent import GhostEntityTracker
from agents.ghost_tracker.fingerprint import build_fingerprint
from agents.money_trail import run_money_trail
from agents.ownership_unwind.agent import OwnershipUnwindAgent
from agents.dark_signal.agent import DarkSignalMonitor
from agents.resurface.agent import ResurfaceAlertEngine

from orchestrator.foundry import FoundryOrchestrator
from orchestrator.merger import merge_agent_results
from orchestrator.report_builder import build_report

router = APIRouter(prefix="/investigate", tags=["investigate"])
logger = get_logger(__name__)

# Singleton — initialised once at import time, reused across every request.
# Lazy Azure client init means this is safe even without credentials in .env.
_foundry = FoundryOrchestrator()


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("", response_model=dict, status_code=202)
async def start_investigation(
    request: InvestigateRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new investigation.

    Returns immediately (HTTP 202) with an ``entity_id``.
    The investigation runs as a FastAPI background task.
    Poll ``GET /investigate/{entity_id}/status`` every 2 seconds for progress.
    """
    fingerprint = build_fingerprint(request)
    entity_id = fingerprint.entity_id

    await store.create(entity_id, request.name, fingerprint)
    background_tasks.add_task(_run_investigation, entity_id)

    logger.info(f"Investigation queued: '{request.name}' → {entity_id}")
    return {
        "entity_id": entity_id,
        "status": "running",
        "message": (
            f"Investigation started for '{request.name}'. "
            f"Poll /investigate/{entity_id}/status for progress."
        ),
    }


@router.get("/{entity_id}/status", response_model=InvestigationStatus)
async def get_investigation_status(entity_id: str):
    """
    Real-time agent-level status for a running or completed investigation.
    The frontend polls this endpoint every 2 seconds to drive the progress UI.
    """
    session = await store.get(entity_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation '{entity_id}' not found.",
        )
    return session.to_status()


@router.get("/{entity_id}", response_model=InvestigationReport)
async def get_investigation_report(entity_id: str):
    """
    Return the completed ``InvestigationReport``.

    Raises HTTP 202 while the investigation is still running,
    HTTP 500 if it failed, or HTTP 404 if the entity_id is unknown.
    """
    session = await store.get(entity_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Investigation '{entity_id}' not found.",
        )
    if session.status.overall_status == "running":
        raise HTTPException(status_code=202, detail="Investigation still in progress.")
    if session.status.overall_status == "failed":
        raise HTTPException(
            status_code=500,
            detail=f"Investigation failed: {session.error}",
        )
    if not session.report:
        raise HTTPException(status_code=202, detail="Report not yet available.")

    return session.report


@router.get("/{entity_id}/report/markdown")
async def download_markdown_report(entity_id: str):
    """Download the investigation report as a Markdown file."""
    session = await store.get(entity_id)
    if not session:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    if not session.report:
        raise HTTPException(status_code=202, detail="Report not yet available.")

    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in session.entity_name
    )
    filename = f"shadow_intel_{safe_name}_{entity_id[:8]}.md"

    return Response(
        content=session.report.report_markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ─── Background pipeline ──────────────────────────────────────────────────────

async def _run_investigation(entity_id: str) -> None:
    """
    Full investigation pipeline — runs as a FastAPI BackgroundTask.

    Flow
    ────
    1. Ghost Entity Tracker   (sequential — it builds/enriches the fingerprint)
    2. Money Trail + Ownership Unwind + Dark Signal + Resurface  (parallel)
    3. Merge → Foundry IQ narrative → Build & store report

    The ``return_exceptions=True`` flag in asyncio.gather() means a single
    agent failure never kills the whole pipeline. Exceptions are normalised
    to ``None`` before being passed to the merger.
    """
    session = await store.get(entity_id)
    if not session:
        logger.error(f"_run_investigation: session not found for {entity_id}")
        return

    fingerprint = session.fingerprint
    status = session.status

    try:
        # ── Step 1: Ghost Entity Tracker ──────────────────────────────────
        logger.info(f"[{entity_id}] Step 1: Ghost Entity Tracker")
        status.agents.ghost_tracker = AgentStatus.running

        ghost = await GhostEntityTracker().execute(fingerprint)
        status.agents.ghost_tracker = AgentStatus.complete

        # Ghost Tracker enriches the shared fingerprint — propagate the
        # enriched version to all downstream agents.
        if ghost.data.get("fingerprint"):
            from shared.schemas import EntityFingerprint as FP
            enriched_fp = FP(**ghost.data["fingerprint"])
            session.fingerprint = enriched_fp
            fingerprint = enriched_fp

        logger.info(
            f"[{entity_id}] Ghost complete | "
            f"risk={ghost.risk_score:.2f} | "
            f"evidence={len(ghost.evidence)} | "
            f"sanctions_hit={ghost.data.get('sanctions_hit', False)}"
        )

        # ── Step 2: Parallel agents ────────────────────────────────────────
        logger.info(f"[{entity_id}] Step 2: running 4 agents in parallel")
        status.agents.money_trail      = AgentStatus.running
        status.agents.ownership_unwind = AgentStatus.running
        status.agents.dark_signal      = AgentStatus.running
        status.agents.resurface_engine = AgentStatus.running

        # Wrapper to return AgentResponse from dict
        async def _run_money_trail_wrapped(fp):
            res_dict = await run_money_trail(fp.model_dump() if hasattr(fp, "model_dump") else fp.dict())
            from shared.schemas import AgentResponse
            return AgentResponse(**res_dict)

        money_r, ownership_r, signal_r, resurface_r = await asyncio.gather(
            _run_money_trail_wrapped(fingerprint),
            OwnershipUnwindAgent().execute(fingerprint),
            DarkSignalMonitor().execute(fingerprint),
            ResurfaceAlertEngine().execute(fingerprint),
            return_exceptions=True,
        )

        # Normalise exceptions → None so the merger handles them gracefully
        money =     money_r     if not isinstance(money_r,     Exception) else None
        ownership = ownership_r if not isinstance(ownership_r, Exception) else None
        signal =    signal_r    if not isinstance(signal_r,    Exception) else None
        resurface = resurface_r if not isinstance(resurface_r, Exception) else None

        # Log any exceptions that occurred
        for name, result in [
            ("money_trail",      money_r),
            ("ownership_unwind", ownership_r),
            ("dark_signal",      signal_r),
            ("resurface_engine", resurface_r),
        ]:
            if isinstance(result, Exception):
                logger.error(f"[{entity_id}] {name} raised exception: {result}")

        status.agents.money_trail      = AgentStatus.complete if money     else AgentStatus.failed
        status.agents.ownership_unwind = AgentStatus.complete if ownership else AgentStatus.failed
        status.agents.dark_signal      = AgentStatus.complete if signal    else AgentStatus.failed
        status.agents.resurface_engine = AgentStatus.complete if resurface else AgentStatus.failed

        logger.info(f"[{entity_id}] Parallel agents complete")

        # ── Step 3: Foundry IQ Orchestration ──────────────────────────────
        logger.info(f"[{entity_id}] Step 3: Foundry IQ Orchestrator")
        status.agents.orchestrator = AgentStatus.running

        merged_evidence, unified_confidence, risk_level, source_breakdown = \
            merge_agent_results(ghost, money, ownership, signal, resurface)

        narrative = await _foundry.generate_narrative(
            entity_name=fingerprint.canonical_name,
            risk_level=risk_level,
            unified_confidence=unified_confidence,
            evidence=merged_evidence,
            source_breakdown=source_breakdown,
        )

        report = build_report(
            entity_id=entity_id,
            entity_name=fingerprint.canonical_name,
            fingerprint=fingerprint,
            ghost=ghost,
            money=money,
            ownership=ownership,
            signal=signal,
            resurface=resurface,
            merged_evidence=merged_evidence,
            unified_confidence=unified_confidence,
            risk_level=risk_level,
            narrative=narrative,
        )

        status.agents.orchestrator = AgentStatus.complete
        await store.complete(entity_id, report)

        logger.info(
            f"[{entity_id}] Investigation COMPLETE | "
            f"entity='{fingerprint.canonical_name}' | "
            f"confidence={unified_confidence:.1%} | "
            f"risk={risk_level.value} | "
            f"evidence={len(merged_evidence)}"
        )

    except Exception as exc:
        logger.error(
            f"[{entity_id}] Investigation FAILED: {exc}",
            exc_info=True,
        )
        await store.fail(entity_id, str(exc))
