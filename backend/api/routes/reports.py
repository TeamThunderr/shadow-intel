from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from shared.logger import get_logger

router = APIRouter(prefix="/report", tags=["reports"])
logger = get_logger(__name__)


@router.get("/{entity_id}/markdown")
async def download_markdown(entity_id: str):
    # TODO: pull from session store
    return Response(
        content="# Report placeholder",
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=shadow_intel_{entity_id}.md"}
    )


@router.get("/{entity_id}/pdf")
async def download_pdf(entity_id: str):
    # TODO (P4): use weasyprint to convert markdown → PDF
    return Response(content=b"", media_type="application/pdf")
