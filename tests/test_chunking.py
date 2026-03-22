from langchain_core.documents import Document

def test_youtube_loader_returns_documents():
    from unittest.mock import patch
    with patch("ingestion_pipeline.youtube_loader.YoutubeLoader") as mock_loader:
        mock_loader.from_youtube_url.return_value.load.return_value = [
            Document(page_content="This is test transcript content " * 50,
                    metadata={"source": "youtube"})
        ]
        from ingestion_pipeline.youtube_loader import ingest_youtube_video
        docs = ingest_youtube_video("https://youtube.com/watch?v=test")
        assert len(docs) > 0
        assert all(isinstance(d, Document) for d in docs)

def test_youtube_chunks_have_source_metadata():
    from unittest.mock import patch
    with patch("ingestion_pipeline.youtube_loader.YoutubeLoader") as mock_loader:
        mock_loader.from_youtube_url.return_value.load.return_value = [
            Document(page_content="Test content " * 100,
                    metadata={})
        ]
        from ingestion_pipeline.youtube_loader import ingest_youtube_video
        docs = ingest_youtube_video("https://youtube.com/watch?v=test")
        assert all(d.metadata.get("source") == "youtube" for d in docs)

def test_chunks_have_content_hash_metadata():
    from unittest.mock import patch
    with patch("ingestion_pipeline.youtube_loader.YoutubeLoader") as mock_loader:
        mock_loader.from_youtube_url.return_value.load.return_value = [
            Document(page_content="Test content " * 100,
                    metadata={})
        ]
        from ingestion_pipeline.youtube_loader import ingest_youtube_video
        docs = ingest_youtube_video("https://youtube.com/watch?v=test")
        assert all("content_hash" in d.metadata for d in docs)

def test_chunk_size_is_reasonable():
    from unittest.mock import patch
    with patch("ingestion_pipeline.youtube_loader.YoutubeLoader") as mock_loader:
        long_content = "word " * 2000
        mock_loader.from_youtube_url.return_value.load.return_value = [
            Document(page_content=long_content, metadata={})
        ]
        from ingestion_pipeline.youtube_loader import ingest_youtube_video
        docs = ingest_youtube_video("https://youtube.com/watch?v=test")
        # Each chunk should not be excessively long
        for doc in docs:
            assert len(doc.page_content.split()) <= 600
