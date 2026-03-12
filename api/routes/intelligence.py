"""
api/routes/intelligence.py

This module defines all API routes for the InsightStream intelligence layer.
It uses FastAPI's APIRouter to keep routing logic modular and separate from the
application entry point (main.py). Two categories of endpoints are registered:

  1. /api/v1/intelligence/ingest  — Ingestion endpoint.
     Accepts a YouTube video URL, fetches and chunks its transcript via the
     ingestion pipeline, then persists those chunks into the Pinecone vector store.

  2. /api/v1/intelligence/query   — Query endpoint.
     Accepts a natural-language question, performs a Pinecone similarity search,
     and returns an LLM-synthesized answer grounded in retrieved context.

Stage 3 note: Additional route modules (e.g., reports.py, sources.py) can be
added alongside this file and registered in main.py with separate include_router()
calls, keeping each concern fully isolated.
"""

from fastapi import APIRouter, HTTPException, Depends
from core_backend.security import get_api_key

# All request schemas live in api/schemas.py. Importing them here keeps this
# module focused purely on routing logic — endpoint definitions, HTTP error
# handling, and response shaping — with no schema duplication.
from api.schemas import IngestRequest, QueryRequest, NewsIngestRequest, SECIngestRequest, ReportsResponse
from core_backend.database import SessionLocal, get_db
from core_backend.models import Report
from sqlalchemy.orm import Session

# ingest_youtube_video handles transcript fetching and chunking.
# It returns a list of LangChain Document objects ready for embedding and storage.
from ingestion_pipeline.youtube_loader import ingest_youtube_video

# ingest_news fetches top Tavily articles and chunks them.
from ingestion_pipeline.news_loader import ingest_news

# ingest_sec_filing downloads and chunks latest SEC 10-K filings.
from ingestion_pipeline.sec_loader import ingest_sec_filing

# BasicRAGService owns both halves of the RAG pipeline:
#   - store_documents(): embeds Document chunks and upserts them into Pinecone.
#   - query():          retrieves relevant context from Pinecone and calls the LLM.
# Instantiating it once at module load time is intentional: __init__ loads
# credentials, wires up the embedding model, the LLM, and the Pinecone connection,
# and seeds the index with the baseline corpus. All of that work is paid once
# at startup so individual requests stay fast.
from services.rag_service import BasicRAGService

# ── Router Initialization ─────────────────────────────────────────────────────
# APIRouter groups related endpoints into a self-contained module. main.py
# attaches this router to the FastAPI application with a single include_router()
# call, keeping the app entry point clean regardless of how many routes we add.
router = APIRouter()

# ── Service Instantiation ─────────────────────────────────────────────────────
# A single module-level instance is shared across all requests. This avoids
# re-initialising the Pinecone connection, the embedding model, and the LLM
# client on every HTTP hit, which would be prohibitively expensive.
rag_service = BasicRAGService()


# ── Ingestion Endpoint ────────────────────────────────────────────────────────

@router.post("/api/v1/intelligence/ingest")
async def ingest_video(request: IngestRequest, api_key: str = Depends(get_api_key)):
    """
    POST /api/v1/intelligence/ingest

    Ingests a YouTube video's transcript into the Pinecone knowledge base.

    Flow:
      1. FastAPI deserialises and validates the request body into an IngestRequest.
      2. ingest_youtube_video() fetches the transcript from YouTube and splits it
         into overlapping Document chunks using RecursiveCharacterTextSplitter
         (token-aware, 512 token chunks with 50 token overlap).
         Each chunk has metadata["source"] = "youtube".
      3. rag_service.store_documents() embeds each chunk with OpenAIEmbeddings
         and upserts the resulting vectors into the live Pinecone index.
         After this call the new content is immediately available for similarity search.
      4. We return a success message that reports how many chunks were stored,
         which gives the caller a simple signal of how much content was indexed.

    Args:
        request: A validated IngestRequest instance containing the video URL.

    Returns:
        A JSON object:
        {
          "message": "Successfully ingested video.",
          "chunks_stored": <int>
        }

    Raises:
        HTTPException 500: Raised if the YouTube transcript cannot be fetched
                           (private video, disabled captions, invalid URL) or if
                           the Pinecone upsert fails (network error, quota exceeded).
    """
    try:
        # Phase 1 — Load and chunk the transcript.
        # ingest_youtube_video() returns a list of Document objects. The number
        # of documents depends on the video length and the splitter's chunk_size
        # setting (currently 512 tokens with 50-token overlap).
        documents = ingest_youtube_video(request.video_url)

        # Phase 2 — Embed and persist to Pinecone.
        # store_documents() delegates to PineconeVectorStore.add_documents(),
        # which handles both embedding and upserting in a single call. Vectors
        # become searchable in Pinecone within a few seconds of this returning.
        rag_service.store_documents(documents)

    except Exception as e:
        # Surface any upstream failure (bad URL, no transcript, Pinecone error)
        # as an HTTP 500 so the caller receives a structured JSON error body
        # rather than an unhandled server crash or an opaque timeout.
        raise HTTPException(status_code=500, detail=str(e))

    # Report back the exact number of chunks stored. This is useful for the
    # caller to verify that the ingestion produced a reasonable amount of content
    # (e.g., a 30-minute video should produce many more chunks than a 2-minute one).
    return {
        "message": "Successfully ingested video.",
        "chunks_stored": len(documents),
    }


