"""
ai_orchestration/graph.py

Compiles the LangGraph for the InsightStream reasoning engine.

ROUTING LOGIC EXPLAINED:
When a user asks a question, we first search our local database (Pinecone). 
If we find enough good information (at least 3 documents), we "proceed" straight 
to the analyst. 
If we don't find enough information, we trigger a "fallback". The fallback 
goes out to the internet, downloads fresh news about the topic, saves it to 
our database, and then tries the search again. 
To prevent the agent from getting stuck in an infinite loop of searching and 
failing, we track a "retry_count". If it has already retried once, we force 
it to "proceed" to the analyst with whatever information it has.
"""

from langgraph.graph import StateGraph, END
from ai_orchestration.state import AgentState
from ai_orchestration.nodes import query_planner_agent, search_agent, fallback_search_agent, analyst_agent, writer_agent

def should_fallback(state: AgentState) -> str:
    """
    Router function that determines if the graph needs to fetch external data.
    """
    if len(state["search_results"]) >= 3:
        return "proceed"
    
    if state["retry_count"] >= 1:
        return "proceed"
        
    return "fallback"

# 1. Initialize the graph with our shared state schema
graph_builder = StateGraph(AgentState)

# 2. Add all execution nodes
graph_builder.add_node("query_planner", query_planner_agent)
graph_builder.add_node("search", search_agent)
graph_builder.add_node("fallback_search", fallback_search_agent)
graph_builder.add_node("analyst", analyst_agent)
graph_builder.add_node("writer", writer_agent)

# 3. Define the entry point
graph_builder.set_entry_point("query_planner")
graph_builder.add_edge("query_planner", "search")

# 4. Add Conditional Routing from the initial search
graph_builder.add_conditional_edges(
    "search",
    should_fallback,
    {
        "proceed": "analyst",
        "fallback": "fallback_search"
    }
)

# 5. Add Conditional Routing from the fallback search
graph_builder.add_conditional_edges(
    "fallback_search",
    should_fallback,
    {
        "proceed": "analyst",
        "fallback": "analyst" # Safety net, should never hit this due to retry_count
    }
)

# 6. Add standard linear edges to finish the flow
graph_builder.add_edge("analyst", "writer")
graph_builder.add_edge("writer", END)

# 7. Compile the final runnable graph
intelligence_graph = graph_builder.compile()
