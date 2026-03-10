"""
api/routes.py

This module defines all API routes for the InsightStream intelligence layer.
It uses FastAPI's APIRouter to keep routing logic modular and separate from
the application entry point (main.py). The router is registered in main.py,
which means every route defined here will be accessible under the application.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import the core RAG service. BasicRAGService encapsulates the full
# Retrieval-Augmented Generation pipeline: embedding, vector search, and
# LLM synthesis. We instantiate it here at module load time so that the
# expensive __init__ work (embedding the corpus, building the FAISS index)
# is done once when the server starts — not on every incoming request.
from services.rag_service import BasicRAGService

# ── Router Initialization ─────────────────────────────────────────────────────
# APIRouter is FastAPI's way of grouping related endpoints. By defining routes
# on a router (rather than directly on the FastAPI app), we can keep this file
# self-contained and include it in main.py with a single line.
router = APIRouter()

# ── Service Instantiation ─────────────────────────────────────────────────────
# A single, module-level instance of BasicRAGService is created here.
# This pattern (sometimes called "poor-man's dependency injection") ensures
# that the FAISS index and LLM client are shared across all requests rather
# than being re-initialized on every hit, which would be prohibitively slow.
rag_service = BasicRAGService()


# ── Request Schema ────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    """
    Pydantic model for the POST /query request body.

    FastAPI automatically parses and validates the incoming JSON body against
    this schema. If the body is missing the 'query' field or if 'query' is
    not a string, FastAPI returns a 422 Unprocessable Entity before our
    handler function even runs.

    Attributes:
        query: The natural-language question submitted by the user,
               e.g. "What is TechNova's latest funding round?"
    """

    query: str


# ── Intelligence Query Endpoint ───────────────────────────────────────────────
@router.post("/api/v1/intelligence/query")
async def intelligence_query(request: QueryRequest):
    """
    POST /api/v1/intelligence/query

    Receives a natural-language query and returns a grounded answer synthesized
    by the RAG pipeline.

    Flow:
      1. FastAPI deserializes the request body into a QueryRequest instance,
         validating that 'query' is present and is a string.
      2. We pass request.query to rag_service.query(), which performs:
           a. A FAISS similarity search to retrieve the most relevant context.
           b. Prompt construction using that context + the user's question.
           c. An LLM call that synthesizes a final, grounded answer.
      3. The answer string is returned as a JSON response: {"answer": "..."}.

    Args:
        request: A validated QueryRequest instance injected by FastAPI.

    Returns:
        A JSON object with a single key "answer" containing the LLM's response.

    Raises:
        HTTPException 500: If the RAG pipeline raises an unexpected error
                           (e.g., OpenAI API is unreachable), we catch it and
                           return a structured error to the client rather than
                           leaking an internal traceback.
    """
    try:
        # Delegate to the RAG service. This is the single point where all
        # intelligence-retrieval logic lives; the route stays thin and clean.
        answer = rag_service.query(request.query)
    except Exception as e:
        # Surface any upstream errors (network issues, API quota exceeded, etc.)
        # as a 500 so the client receives a meaningful JSON error body instead
        # of an unhandled server crash.
        raise HTTPException(status_code=500, detail=str(e))

    # Return a simple JSON envelope. Wrapping the answer in a keyed dict
    # (rather than returning a bare string) keeps the API response consistent
    # and easy to extend with additional fields (e.g., "sources", "confidence")
    # in future versions without breaking existing clients.
    return {"answer": answer}
