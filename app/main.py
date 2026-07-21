import uuid
import json
import shutil
from fastapi import FastAPI, Depends ,UploadFile, File ,HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.tools.resume_parser import extract_raw_text, build_structured_profile
from app.db.crud import save_resume,save_interview_session,get_resume_by_id, get_all_resumes
from app.db.session import get_db
from app.agents.orchestrator_agent import app as orchestrator_app, OrchestratorState
from app.agents.interview_coach_agent import app as interview_coach_app, InterviewCoachState,generate_interview_question, evaluate_interview_answer
from app.agents.resume_tailor_agent import tailor_resume_for_job
from app.agents.performance_analyst_agent import build_score_trends
from app.guardrails.policies import check_resume_honesty
from langgraph.types import Command

api = FastAPI(title="Career Copilot")


api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://career-copilot-frontend-82uu.onrender.com"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class OrchestratorRequest(BaseModel):
    profile_text: str
    skills: list[str]
    query: str
    resume_id: int


class InterviewRequest(BaseModel):
    job_id: int
    user_answer: str


@api.post("/interview/practice")
def practice_interview(request: InterviewRequest):
    """Generates a question for this job and evaluates the given answer."""
    result = interview_coach_app.invoke(InterviewCoachState(
        job_id =request.job_id,
        user_answer=request.user_answer,
        question="",
        feedback="",
        technical_score=0,
        communication_score=0,
        session_id=None,
    ))
    return {
        "question":result['question'],
        "feedback":result['feedback'],
        "technical_score":result['technical_score'],
        "communication_score":result['communication_score'],
    }

@api.post("/run-job-search")
def run_job_search(request: OrchestratorRequest):
    """Runs the pipeline up to the approval pause point. Returns a thread_id to resume later."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    result = orchestrator_app.invoke(OrchestratorState(
        profile_text=request.profile_text,
        skills=request.skills,
        query=request.query,
        resume_id=request.resume_id,
    ), config=config)

    interrupt_data = result["__interrupt__"][0].value
    return {
        "thread_id": thread_id,
        "job_id": interrupt_data["job_id"],
        "job_title": interrupt_data["job_title"],
        "company": interrupt_data["company"],
        "apply_url": interrupt_data["apply_url"],
        "message": interrupt_data["message"],
    }


class ApprovalRequest(BaseModel):
    thread_id: str
    decision: str  # "approve" or "reject"


@api.post("/application/approve")
def approve_application(request: ApprovalRequest):
    """Resumes a paused orchestrator run with the given decision."""
    config = {"configurable":{"thread_id":request.thread_id}}

    result = orchestrator_app.invoke(Command(resume=request.decision),
                                     config = config)
    
    return {
        "thread_id":request.thread_id,
        "decision_made":request.decision,
        "workflow_finished":result.get("__interrupt__") is None,
    }


class QuestionRequest(BaseModel):
    job_id: int


@api.post("/interview/question")
def get_interview_question(request: QuestionRequest, db: Session = Depends(get_db)):
    """Step 1: generates a question for this job, no answer yet."""
    return generate_interview_question(db, request.job_id)


class AnswerRequest(BaseModel):
    job_id: int
    question: str
    user_answer: str


@api.post("/interview/answer")
def submit_interview_answer(request: AnswerRequest, db: Session = Depends(get_db)):
    """Step 2: evaluates the given answer, saves the session + scores."""
    result = evaluate_interview_answer(request.question, request.user_answer)
    session_id = save_interview_session(
        db, request.job_id, request.user_answer,
        result["feedback"], result["technical_score"], result["communication_score"],
    )
    result["session_id"] = session_id
    return result

UPLOAD_DIR = Path("data/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@api.post("/resume/upload")
def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Saves an uploaded resume, extracts + structures it, stores as a new master resume."""
    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    raw_text = extract_raw_text(str(dest))
    profile_json = build_structured_profile(raw_text)

    resume_id = save_resume(
        db, raw_text=raw_text, profile_summary=profile_json,
        version_label="master", is_master=True,
    )
    return {"resume_id": resume_id, "profile": json.loads(profile_json)}


class TailorRequest(BaseModel):
    resume_id: int
    job_id: int


@api.post("/resume/tailor")
def tailor_resume(request: TailorRequest, db: Session = Depends(get_db)):
    tailored = tailor_resume_for_job(db, request.resume_id, request.job_id)
    honesty_check = check_resume_honesty(tailored["summary"])
    if not honesty_check["passed"]:
        raise HTTPException(status_code=422, detail=f"Fabrication detected: {honesty_check['flagged_terms']}")

    original = get_resume_by_id(db, request.resume_id)
    new_id = save_resume(
        db, original.raw_text, json.dumps(tailored),
        version_label=f"tailored-for-job-{request.job_id}", is_master=False,
    )
    return {"new_resume_id": new_id, "tailored_profile": tailored}

@api.get("/performance/trends")
def get_progress_trends(db: Session = Depends(get_db)):
    return build_score_trends(db)

@api.get("/resumes")
def list_resumes(db: Session = Depends(get_db)):
    resumes = get_all_resumes(db)
    return [
        {
            "id": r.id,
            "version_label": r.version_label,
            "is_master": r.is_master,
            "created_at": r.created_at.isoformat(),
        }
        for r in resumes
    ]