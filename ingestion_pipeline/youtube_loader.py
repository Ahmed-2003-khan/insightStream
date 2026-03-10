"""
ingestion_pipeline/youtube_loader.py

This module is responsible for the first stage of the InsightStream RAG pipeline:
ingesting raw video content from YouTube and converting it into structured,
search-ready Document chunks.

The pipeline works in two phases:
  1. LOADING   — YoutubeLoader fetches the video's auto-generated or manual
                 transcript via the YouTube Transcript API and wraps it in a
                 LangChain Document object.
  2. CHUNKING  — RecursiveCharacterTextSplitter breaks that single large Document
                 into smaller, overlapping chunks so that each chunk fits
                 comfortably inside an embedding model's context window and
                 represents a focused, coherent idea rather than an entire video.

The resulting list of Document chunks is designed to be passed directly into
a FAISS vector store (such as the one in services/rag_service.py) for indexing.
"""

from typing import List

# YoutubeLoader is a LangChain community document loader that wraps the
# youtube-transcript-api library. Given a public YouTube video URL, it fetches
# the video's transcript and returns it as a list of LangChain Document objects,
# each containing the full transcript text and metadata like the video URL.
from langchain_community.document_loaders import YoutubeLoader

# RecursiveCharacterTextSplitter is LangChain's recommended general-purpose
# splitter. It attempts to split on natural language boundaries in this order:
# paragraphs ("\n\n") → sentences ("\n") → words (" ") → characters ("").
# This hierarchy preserves semantic coherence as much as possible.
from langchain_text_splitters import RecursiveCharacterTextSplitter

# LangChain's core Document schema. A Document holds:
#   - page_content (str): the raw text of this chunk.
#   - metadata (dict): arbitrary key/value pairs (e.g., source URL, timestamps).
from langchain_core.documents import Document


def ingest_youtube_video(video_url: str) -> List[Document]:
    """
    Loads a YouTube video transcript and splits it into overlapping text chunks.

    This function performs:
      1. Transcript fetching via YoutubeLoader.
      2. Text chunking via RecursiveCharacterTextSplitter.

    The resulting Document chunks are ready to be embedded and stored in a
    vector database for semantic search and RAG-based question answering.

    Args:
        video_url: The full public URL of the YouTube video whose transcript
                   should be ingested. Example:
                   "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    Returns:
        A list of Document objects, each representing a meaningful text chunk
        from the transcript. The metadata on each Document inherits the source
        URL populated by YoutubeLoader, so we always know which video a chunk
        came from.

    Raises:
        Exception: Propagates any error from the YouTube Transcript API
                   (e.g., transcripts disabled, private video, invalid URL).
    """

    # ── Phase 1: Load the Transcript ─────────────────────────────────────────
    # YoutubeLoader.from_youtube_url() creates a loader instance bound to the
    # given URL. Setting add_video_info=False skips an extra API call to fetch
    # the video title and author — we only need the transcript text here.
    # .load() executes the network request and returns a list of Document objects.
    # For most videos this list contains a single Document whose page_content
    # is the full transcript as one long string.
    loader = YoutubeLoader.from_youtube_url(
        video_url,
        add_video_info=False,  # Set to True if you later want title/author in metadata
    )
    raw_documents = loader.load()

    # ── Phase 2: Chunk the Transcript ─────────────────────────────────────────
    # A full video transcript can easily exceed 10,000+ words — far too large
    # to embed as a single vector (embedding models have token limits) and too
    # broad to retrieve usefully (a 10k-word chunk provides poor signal).
    #
    # chunk_size=1000 limits each chunk to ~1000 characters. This is a
    # deliberate balance: large enough to contain a coherent idea (a few
    # sentences of discussion), small enough to fit any embedding model and
    # to be precise when retrieved.
    #
    # chunk_overlap=100 means consecutive chunks share 100 characters at their
    # boundary. This prevents a sentence that straddles a chunk boundary from
    # being split in half and losing its context — the overlapping region ensures
    # that meaning is never accidentally cut off at the seam between two chunks.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
    )

    # split_documents() takes our list of raw Document objects and returns a
    # new (longer) list of smaller Document objects. Each child chunk inherits
    # the metadata of its parent Document (including the source URL), so
    # provenance is preserved automatically throughout the chunk list.
    chunked_documents = text_splitter.split_documents(raw_documents)

    return chunked_documents
