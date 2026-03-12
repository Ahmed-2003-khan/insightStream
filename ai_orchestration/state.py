"""
ai_orchestration/state.py

Defines the shared state for the InsightStream reasoning graph.
"""

from typing import TypedDict, List

class AgentState(TypedDict):
    """
    The shared state dictionary passed between all nodes in the graph.
    Every node reads from and/or writes to this state structure.
    """
    query: str
    search_results: list
    signal_label: str
    signal_confidence: float
    final_report: str
    retry_count: int
