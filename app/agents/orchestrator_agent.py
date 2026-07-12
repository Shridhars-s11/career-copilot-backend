from pydantic import BaseModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command
from langgraph.graph import StateGraph, START, END

from app.agents.job_finder_agent import app as job_finder_app
from app.agents.resume_tailor_agent import app as resume_tailor_app
from app.db.crud import get_application_by_job_id, update_application_status
from app.db.models import ApplicationStatus
from app.db.session import SessionLocal


class OrchestratorState(BaseModel):
    profile_text: str = ""
    skills: list = []
    query: str = ""
    resume_id: int = 0
    matched_jobs: list = []
    best_job_id: int = None
    tailored_profile: dict = {}
    new_resume_id: int = None
    best_job_score: float = 0.0
    best_job_url: str = ""
    best_job_title: str = ""
    best_job_company: str = ""



def orchestrator_node(state: OrchestratorState) -> OrchestratorState:
    job_finder_input = {
        "profile_text": state.profile_text,
        "skills": state.skills,
        "query": state.query,
        "resume_id": state.resume_id,
        "matched_jobs": [],
    }
    job_finder_result = job_finder_app.invoke(job_finder_input)
    state.matched_jobs = job_finder_result['matched_jobs']

    best_job = max(state.matched_jobs, key=lambda x: x["match_score"])
    state.best_job_id = best_job['id']
    state.best_job_url = best_job['url']
    state.best_job_title = best_job['title']
    state.best_job_company = best_job['company']

    return state


def approval_node(state: OrchestratorState) -> OrchestratorState:
    decision = interrupt({
        "message": "Approve this application?",
        "job_id": state.best_job_id,
        "job_title": state.best_job_title,
        "company": state.best_job_company,
        "apply_url": state.best_job_url,
    })

    db = SessionLocal()
    application = get_application_by_job_id(db, state.best_job_id)
    if application is None:
        raise ValueError(f"No application found for job_id {state.best_job_id}")
    if decision == "approve":
        update_application_status(db, application.id, ApplicationStatus.AWAITING_APPROVAL)
    else:
        update_application_status(db, application.id, ApplicationStatus.REJECTED)
    db.close()

    return state


graph = StateGraph(OrchestratorState)
graph.add_node("orchestrator", orchestrator_node)
graph.add_node("approval", approval_node)
graph.add_edge(START, "orchestrator")
graph.add_edge("orchestrator", "approval")
graph.add_edge("approval", END)

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)