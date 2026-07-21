from sqlalchemy.orm import Session
from app.tools.embeddings import embed_text
from app.db.models import Resume, Job, Application, ApplicationStatus,InterviewSession, PerformanceScore
from sqlalchemy import select


def save_resume(db: Session, raw_text: str, profile_summary: str, version_label: str = "master", is_master: bool = True) -> int:
    """Creates a new Resume row, returns its id."""
    resume = Resume(
        version_label=version_label,
        raw_text=raw_text,
        profile_summary=profile_summary,
        is_master=is_master,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume.id


def save_job(db: Session, job: dict) -> int:
    """Creates a new Job row from a normalized job dict, returns its id."""
    job_embeds = embed_text(job['description'])

    new_job = Job(
        source = job['source'],
        external_id = job['external_id'],
        title = job['title'],
        company = job['company'],
        location = job['location'],
        description = job['description'],
        url = job['url'],
        embedding = job_embeds
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job.id


def save_application(db: Session, job_id: int, resume_id: int, match_score: float = None) -> int:
    """Creates a new Application row linking a job and a resume, returns its id."""
    new_application = Application(
        job_id = job_id,
        resume_id = resume_id,
        match_score=match_score,
        status = ApplicationStatus.DRAFT
        )
    
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    
    return new_application.id


def save_interview_session(db: Session, job_id: int, transcript: str, feedback: str,
                             technical_score: float, communication_score: float) -> int:
    """Creates an InterviewSession row plus two linked PerformanceScore rows (technical + communication)."""
    interview_sessions = InterviewSession(
        job_id = job_id,
        transcript = transcript,
        feedback = feedback
    )
    db.add(interview_sessions)
    db.commit()
    db.refresh(interview_sessions)

    technical_score_row = PerformanceScore(
        session_id = interview_sessions.id,
        category = "technical",
        score = technical_score
    )

    communication_score_row = PerformanceScore(
        session_id = interview_sessions.id,
        category = "communication",
        score = communication_score
    )

    db.add(technical_score_row)
    db.add(communication_score_row)
    db.commit()

    return interview_sessions.id


def get_resume_by_id(db: Session, resume_id: int) -> Resume | None:
    return db.get(Resume,resume_id)


def get_job_by_id(db: Session, job_id: int) -> Job | None:
    return db.get(Job,job_id)


def get_all_performance_scores(db: Session) -> list[PerformanceScore]:
    """Returns every PerformanceScore row across all sessions, oldest first."""
    statement = select(PerformanceScore).order_by(PerformanceScore.created_at)
    scores = db.scalars(statement).all()
    return scores


def get_application_by_job_id(db: Session, job_id: int) -> Application | None:
    """Returns the Application row linked to a given job_id, or None."""
    statement = select(Application).where(Application.job_id == job_id)
    return db.scalars(statement).first()


def update_application_status(db: Session, application_id: int, new_status: ApplicationStatus) -> None:
    """Updates an existing Application's status."""
    application = db.get(Application,application_id)
    if application:
        application.status = new_status
    db.commit()
    

def get_all_resumes(db: Session) -> list[Resume]:
    """Returns every resume, newest first."""
    statement = select(Resume).order_by(Resume.created_at.desc())
    return db.scalars(statement).all()