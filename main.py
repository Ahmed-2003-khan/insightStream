"""
main.py

Application entry point for InsightStream.

This file is intentionally thin. Its only responsibilities are:
  1. Create the FastAPI application instance.
  2. Register all routers (route modules) onto that instance.
  3. Configure global middleware, CORS, rate limiting, and startup/shutdown events.

All actual routing logic lives in api/routes/intelligence.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core_backend.limiter import limiter

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ingestion_pipeline.news_loader import ingest_news
from ingestion_pipeline.sec_loader import ingest_sec_filing
from services.rag_service import BasicRAGService
from core_backend.database import SessionLocal
from core_backend.models import Report
from datetime import datetime
from services.cache_service import clear_cache
import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# ── Rate Limiter ──────────────────────────────────────────────────────────────
# Imported from core_backend.limiter to avoid circular imports with routes.

TRACKED_COMPANIES = [
    {"name": "Microsoft", "ticker": "MSFT"},
    {"name": "Apple",     "ticker": "AAPL"},
    {"name": "Google",    "ticker": "GOOGL"},
]

async def nightly_pipeline():
    logger.info("Nightly pipeline starting...")

    # Clear cache before pipeline so fresh data is used
    cleared = clear_cache()
    logger.info(f"Cache cleared: {cleared} keys removed")

    rag = BasicRAGService()
    is_monday = datetime.now().weekday() == 0

    for company in TRACKED_COMPANIES:
        try:
            # SEC only on Mondays
            if is_monday:
                sec_chunks = ingest_sec_filing(company["ticker"])
                rag.store_documents(sec_chunks)
                logger.info(f"SEC filing ingested for {company['name']}: {len(sec_chunks)} chunks")
            else:
                logger.info(f"SEC skipped for {company['name']} — not Monday")

            # Query planner generates dynamic query via LangGraph
            from ai_orchestration.graph import intelligence_graph
            result = intelligence_graph.invoke({
                "company_name": company["name"],
                "planned_query": "",
                "query": "",
                "search_results": [],
                "signal_label": "",
                "signal_confidence": 0.0,
                "final_report": "",
                "retry_count": 0,
                "conversation_history": [],
            })
            logger.info(f"Planned query for {company['name']}: {result['planned_query']}")
            logger.info(f"Report generated for {company['name']}: {result['signal_label']}")

        except Exception as e:
            logger.error(f"Pipeline failed for {company['name']}: {e}")
            continue

    logger.info("Nightly pipeline complete.")

# ── Application Initialization ────────────────────────────────────────────────
app = FastAPI(
    title="InsightStream Intelligence API",
    version="1.0.0",
    description=(
        "A Retrieval-Augmented Generation (RAG) API that answers competitive "
        "intelligence queries by grounding LLM responses in curated knowledge."
    ),
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
# Attach limiter to app state so SlowAPI can find it,
# and register the 429 exception handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router Registration ───────────────────────────────────────────────────────
from api.routes.intelligence import router
app.include_router(router)

@app.on_event("startup")
async def startup_event():
    scheduler.add_job(
        nightly_pipeline,
        CronTrigger(hour=2, minute=0),
        id="nightly_pipeline",
        replace_existing=True
    )
    scheduler.start()
    logger.info("Scheduler started. Nightly pipeline scheduled at 2:00 AM.")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped.")
