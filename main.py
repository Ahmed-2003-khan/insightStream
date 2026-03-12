"""
main.py

Application entry point for InsightStream.

This file is intentionally thin. Its only responsibilities are:
  1. Create the FastAPI application instance.
  2. Register all routers (route modules) onto that instance.
  3. (Optionally) configure global middleware, CORS, or startup/shutdown events.

All actual routing logic lives in api/routes.py, keeping this file clean
and easy to extend as the project grows.
"""

from fastapi import FastAPI
from api.routes.intelligence import router

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from ingestion_pipeline.news_loader import ingest_news
from ingestion_pipeline.sec_loader import ingest_sec_filing
from services.rag_service import BasicRAGService
from core_backend.database import SessionLocal
from core_backend.models import Report
import logging
import sys

logging.basicConfig(
    stream=sys.stdout, 
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

TRACKED_COMPANIES = [
    {"name": "Microsoft", "ticker": "MSFT", "query": "Microsoft AI strategy and product launches"},
    {"name": "Apple",     "ticker": "AAPL", "query": "Apple revenue earnings and product news"},
    {"name": "Google",    "ticker": "GOOGL", "query": "Google Alphabet AI competition and launches"},
]

async def nightly_pipeline():
    logger.info("Nightly pipeline starting...")
    rag = BasicRAGService()

    for company in TRACKED_COMPANIES:
        try:
            # Step 1: Ingest fresh news
            news_chunks = ingest_news(company["query"])
            rag.store_documents(news_chunks)
            logger.info(f"News ingested for {company['name']}: {len(news_chunks)} chunks")

            # Step 2: Ingest SEC filing
            sec_chunks = ingest_sec_filing(company["ticker"])
            rag.store_documents(sec_chunks)
            logger.info(f"SEC filing ingested for {company['name']}: {len(sec_chunks)} chunks")

            # Step 3: Generate intelligence report
            result = rag.query(company["query"])
            
            logger.info(f"Report Output Keys: {result.keys()}")
            logger.info(f"Cache Hit?: {result.get('cache_hit')}")

            logger.info(f"Nightly report generated for {company['name']}")

        except Exception as e:
            logger.error(f"Nightly pipeline failed for {company['name']}: {repr(e)}")
            import traceback
            traceback.print_exc()
            continue

    logger.info("Nightly pipeline complete.")

# ── Application Initialization ────────────────────────────────────────────────
# FastAPI() creates the ASGI application object. The title and version appear
# in the auto-generated OpenAPI docs (accessible at /docs once the server is
# running), which makes the API self-documenting out of the box.
app = FastAPI(
    title="InsightStream Intelligence API",
    version="1.0.0",
    description=(
        "A Retrieval-Augmented Generation (RAG) API that answers competitive "
        "intelligence queries by grounding LLM responses in curated knowledge."
    ),
)

# ── Router Registration ───────────────────────────────────────────────────────
# include_router() mounts all routes defined in api/routes.py onto the app.
# Because the full path (/api/v1/intelligence/query) is already declared on
# each endpoint inside routes.py, we do not need to add a prefix here.
# If we had multiple route modules (e.g., for users, reports, settings),
# we would call include_router() once for each, keeping concerns separated.
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
