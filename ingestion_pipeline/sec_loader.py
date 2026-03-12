"""
ingestion_pipeline/sec_loader.py

Downloads and processes SEC 10-K filings for competitive intelligence analysis.
Supports ticker-based downloading, content extraction, and standard chunking.
"""

import os
import shutil
from typing import List
from sec_edgar_downloader import Downloader

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

def ingest_sec_filing(ticker: str) -> List[Document]:
    """
    Downloads the latest 10-K filing for a given ticker, extracts text,
    and chunks it for insertion into the InsightStream RAG system.

    Args:
        ticker: The stock ticker symbol (e.g., "MSFT", "AAPL").

    Returns:
        A list of Document chunks with SEC-specific metadata.
    """
    # 1. Setup the downloader. We use "InsightStream/1.0" as the User-Agent
    # to comply with SEC EDGAR access rules.
    # The files will be saved in a temporary 'sec_data' directory.
    download_dir = "sec_data"
    dl = Downloader("InsightStream", "admin@insightstream.ai", download_dir)
    
    # 2. Download the latest 10-K
    # This creates a folder structure like: sec_data/sec-edgar-filings/MSFT/10-K/...
    dl.get("10-K", ticker, limit=1)
    
    # 3. Locate the downloaded file
    # We iterate to find the actual .txt or .html filing content
    ticker_dir = os.path.join(download_dir, "sec-edgar-filings", ticker, "10-K")
    if not os.path.exists(ticker_dir):
        raise FileNotFoundError(f"Could not find SEC filing directory for {ticker}")
        
    documents = []
    
    # Walk through the ticker directory to find the actual filing file
    for root, dirs, files in os.walk(ticker_dir):
        for file in files:
            if file.endswith((".txt", ".html")):
                file_path = os.path.join(root, file)
                
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    # Limit to first 40,000 characters to keep context clean 
                    # as per requirements (SEC filings are massive).
                    content = f.read(40000)
                    
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": "sec",
                        "filing_type": "10-K",
                        "ticker": ticker,
                    }
                )
                documents.append(doc)
                break # We only need the one latest 10-K
        if documents:
            break

    if not documents:
        # Cleanup before raising
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir)
        raise ValueError(f"No valid 10-K filing text found for {ticker}")

    # 4. Chunk with the standard token-aware splitter
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512,
        chunk_overlap=50,
    )
    
    chunked_documents = text_splitter.split_documents(documents)
    
    # Ensure every chunk carries the necessary metadata (source is already in parent)
    # We add metadata here explicitly to be consistent with our news/youtube loaders.
    import hashlib
    for chunk in chunked_documents:
        chunk.metadata["source"] = "sec"
        chunk.metadata["filing_type"] = "10-K"
        chunk.metadata["ticker"] = ticker
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
        chunk.metadata["content_hash"] = content_hash

    # 5. Cleanup the downloaded files
    if os.path.exists(download_dir):
        shutil.rmtree(download_dir)
        
    return chunked_documents
