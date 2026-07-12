from app.db.crud import get_all_performance_scores
from app.db.session import SessionLocal
from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END


class PerformanceAnalystState(BaseModel):
    trends: dict = {}


def build_score_trends(db) -> dict:
    """Groups all performance scores by category into chronological trend lists.
    Returns: {"technical": [{"date": ..., "score": ...}, ...], "communication": [{"date": ..., "score": ...}, ...]}"""
    scores = get_all_performance_scores(db)

    trends = {}
    for s in scores:
        if s.category not in trends:
            trends[s.category] = []
        trends[s.category].append({"date":s.created_at,"score":s.score})
    return trends


def performance_analyst_node(state: PerformanceAnalystState) -> PerformanceAnalystState:
    db = SessionLocal()
    state.trends = build_score_trends(db)
    db.close()
    return state

graph = StateGraph(PerformanceAnalystState)
graph.add_node("performance_analyst",performance_analyst_node)
graph.add_edge(START,"performance_analyst")
graph.add_edge("performance_analyst",END)
app = graph.compile()