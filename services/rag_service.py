"""
services/rag_service.py

This module is the core of the InsightStream intelligence engine.
It contains the BasicRAGService class, which is responsible for:
  1. Embedding textual knowledge into a vector space using OpenAI embeddings.
  2. Storing and persisting those vectors in a Pinecone index — a managed,
     cloud-native vector database that survives restarts and scales horizontally.
  3. Retrieving the most semantically relevant pieces of knowledge given a
     user's query, and using an LLM to synthesize a final, grounded answer.

Why Pinecone over an in-memory store?
  An in-memory vector store is useful for prototyping — it is fast and needs
  zero infrastructure — but it is destroyed whenever the process restarts.
  Pinecone persists vectors across deployments, supports real-time upserts
  from multiple sources (e.g., the YouTube ingestion pipeline), and provides
  sub-millisecond ANN (Approximate Nearest Neighbour) search at scale.
  This makes it the right choice for a production intelligence engine.
"""

import os
from typing import List

from dotenv import load_dotenv

# LangChain's core Document schema.
# A Document bundles page_content (str) with an optional metadata dict,
# propagating source information (URL, timestamps, etc.) throughout the pipeline.
from langchain_core.documents import Document

# PineconeVectorStore is LangChain's official integration with Pinecone.
# It wraps the Pinecone client and exposes the familiar LangChain vector-store
# interface (from_documents, add_documents, similarity_search) so the rest of
# the RAG pipeline stays unchanged regardless of the underlying store.
from langchain_pinecone import PineconeVectorStore

# OpenAIEmbeddings converts text into high-dimensional float vectors.
# Every document stored in Pinecone and every incoming query is first passed
# through this model so they share the same vector space — a prerequisite for
# meaningful similarity search.
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# PromptTemplate defines a reusable prompt structure with named placeholders
# ({context}, {question}) that are filled in at query time.
from langchain_core.prompts import PromptTemplate


