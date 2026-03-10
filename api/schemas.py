"""
api/schemas.py

Pydantic request/response schemas for the InsightStream API.

Centralising all models here keeps routes.py focused purely on routing logic
and makes schemas easy to reuse across multiple route modules as the API grows.
"""

from pydantic import BaseModel


class IngestRequest(BaseModel):
    """
    Request body for POST /api/v1/intelligence/ingest.

    Attributes:
        video_url: The full public URL of the YouTube video to ingest,
                   e.g. "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    """

    video_url: str


class QueryRequest(BaseModel):
    """
    Request body for POST /api/v1/intelligence/query.

    Attributes:
        query: The natural-language question the user wants answered,
               e.g. "What is TechNova's latest product launch?"
    """

    query: str
