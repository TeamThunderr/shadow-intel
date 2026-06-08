from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from shared.http_client import close_client
from shared.logger import get_logger
from api.routes.investigate import router as investigate_router
from api.routes.watchlist import router as watchlist_router
from api.routes.reports import router as reports_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Shadow Intel backend starting up")
    from shared.config import get_settings
    settings = get_settings()
    has_occrp_key = "YES" if settings.occrp_api_key else "NO"
    logger.info(f"OCCRP API key detected: {has_occrp_key}")
    yield
    await close_client()
    logger.info("Shadow Intel backend shut down")


app = FastAPI(
    title="Shadow Intel API",
    description="Financial crime intelligence platform — Shadow Intel",
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

app.include_router(investigate_router)
app.include_router(watchlist_router)
app.include_router(reports_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "shadow-intel-api"}
