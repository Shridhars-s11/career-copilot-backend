from typing import TypedDict
from langgraph.graph import StateGraph, END,START

from app.tools.job_sources import fetch_all_jobs
from app.tools.matching import rank_jobs
from app.db.crud import save_job,save_application
from app.db.session import SessionLocal
from app.guardrails.policies import check_prompt_injection


class JobFinderState(TypedDict):
    profile_text: str
    skills: list[str]
    query: str
    resume_id: int
    matched_jobs: list[dict]


def job_finder_node(state: JobFinderState) -> JobFinderState:
    jobs = fetch_all_jobs(state["query"])
    top_jobs = rank_jobs(state["profile_text"], state["skills"], jobs, top_n=10)

    db = SessionLocal()

    for job in top_jobs:
        injection_check = check_prompt_injection(job['description'])
        if not injection_check["passed"]:
            continue
        job_id = save_job(db, job)
        job["id"] = job_id
        save_application(db, job_id=job_id, resume_id=state["resume_id"], match_score=job["match_score"])

    db.close()
    
    state["matched_jobs"] = top_jobs
    return state


graph = StateGraph(JobFinderState)
graph.add_node("job_finder",job_finder_node)
graph.add_edge(START,"job_finder")
graph.add_edge("job_finder",END)
app = graph.compile()