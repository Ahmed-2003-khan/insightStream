"""
ingestion_pipeline/youtube_loader.py

This module is responsible for the first stage of the InsightStream RAG pipeline:
ingesting raw video content from YouTube and converting it into structured,
search-ready Document chunks.

The pipeline works in two phases:
  1. LOADING   — YoutubeLoader fetches the video's auto-generated or manual
                 transcript via the YouTube Transcript API and wraps it in a
                 LangChain Document object.
  2. CHUNKING  — RecursiveCharacterTextSplitter.from_tiktoken_encoder breaks that
                 single large Document into smaller, overlapping chunks measured in
                 TOKENS (not characters), ensuring each chunk fits within an
                 embedding model's context window precisely.

The resulting list of Document chunks is designed to be passed directly into
the Pinecone vector store (via services/rag_service.py) for indexing.
"""

from typing import List

# YoutubeLoader is a LangChain community document loader that wraps the
# youtube-transcript-api library. Given a public YouTube video URL, it fetches
# the video's transcript and returns it as a list of LangChain Document objects,
# each containing the full transcript text and metadata like the video URL.
from langchain_community.document_loaders import YoutubeLoader

# RecursiveCharacterTextSplitter is LangChain's recommended general-purpose
# splitter. The from_tiktoken_encoder() class method replaces the default
# character-based length function with tiktoken's token counter, ensuring that
# chunk_size and chunk_overlap are measured in TOKENS rather than raw characters.
# This is more accurate for language models, which have token-based context limits.
from langchain_text_splitters import RecursiveCharacterTextSplitter

# LangChain's core Document schema. A Document holds:
#   - page_content (str): the raw text of this chunk.
#   - metadata (dict): arbitrary key/value pairs (e.g., source URL, timestamps).
from langchain_core.documents import Document


def ingest_youtube_video(video_url: str) -> List[Document]:
    """
    Loads a YouTube video transcript and splits it into overlapping token chunks.

    This function performs:
      1. Transcript fetching via YoutubeLoader.
      2. Token-aware chunking via RecursiveCharacterTextSplitter.from_tiktoken_encoder.
      3. Source metadata tagging so every chunk carries {"source": "youtube"}.

    The resulting Document chunks are ready to be embedded and stored in a
    vector database for semantic search and RAG-based question answering.

    Args:
        video_url: The full public URL of the YouTube video whose transcript
                   should be ingested. Example:
                   "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    Returns:
        A list of Document objects, each representing a meaningful token chunk
        from the transcript. Every chunk has metadata["source"] = "youtube" so
        downstream consumers can filter or cite by source type.

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
    # from_tiktoken_encoder() uses tiktoken (OpenAI's tokeniser) as the length
    # function instead of Python's len(). This ensures:
    #   - chunk_size=512 limits each chunk to 512 tokens — fits comfortably inside
    #     any OpenAI embedding model (text-embedding-ada-002 supports up to 8192).
    #   - chunk_overlap=50 means consecutive chunks share 50 tokens at their
    #     boundary, preventing a sentence that straddles a chunk boundary from
    #     being split in half and losing context.
    # The splitter still uses the recursive character hierarchy internally
    # (\\n\\n → \\n → space → char) to find natural split points.
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=512,
        chunk_overlap=50,
    )

    # split_documents() takes our list of raw Document objects and returns a
    # new (longer) list of smaller Document objects. Each child chunk inherits
    # the metadata of its parent Document (including the source URL populated
    # by YoutubeLoader).
    chunked_documents = text_splitter.split_documents(raw_documents)

    # ── Phase 3: Tag Every Chunk with Source Metadata ─────────────────────────
    # We explicitly set metadata["source"] = "youtube" on every chunk to make
    # the data provenance clear and filterable. YoutubeLoader does populate the
    # parent document's metadata with the video URL in the "source" field, but
    # we standardise it here to the string "youtube" so downstream consumers
    # (e.g., citation logic, source-specific filtering) can rely on a consistent
    # value regardless of which loader was used.
    import hashlib
    for chunk in chunked_documents:
        chunk.metadata["source"] = "youtube"
        content_hash = hashlib.md5(chunk.page_content.encode()).hexdigest()
        chunk.metadata["content_hash"] = content_hash

    return chunked_documents