class BasicRAGService:
    """
    A cloud-backed Retrieval-Augmented Generation (RAG) service for InsightStream.

    On initialization this service:
      - Loads all credentials (OpenAI + Pinecone) from environment variables.
      - Reads the Pinecone index name from the PINECONE_INDEX_NAME env var.
      - Instantiates the embedding model and the chat LLM.
      - Connects to the existing Pinecone index and seeds it with a baseline
        corpus of competitive intelligence about TechNova.

    After initialization the service exposes two public methods:
      - store_documents(documents): persists new Document chunks to Pinecone.
      - query(user_prompt):         retrieves relevant context and returns an
                                    LLM-synthesized answer.
    """

    def __init__(self):
        """
        Bootstraps the RAG pipeline:
          1. Loads environment variables (.env → os.environ).
          2. Reads PINECONE_INDEX_NAME from the environment.
          3. Initialises the embedding model and the LLM.
          4. Connects to the Pinecone vector store.
          5. Seeds the index with the hardcoded TechNova intelligence corpus.
        """

        # load_dotenv() reads the project-root .env file and injects its
        # key=value pairs into the process environment. This means neither
        # OPENAI_API_KEY nor PINECONE_API_KEY ever appear in source code.
        load_dotenv()

        # ── Pinecone Index Name ───────────────────────────────────────────────
        # Reading the index name from an environment variable (set in .env as
        # PINECONE_INDEX_NAME=insightstream) means we can point the service at a
        # different index per environment (dev, staging, prod) without touching
        # application code. If the variable is absent, we raise immediately with
        # a clear error rather than failing later with a cryptic Pinecone 404.
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        if not pinecone_index_name:
            raise ValueError(
                "PINECONE_INDEX_NAME environment variable is not set. "
                "Add PINECONE_INDEX_NAME=insightstream to your .env file."
            )

        # ── Embedding Model ──────────────────────────────────────────────────
        # OpenAIEmbeddings uses "text-embedding-ada-002" by default, producing
        # 1536-dimensional vectors. It reads OPENAI_API_KEY from the environment.
        # Both storage (via store_documents) and retrieval (via query) use this
        # same model instance to guarantee vectors live in the same space.
        self.embeddings = OpenAIEmbeddings()

        # ── Language Model ───────────────────────────────────────────────────
        # ChatOpenAI wraps the OpenAI Chat Completions API.
        # gpt-4o-mini is chosen for its speed and cost efficiency while still
        # producing high-quality analytical summaries.
        # temperature=0 forces the model to be deterministic and factual —
        # essential for competitive intelligence where consistency matters.
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # ── Connect to the Pinecone Vector Store ─────────────────────────────
        # PineconeVectorStore.from_existing_index() establishes a connection to
        # an index that already exists in our Pinecone project. Unlike
        # from_documents(), this call does NOT embed or upload anything — it
        # simply creates a client handle so we can run similarity_search() and
        # add_documents() against the live index.
        #
        # The Pinecone client reads PINECONE_API_KEY (and optionally
        # PINECONE_ENVIRONMENT) from the environment automatically.
        self.vector_store = PineconeVectorStore.from_existing_index(
            index_name=pinecone_index_name,
            embedding=self.embeddings,
        )

        # ── Seed the Index with the Baseline Intelligence Corpus ─────────────
        # These three facts about TechNova represent the initial, curated
        # knowledge base of InsightStream. In production, this corpus would be
        # replaced by dynamic ingestion (e.g., via the YouTube loader pipeline),
        # but seeding the index here ensures the service can answer questions
        # immediately after the first deploy — useful for smoke-testing the
        # end-to-end pipeline without running a separate ingestion job.
        seed_intelligence = [
            (
                "TechNova launched its flagship AI-powered analytics platform, "
                "NovaSight 2.0, in Q1 2025. The release introduced real-time "
                "anomaly detection and a natural language querying interface, "
                "targeting enterprise clients in the finance and healthcare sectors."
            ),
            (
                "TechNova appointed Dr. Priya Mehta as its new Chief Technology "
                "Officer in February 2025, replacing the outgoing CTO Marcus Webb. "
                "Dr. Mehta joins from DeepScale AI and is expected to accelerate "
                "TechNova's push into edge computing and on-device inference."
            ),
            (
                "TechNova secured a $120 million Series C funding round led by "
                "Horizon Ventures in March 2025. The capital is earmarked for "
                "expanding its European go-to-market team and doubling down on "
                "its R&D efforts around multimodal AI models."
            ),
        ]

        seed_documents = [
            Document(page_content=text, metadata={"source": f"technova_brief_{i}"})
            for i, text in enumerate(seed_intelligence)
        ]

        # Persist the seed corpus to Pinecone via store_documents so the
        # seeding and dynamic ingestion codepaths share a single implementation.
        self.store_documents(seed_documents)

    # ──────────────────────────────────────────────────────────────────────────
    # Public Methods
    # ──────────────────────────────────────────────────────────────────────────

    def store_documents(self, documents: List[Document]) -> None:
        """
        Embeds and persists a list of Document chunks into the Pinecone index.

        This method is the bridge between the ingestion pipeline
        (ingestion_pipeline/youtube_loader.py → chunked Document objects) and
        the vector store. Calling it is idempotent in terms of retrieval quality:
        if you ingest the same content twice, Pinecone will store duplicate
        vectors, so callers should deduplicate before ingesting if needed.

        Args:
            documents: A list of LangChain Document objects. Each Document's
                       page_content is embedded and its metadata (source URL,
                       timestamps, etc.) is stored alongside the vector so that
                       provenance information survives into retrieval results.
        """

        # add_documents() does two things:
        #   1. Calls self.embeddings.embed_documents() to convert each
        #      Document's page_content into a float vector.
        #   2. Upserts those vectors (with their metadata) into the live
        #      Pinecone index identified by pinecone_index_name.
        # Upserting is non-blocking in Pinecone — vectors become searchable
        # within a few seconds of the call returning.
        self.vector_store.add_documents(documents)

    def query(self, user_prompt: str) -> str:
        """
        Executes a RAG query by submitting the user's prompt to the compiled
        LangGraph reasoning engine (intelligence_graph).
        
        The graph will automatically handle:
          1. Searching Pinecone.
          2. Fallback fetching of external data (if Pinecone is lacking).
          3. ML signal classification of the context.
          4. Final LLM synthesis of the intelligence report.
        """
        from ai_orchestration.graph import intelligence_graph

        # We construct the initial AgentState to feed into the graph
        result = intelligence_graph.invoke({
            "query": user_prompt,
            "search_results": [],
            "signal_label": "",
            "signal_confidence": 0.0,
            "final_report": "",
            "retry_count": 0
        })

        # Save the generated report to PostgreSQL before returning
        from core_backend.database import SessionLocal
        from core_backend.models import Report
        
        db = SessionLocal()
        try:
            sources = ", ".join([r.get("source", "unknown") for r in result.get("search_results", [])])
            report_record = Report(
                query        = user_prompt,
                signal_label = result.get("signal_label", "UNKNOWN"),
                confidence   = result.get("signal_confidence", 0.0),
                report_text  = result.get("final_report", ""),
                sources      = sources
            )
            db.add(report_record)
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Database save error: {e}")
        finally:
            db.close()
        
        # The node writer_agent populates "final_report" at the end of the graph execution
        return result["final_report"]
