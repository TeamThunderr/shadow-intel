from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from shared.session import store
from shared.logger import get_logger

router = APIRouter(prefix="/report", tags=["reports"])
logger = get_logger(__name__)


@router.get("/{entity_id}/markdown")
async def download_markdown(entity_id: str):
    """Download the investigation report as a Markdown file."""
    session = await store.get(entity_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")
    safe_name = "".join(
        c if c.isalnum() or c in "-_" else "_"
        for c in session.entity_name
    )
    return Response(
        content=session.report.report_markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f"attachment; filename=shadow_intel_{safe_name}_{entity_id[:8]}.md"
            )
        },
    )


@router.get("/{entity_id}/pdf")
async def download_pdf(entity_id: str):
    """
    Download the investigation report as a PDF.
    TODO (P4): use weasyprint to convert report_markdown → PDF.
    """
    session = await store.get(entity_id)
    if not session or not session.report:
        raise HTTPException(status_code=404, detail="Report not found")
    # Stub — P4 implements weasyprint conversion
    return Response(content=b"", media_type="application/pdf")
