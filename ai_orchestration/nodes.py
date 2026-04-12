"""
ai_orchestration/nodes.py

Defines the individual execution nodes for the InsightStream reasoning graph.
Every node accepts the shared AgentState and returns the updated AgentState.
"""

import logging
import os
from ai_orchestration.state import AgentState
from services.rag_service import BasicRAGService
from ingestion_pipeline.news_loader import ingest_news
from ml_models.signal_classifier import SignalClassifier
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

def query_planner_agent(state: AgentState) -> AgentState:
    """
    Dynamically generates a specific intelligence query based on
    company name and today's date. Replaces static hardcoded queries.
    """
    from langchain_openai import ChatOpenAI
    from datetime import datetime

    today = datetime.now().strftime("%B %d, %Y")
    company = state.get("company_name", "")

    # If no company name provided — user is querying directly via API
    # Skip planning and use existing query as is
    if not company:
        state["planned_query"] = state["query"]
        return state

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

    prompt = f"""You are a competitive intelligence analyst.
Today's date is {today}.
Generate ONE specific search query for gathering fresh intelligence about {company}.
The query must:
- Be specific to what is newsworthy about {company} right now
- Focus on one of: product launches, earnings, or geopolitical/regulatory news
- Include the current year
- Be between 8 and 15 words
Return only the query string. No explanation. No punctuation at the end."""

    response = llm.invoke(prompt)
    planned_query = response.content.strip()

    state["planned_query"] = planned_query
    state["query"] = planned_query
    return state


def search_agent(state: AgentState) -> AgentState:
    """
    Node 1: Executes semantic search against the Pinecone knowledge base.
    """
    query = state["query"]
    logger.info(f"[Node: search_agent] Searching Pinecone for: {query}")
    
    rag_service = BasicRAGService()
    
    # Use the underlying vector store's similarity_search to get Docs natively
    docs = rag_service.vector_store.similarity_search(query, k=5)
    
    results = []
    for doc in docs:
        results.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown")
        })
        
    state["search_results"] = results
    # Do not alter retry_count here
    return state


def fallback_search_agent(state: AgentState) -> AgentState:
    """
    Node 2: Automatically enriches the knowledge base when local data is insufficient,
    then retries the Pinecone search.
    """
    query = state["query"]
    logger.warning(f"[Node: fallback_search_agent] Insufficient data. Fetching live news for: {query}")
    
    try:
        # Step A: Ingest fresh data
        docs = ingest_news(query)
        
        # Step B: Insert into Pinecone
        rag_service = BasicRAGService()
        rag_service.store_documents(docs)
        
        # Step C: Re-query Pinecone now that the new data is searchable vectors
        fresh_docs = rag_service.vector_store.similarity_search(query, k=5)
        
        results = []
        for doc in fresh_docs:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "news")
            })
            
        state["search_results"] = results
        
    except Exception as e:
        logger.error(f"Fallback search failed: {e}")
        # Note: If ingestion fails, search_results remains whatever it was,
        # but the retry_count prevents looping infinitely.
        
    state["retry_count"] += 1
    return state


def analyst_agent(state: AgentState) -> AgentState:
    """
    Node 3: Applies an ML classification model to the retrieved text context
    to determine the signal sentiment/category.
    """
    logger.info("[Node: analyst_agent] Analyzing text for intelligence signals.")
    classifier = SignalClassifier()
    
    # Combine all found context into a single analytical block
    combined_text = "\\n\\n".join([item["content"] for item in state["search_results"]])
    
    # If there is absolutely no text, we just return nothing
    if not combined_text:
        state["signal_label"] = "NONE"
        state["signal_confidence"] = 0.0
        return state
        
    prediction = classifier.predict(combined_text)
    
    state["signal_label"] = prediction["label"]
    state["signal_confidence"] = prediction["confidence"]
    return state


def writer_agent(state: AgentState) -> AgentState:
    """
    Node 4: Uses a generative LLM to synthesize all context and signals into
    a structured intelligence report.
    """
    logger.info("[Node: writer_agent] Drafting final intelligence report.")

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )

    history = state.get("conversation_history", [])
    history_text = ""
    if history:
        history_text = "\nPrevious conversation:\n"
        for msg in history[-4:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:200]
            history_text += f"{role.upper()}: {content}\n"
        history_text += "\n"

    prompt = f"""{history_text}Current query: {state['query']}

Evidence from retrieved sources:
{chr(10).join([f"[{r.get('source','unknown')}]: {r.get('content','')}" for r in state['search_results']])}

Signal Classification: {state['signal_label']} (confidence: {state['signal_confidence']})
{"Note: Fresh news was automatically fetched for this query." if state['retry_count'] > 0 else ""}

Write a structured intelligence report with exactly these four sections:

SUMMARY:
[2-3 sentences — if there is conversation history, make sure this response is contextually connected]

KEY EVIDENCE:
[specific facts from the sources]

SIGNAL CLASSIFICATION:
[explain why this signal label was assigned]

STRATEGIC IMPLICATION:
[what this means for competitors]
"""

    response = llm.invoke(prompt)
    state["final_report"] = response.content
    return state
