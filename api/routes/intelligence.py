"""
api/routes/intelligence.py

All API routes for the InsightStream intelligence layer.
Rate limits applied per endpoint using SlowAPI:
  - /query        10/minute  (most expensive — LLM + Pinecone)
  - /ingest*       5/minute  (expensive — embedding + Pinecone write)
  - /reports      30/minute  (cheap read — PostgreSQL only)
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from core_backend.security import get_api_key
from api.schemas import IngestRequest, QueryRequest, NewsIngestRequest, SECIngestRequest
from core_backend.database import get_db
from core_backend.models import Report
from sqlalchemy.orm import Session

from ingestion_pipeline.youtube_loader import ingest_youtube_video
from ingestion_pipeline.news_loader import ingest_news
from ingestion_pipeline.sec_loader import ingest_sec_filing
from services.rag_service import BasicRAGService

# Import shared limiter — defined in core_backend/limiter.py to avoid
# circular imports (main.py imports this router, so we can't import from main).
from core_backend.limiter import limiter

router = APIRouter()

# Single module-level RAG service instance shared across all requests.
rag_service = BasicRAGService()


# ── YouTube Ingest Endpoint ───────────────────────────────────────────────────

@router.post("/api/v1/intelligence/ingest")
@limiter.limit("5/minute")
async def ingest_video(
    request: Request,
    body: IngestRequest,
    api_key: str = Depends(get_api_key)
):
    """
    POST /api/v1/intelligence/ingest
    Rate limit: 5/minute per IP.
    """
    try:
        documents = ingest_youtube_video(body.video_url)
        rag_service.store_documents(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Successfully ingested video.",
        "chunks_stored": len(documents),
    }


# ── News Ingest Endpoint ──────────────────────────────────────────────────────

@router.post("/api/v1/intelligence/ingest/news")
@limiter.limit("5/minute")
async def ingest_news_topic(
    request: Request,
    body: NewsIngestRequest,
    api_key: str = Depends(get_api_key)
):
    """
    POST /api/v1/intelligence/ingest/news
    Rate limit: 5/minute per IP.
    """
    try:
        documents = ingest_news(body.topic)
        rag_service.store_documents(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Successfully ingested news for topic: {body.topic}",
        "chunks_stored": len(documents),
    }


# ── SEC Ingest Endpoint ───────────────────────────────────────────────────────

@router.post("/api/v1/intelligence/ingest/sec")
@limiter.limit("5/minute")
async def ingest_sec_ticker(
    request: Request,
    body: SECIngestRequest,
    api_key: str = Depends(get_api_key)
):
    """
    POST /api/v1/intelligence/ingest/sec
    Rate limit: 5/minute per IP.
    """
    try:
        documents = ingest_sec_filing(body.ticker)
        rag_service.store_documents(documents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Successfully ingested 10-K for ticker: {body.ticker}",
        "chunks_stored": len(documents),
        "ticker": body.ticker
    }


# ── Query Endpoint ────────────────────────────────────────────────────────────

@router.post("/api/v1/intelligence/query")
@limiter.limit("10/minute")
async def query(
    request: Request,
    body: QueryRequest,
    api_key: str = Depends(get_api_key)
):
    """
    POST /api/v1/intelligence/query
    Rate limit: 10/minute per IP.
    """
    try:
        result = rag_service.query(
            user_prompt          = body.query,
            conversation_history = [msg.model_dump() for msg in body.conversation_history],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "report":            result["report"],
        "cache_hit":         result["cache_hit"],
        "signal_label":      result["signal_label"],
        "signal_confidence": result["signal_confidence"],
        "contexts":          result.get("contexts", []),
    }


# ── Reports Endpoint ──────────────────────────────────────────────────────────

@router.get("/api/v1/intelligence/reports")
@limiter.limit("30/minute")
def get_reports(
    request: Request,
    limit: int = 10,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/intelligence/reports
    Rate limit: 30/minute per IP.
    """
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(limit).all()
    return {"total": len(reports), "reports": reports}
