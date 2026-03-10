"""
services/rag_service.py

This module is the core of the InsightStream intelligence engine.
It contains the BasicRAGService class, which is responsible for:
  1. Embedding textual knowledge into a vector space.
  2. Storing those vectors in a fast, in-memory FAISS index.
  3. Retrieving the most semantically relevant pieces of knowledge
     given a user's query, and using an LLM to synthesize a final answer.

This pattern — Retrieval-Augmented Generation (RAG) — grounds the LLM's
response in specific, curated data rather than relying solely on its
pre-trained knowledge, which greatly reduces hallucinations.
"""

import os
from dotenv import load_dotenv

# LangChain's document schema. Even though our raw data is plain strings,
# FAISS works with Document objects so we convert our strings into this format.
# Note: In LangChain >= 0.1, Document moved from langchain.schema to langchain_core.documents.
from langchain_core.documents import Document

# The FAISS integration provided by LangChain. FAISS (Facebook AI Similarity
# Search) is an efficient library for similarity search over dense vector
# embeddings. We use the in-memory version here so no disk I/O is needed.
from langchain_community.vectorstores import FAISS

# OpenAIEmbeddings converts text strings into high-dimensional numerical
# vectors. Semantically similar texts will produce vectors that are close
# to each other in this vector space, which is what powers the similarity search.
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

# PromptTemplate lets us define a structured prompt with named placeholders
# (like {context} and {question}) that get filled in at runtime.
# Note: In LangChain >= 0.1, PromptTemplate moved from langchain.prompts to langchain_core.prompts.
from langchain_core.prompts import PromptTemplate


class BasicRAGService:
    """
    A basic Retrieval-Augmented Generation (RAG) service for InsightStream.

    On initialization, this service:
      - Loads API credentials from the environment.
      - Instantiates the embedding model and the language model.
      - Ingests a hardcoded corpus of competitive intelligence into a FAISS
        vector store, making it immediately ready to answer queries.
    """

    def __init__(self):
        """
        Sets up the entire RAG pipeline at startup time so that query()
        calls are fast (the embedding and indexing cost is paid once here,
        not on every request).
        """

        # load_dotenv() reads the .env file in the project root and injects
        # its key-value pairs as environment variables. This keeps secrets
        # (like OPENAI_API_KEY) out of source code entirely.
        load_dotenv()

        # ── Embedding Model ──────────────────────────────────────────────────
        # OpenAIEmbeddings uses the "text-embedding-ada-002" model by default.
        # It automatically reads OPENAI_API_KEY from the environment.
        # Every piece of text we want to store — and every query we receive —
        # will be passed through this model to get its vector representation.
        self.embeddings = OpenAIEmbeddings()

        # ── Language Model ───────────────────────────────────────────────────
        # ChatOpenAI wraps the OpenAI Chat Completions API. We use gpt-4o-mini
        # for a cost-efficient, fast model that is still highly capable for
        # synthesizing concise intelligence summaries.
        # temperature=0 makes responses deterministic and factual — important
        # for competitive intelligence where we want precision, not creativity.
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        # ── Knowledge Corpus ─────────────────────────────────────────────────
        # This is the "database" of competitive intelligence for TechNova.
        # In a production system, these strings would be ingested dynamically
        # from news feeds, reports, or databases. For this foundational build,
        # we hardcode three representative facts to validate the full pipeline.
        raw_intelligence = [
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

        # ── Convert Strings to LangChain Documents ───────────────────────────
        # FAISS.from_documents() expects Document objects. We wrap each raw
        # intelligence string in a Document, optionally attaching metadata
        # (source label here) that can be used for provenance tracking later.
        documents = [
            Document(page_content=text, metadata={"source": f"technova_brief_{i}"})
            for i, text in enumerate(raw_intelligence)
        ]

        # ── Build the FAISS Vector Store ─────────────────────────────────────
        # FAISS.from_documents() does two things in one call:
        #   1. Calls self.embeddings.embed_documents() on every Document's
        #      page_content, converting text → float vectors.
        #   2. Inserts those vectors into an in-memory FAISS index.
        # The resulting vector_store object exposes a similarity_search() method
        # that we will use inside query() to retrieve relevant context.
        self.vector_store = FAISS.from_documents(documents, self.embeddings)

    def query(self, user_prompt: str) -> str:
        """
        Answers a competitive intelligence question using the RAG pattern.

        Steps:
          1. Embed the user_prompt and find the top-k most similar Documents
             in the FAISS index (similarity search).
          2. Concatenate those Documents into a context string.
          3. Inject the context + question into a structured prompt template.
          4. Pass the filled-in prompt to the LLM and return its text reply.

        Args:
            user_prompt: The natural-language question from the user,
                         e.g. "What do we know about TechNova's leadership?"

        Returns:
            A string containing the LLM's synthesized answer, grounded in
            the retrieved context from our FAISS index.
        """

        # ── Step 1: Similarity Search ─────────────────────────────────────────
        # similarity_search() embeds the user_prompt using the same embedding
        # model used at ingestion time, then returns the k Documents whose
        # stored vectors are closest (most semantically similar) to the query vector.
        # k=2 means we retrieve the top 2 most relevant intelligence snippets.
        retrieved_docs = self.vector_store.similarity_search(user_prompt, k=2)

        # ── Step 2: Build the Context String ─────────────────────────────────
        # We join the page content of each retrieved document with a separator.
        # This combined text becomes the "context" the LLM is grounded in.
        # Keeping retrieved chunks clearly separated helps the model parse
        # multiple distinct facts without merging them incorrectly.
        context = "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)

        # ── Step 3: Construct the Prompt Template ────────────────────────────
        # PromptTemplate defines the exact structure of the message we send to
        # the LLM. The {context} and {question} placeholders are filled at
        # runtime via .format(). Instructing the model explicitly to answer
        # "only based on the context below" keeps it grounded and prevents
        # it from drifting into speculation unsupported by our data.
        prompt_template = PromptTemplate(
            input_variables=["context", "question"],
            template=(
                "You are a precise competitive intelligence analyst for InsightStream.\n"
                "Answer the question below using ONLY the context provided.\n"
                "If the context does not contain enough information, say so clearly.\n\n"
                "Context:\n{context}\n\n"
                "Question: {question}\n\n"
                "Answer:"
            ),
        )

        # Fill in the template placeholders with our runtime values.
        filled_prompt = prompt_template.format(context=context, question=user_prompt)

        # ── Step 4: Call the LLM and Return the Response ─────────────────────
        # self.llm.invoke() sends the filled prompt to the OpenAI Chat API
        # and returns an AIMessage object. We access .content to get the
        # plain string text of the model's reply.
        response = self.llm.invoke(filled_prompt)

        return response.content
