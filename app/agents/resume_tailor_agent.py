import json
import json as json_module
from google import genai
from app.tools.resume_parser import clean_json_response
from app.db.crud import get_resume_by_id, get_job_by_id ,save_resume
from app.db.session import SessionLocal
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from app.guardrails.policies import check_resume_honesty

gemini_client = genai.Client()

TAILOR_PROMPT = """You are helping tailor a resume profile to a specific job posting.

Below is the candidate's current structured profile (JSON), and a job description
they're applying to. Compare them carefully.

If the profile already fits this job well, return it completely unchanged, and set
"changes_made" to false. Do NOT invent superficial edits just to seem useful --
only make changes that are genuinely warranted by a real mismatch between the
profile and this specific job.

If changes ARE warranted, return an updated profile emphasizing the most relevant
skills/projects for THIS job, and set "changes_made" to true, with a short
"change_summary" explaining what you changed and why.

Never invent or exaggerate seniority, years of experience, or achievements the
candidate hasn't actually claimed. This candidate is a fresher with no professional
experience -- reframe and reprioritize their REAL projects/skills for relevance,
but do not imply professional experience, seniority, or accomplishments beyond
what's genuinely in their profile. If asked to make a fresher sound senior, refuse
that specific change and keep the honest framing instead.

Return ONLY a JSON object with this exact shape, no other text, no markdown fences:
{{
  "changes_made": true or false,
  "change_summary": "explanation, or empty string if changes_made is false",
  "summary": "...",
  "skills": ["...", "..."],
  "projects": [{{"name": "...", "description": "...", "tech_used": ["..."]}}]
}}

CURRENT PROFILE:
{profile_json}

JOB DESCRIPTION:
{job_description}
"""


def tailor_resume_for_job(db, resume_id: int, job_id: int) -> dict:
    """Fetches a resume + job by id, asks the LLM to tailor (or confirm no change needed).
    Returns the parsed JSON response as a dict."""

    resume = get_resume_by_id(db,resume_id)
    job = get_job_by_id(db,job_id)
    if resume is None or job is None:
        raise ValueError("Resume or job not found")
    response = gemini_client.models.generate_content(
    model="gemini-2.5-flash",
    contents=TAILOR_PROMPT.format(profile_json = resume.profile_summary,job_description = job.description)
        )
    cleaned = clean_json_response(response.text)
    results = json.loads(cleaned)

    return results

class ResumeTailorState(TypedDict):
    resume_id: int
    job_id : int
    tailored_profile : dict
    new_resume_id : int


def resume_tailor_node(state: ResumeTailorState) -> ResumeTailorState:
    db = SessionLocal()

    tailored_resume = tailor_resume_for_job(db,state['resume_id'],state['job_id'])

    original_resume = get_resume_by_id(db,state['resume_id'])
    
    honesty_check = check_resume_honesty(tailored_resume["summary"])
    if not honesty_check["passed"]:
        raise ValueError(f"Guardrail failed: fabricated experience detected - {honesty_check['flagged_terms']}")

    saved_resume = save_resume(db,original_resume.raw_text,json_module.dumps(tailored_resume),version_label=f"tailored-for-job-{state['job_id']}",is_master=False)
    
    state["new_resume_id"] = saved_resume
    state["tailored_profile"] = tailored_resume
    
    db.close()

    return state

graph = StateGraph(ResumeTailorState)
graph.add_node("resume_tailor",resume_tailor_node)
graph.add_edge(START,"resume_tailor")
graph.add_edge("resume_tailor",END)
app = graph.compile()