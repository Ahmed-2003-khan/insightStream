"""
ai_orchestration/nodes.py

Defines the individual execution nodes for the InsightStream reasoning graph.
Every node accepts the shared AgentState and returns the updated AgentState.
"""

import logging
from ai_orchestration.state import AgentState
from services.rag_service import BasicRAGService
from ingestion_pipeline.news_loader import ingest_news
from ml_models.signal_classifier import SignalClassifier
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

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
    query = state["query"]
    label = state["signal_label"]
    confidence = state["signal_confidence"]
    retry_count = state["retry_count"]
    
    # Format the evidence string for the prompt
    evidence = ""
    for idx, res in enumerate(state["search_results"], 1):
        evidence += f"Source {idx} ({res['source']}):\n{res['content']}\n\n"
        
    # Inject a transparency note if graph took extreme measures
    fallback_note = ""
    if retry_count > 0:
        fallback_note = "\nNOTE: Initial local data was insufficient. The system automatically fetched fresh external news data to fulfill this request.\n"

    system_prompt = (
        "You are an expert intelligence analyst summarizing information for executives. "
        "You must output a structured intelligence report with exactly these four sections: "
        "\n1. Summary\n2. Key Evidence\n3. Signal Classification\n4. Strategic Implication\n"
        "Do not include any other text."
    )
    
    user_prompt = (
        f"Query: {query}\n\n"
        f"AI Signal Classifier Output: {label} (Confidence: {confidence})\n"
        f"{fallback_note}\n"
        f"Evidence Context:\n{evidence}"
    )
        
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ])
    
    state["final_report"] = response.content
    return state
