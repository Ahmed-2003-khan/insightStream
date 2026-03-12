"""
ingestion_pipeline/news_loader.py

Fetches competitive intelligence news using the Tavily API and chunks the
resulting articles into search-ready Document objects for the InsightStream RAG system.
"""

import os
from typing import List
from tavily import TavilyClient

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def ingest_news(query: str) -> List[Document]:
    """
    Fetches the top 5 news articles for a given topic using Tavily, and splits
    them into overlapping token chunks.

    Args:
        query: The search topic to find news for, e.g. "OpenAI product announcements".

    Returns:
        A list of Document chunks. Every chunk has metadata["source"] = "news" 
        and metadata["topic"] = query.
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key or tavily_api_key == "your_key_here":
        raise ValueError("TAVILY_API_KEY is not set or is invalid in .env")

    client = TavilyClient(api_key=tavily_api_key)

    # Fetch top 5 results for the given query from Tavily
    # We request full article content to get maximum context for chunking
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=5,
        include_raw_content=True
    )

    raw_documents = []
    
    # Process each article returned by Tavily
    for result in response.get("results", []):
        # Prefer raw_content if available, fallback to the snippet content
        content = result.get("raw_content") or result.get("content", "")
        if not content:
            continue
            
        doc = Document(
            page_content=content,
            metadata={
                "url": result.get("url", ""),
                "title": result.get("title", ""),
                "score": result.get("score", 0.0)
            }
        )
        raw_documents.append(doc)

    # Token-aware chunking matching the YouTube loader
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512,
        chunk_overlap=50,
    )

    chunked_documents = text_splitter.split_documents(raw_documents)

    # Tag every chunk with standard metadata for downstream filtering
    import hashlib
    for chunk in chunked_documents:
        chunk.metadata["source"] = "news"
        chunk.metadata["topic"] = query
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
        chunk.metadata["content_hash"] = content_hash

    return chunked_documents
