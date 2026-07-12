from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
 
from sqlalchemy import String, Text, ForeignKey, DateTime, Enum, Float, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
 
# all-MiniLM-L6-v2 via sentence-transformers: free, runs locally, 384-dim.
# No API cost for embeddings — only Claude calls hit your budget.
EMBEDDING_DIM = 384
 
 
class Base(DeclarativeBase):
    pass
 
 
class Resume(Base):
    __tablename__ = "resumes"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    version_label: Mapped[str] = mapped_column(String(100))  # "master" or "tailored-for-job-42"
    raw_text: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(String(500),nullable=True)
    profile_summary: Mapped[str|None] = mapped_column(Text,nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    is_master: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    applications: Mapped[list["Application"]] = relationship(back_populates="resume")
 
 
class Job(Base):
    __tablename__ = "jobs"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))       # "adzuna" | "jsearch"
    external_id: Mapped[str] = mapped_column(String(200))  # source's own id, used to de-dupe
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(500))
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    applications: Mapped[list["Application"]] = relationship(back_populates="job")
 
 
class ApplicationStatus(str, PyEnum):
    DRAFT = "draft"
    AWAITING_APPROVAL = "awaiting_approval"
    SUBMITTED = "submitted"
    INTERVIEW = "interview"
    REJECTED = "rejected"
    OFFER = "offer"
 
 
class Application(Base):
    __tablename__ = "applications"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT)
    cover_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # cosine similarity, resume vs job
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    job: Mapped["Job"] = relationship(back_populates="applications")
    resume: Mapped["Resume"] = relationship(back_populates="applications")
 
 
class InterviewSession(Base):
    __tablename__ = "interview_sessions"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True)
    transcript: Mapped[str] = mapped_column(Text)   # Q&A text
    feedback: Mapped[str] = mapped_column(Text)     # coach's written feedback
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    scores: Mapped[list["PerformanceScore"]] = relationship(back_populates="session")
 
 
class PerformanceScore(Base):
    __tablename__ = "performance_scores"
 
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"))
    category: Mapped[str] = mapped_column(String(50))  # "technical" | "communication" | "confidence"
    score: Mapped[float] = mapped_column(Float)         # 0-100
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
 
    session: Mapped["InterviewSession"] = relationship(back_populates="scores")