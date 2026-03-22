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
    {"name": "Microsoft", "ticker": "MSFT"},
    {"name": "Apple",     "ticker": "AAPL"},
    {"name": "Google",    "ticker": "GOOGL"},
]

from datetime import datetime
from services.cache_service import clear_cache

async def nightly_pipeline():
    logger.info("Nightly pipeline starting...")

    # Fix 2A: Clear cache before pipeline so fresh data is used
    cleared = clear_cache()
    logger.info(f"Cache cleared: {cleared} keys removed")

    rag = BasicRAGService()
    is_monday = datetime.now().weekday() == 0

    for company in TRACKED_COMPANIES:
        try:
            # Fix 2B: SEC only on Mondays
            if is_monday:
                sec_chunks = ingest_sec_filing(company["ticker"])
                rag.store_documents(sec_chunks)
                logger.info(f"SEC filing ingested for {company['name']}: {len(sec_chunks)} chunks")
            else:
                logger.info(f"SEC skipped for {company['name']} — not Monday")

            # Query planner generates dynamic query via LangGraph
            result = intelligence_graph.invoke({
                "company_name": company["name"],
                "planned_query": "",
                "query": "",
                "search_results": [],
                "signal_label": "",
                "signal_confidence": 0.0,
                "final_report": "",
                "retry_count": 0
            })
            logger.info(f"Planned query for {company['name']}: {result['planned_query']}")
            logger.info(f"Report generated for {company['name']}: {result['signal_label']}")

        except Exception as e:
            logger.error(f"Pipeline failed for {company['name']}: {e}")
            continue

    logger.info("Nightly pipeline complete.")

# ── Application Initialization ────────────────────────────────────────────────
# FastAPI() creates the ASGI application object. The title and version appear
# in the auto-generated OpenAPI docs (accessible at /docs once the server is
# running), which makes the API self-documenting out of the box.
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="InsightStream Intelligence API",
    version="1.0.0",
    description=(
        "A Retrieval-Augmented Generation (RAG) API that answers competitive "
        "intelligence queries by grounding LLM responses in curated knowledge."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
