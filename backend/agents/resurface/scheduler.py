from apscheduler.schedulers.asyncio import AsyncIOScheduler
from shared.logger import get_logger

logger = get_logger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


async def start_watchlist_polling(interval_minutes: int = 60):
    """
    Start periodic polling of all watchlist entries.
    Runs the Resurface agent on each entity at the given interval.
    """
    scheduler = get_scheduler()

    scheduler.add_job(
        poll_all_watchlist_entries,
        "interval",
        minutes=interval_minutes,
        id="watchlist_poll",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info(f"Watchlist polling started — interval: {interval_minutes}m")


async def poll_all_watchlist_entries():
    """
    Runs on schedule. Iterates all watchlist entries and checks for resurface events.
    """
    # TODO (P4): import watchlist store, iterate entries, run ResurfaceAlertEngine
    logger.info("Running scheduled watchlist poll...")