@router.post("/api/v1/intelligence/ingest/news")
async def ingest_news_topic(request: NewsIngestRequest, api_key: str = Depends(get_api_key)):
    """
    POST /api/v1/intelligence/ingest/news

    Ingests recent competitive intelligence news on a specific topic.
    """
    try:
        # Phase 1 — Load and chunk the news articles using Tavily.
        # ingest_news() fetches top 5 results and chunks them (512 tokens).
        documents = ingest_news(request.topic)

        # Phase 2 — Embed and persist to Pinecone.
        rag_service.store_documents(documents)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Successfully ingested news for topic: {request.topic}",
        "chunks_stored": len(documents),
    }


@router.post("/api/v1/intelligence/ingest/sec")
async def ingest_sec_ticker(request: SECIngestRequest, api_key: str = Depends(get_api_key)):
    """
    POST /api/v1/intelligence/ingest/sec

    Ingests the latest 10-K SEC filing for a specific stock ticker.
    """
    try:
        # Phase 1 — Download and chunk the latest 10-K using sec-edgar-downloader.
        documents = ingest_sec_filing(request.ticker)

        # Phase 2 — Embed and persist to Pinecone.
        rag_service.store_documents(documents)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": f"Successfully ingested 10-K for ticker: {request.ticker}",
        "chunks_stored": len(documents),
        "ticker": request.ticker
    }


# ── Query Endpoint ────────────────────────────────────────────────────────────

@router.post("/api/v1/intelligence/query")
async def intelligence_query(request: QueryRequest, api_key: str = Depends(get_api_key)):
    """
    POST /api/v1/intelligence/query

    Answers a natural-language competitive intelligence question by searching
    the Pinecone knowledge base and synthesising a grounded LLM response.

    Flow:
      1. FastAPI deserialises and validates the request body into a QueryRequest.
      2. rag_service.query() performs a cosine-similarity search against the
         Pinecone index to retrieve the top-10 most relevant Document chunks,
         constructs a grounded prompt (context + question), and calls the LLM.
      3. The LLM's plain-text response is wrapped in a JSON envelope and returned.

    Args:
        request: A validated QueryRequest instance containing the user's question.

    Returns:
        A JSON object:
        {
          "answer": "<LLM-synthesised response string>"
        }

    Raises:
        HTTPException 500: Raised if the Pinecone similarity search or the
                           OpenAI Chat API call fails for any reason.
    """
    try:
        # Delegate entirely to the RAG service. The route stays thin — it is
        # responsible only for HTTP concerns (parsing, error shaping, response
        # formatting). All intelligence logic lives in rag_service.query().
        answer_dict = rag_service.query(request.query)

    except Exception as e:
        # Convert any RAG-layer or network exception into a structured 500 so
        # the client always receives JSON, never an unhandled Python traceback.
        raise HTTPException(status_code=500, detail=str(e))

    # Return the exact dictionary returned by the RAG service which now 
    # includes "report", "cache_hit", "signal_label", and "signal_confidence".
    return answer_dict

@router.get("/api/v1/intelligence/reports")
def get_reports(
    limit: int = 10,
    api_key: str = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/intelligence/reports
    Returns a list of previously generated intelligence reports from PostgreSQL.
    """
    reports = db.query(Report).order_by(Report.created_at.desc()).limit(limit).all()
    return {"total": len(reports), "reports": reports}
