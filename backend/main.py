from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.http_client import close_client
from shared.logger import get_logger

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Load local parquet datasets into memory ───────────────────────────────
    logger.info("Loading local intelligence datasets…")
    from shared.data_loader import load_all
    load_all()

    # ── Log key config state ──────────────────────────────────────────────────
    from shared.config import get_settings
    settings = get_settings()
    logger.info(
        f"Foundry IQ endpoint configured: {'YES' if settings.azure_foundry_endpoint else 'NO'} | "
        f"deployment: {settings.azure_foundry_deployment}"
    )
    logger.info(
        f"OpenSanctions key: {'YES' if settings.opensanctions_api_key else 'NO'} | "
        f"Etherscan key: {'YES' if settings.etherscan_api_key else 'NO'}"
    )
    logger.info("Shadow Intel ready — all systems operational")
    yield
    await close_client()
    logger.info("Shadow Intel shutdown complete")


app = FastAPI(
    title="Shadow Intel API",
    description="Multi-agent financial crime intelligence platform — Agents League 2026",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes.investigate import router as investigate_router
from api.routes.watchlist import router as watchlist_router
from api.routes.reports import router as reports_router

app.include_router(investigate_router)
app.include_router(watchlist_router)
app.include_router(reports_router)


@app.get("/health")
async def health():
    from shared.data_loader import get_dataset_counts
    return {
        "status": "ok",
        "service": "shadow-intel-api",
        "version": "1.0.0",
        "datasets": get_dataset_counts(),
    }
