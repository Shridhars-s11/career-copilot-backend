from google import genai
from app.tools.resume_parser import clean_json_response
from app.db.crud import get_job_by_id, save_interview_session
from app.db.session import SessionLocal
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
import json

gemini_client = genai.Client()

QUESTION_PROMPT = """You are an interviewer preparing for a candidate's interview for this job:

JOB DESCRIPTION:
{job_description}

Ask ONE realistic interview question a candidate for this specific role would likely
be asked -- technical or behavioral, your choice, based on what this job actually
needs. Do not ask something generic and unrelated to this posting.

Return ONLY a JSON object with this exact shape, no other text, no markdown fences:
{{
  "question": "...",
  "category": "technical" or "behavioral"
}}
"""


def generate_interview_question(db, job_id: int) -> dict:
    """Fetches a job by id, asks the LLM to generate one relevant interview question."""
    job = get_job_by_id(db,job_id)
    
    if job is None:
        raise ValueError("Resume or job not found")
    response = gemini_client.models.generate_content(
    model="gemini-2.5-flash",
    contents=QUESTION_PROMPT.format(job_description = job.description)
        )
    
    cleaned = clean_json_response(response.text)
    result = json.loads(cleaned)

    return result


FEEDBACK_PROMPT = """You are an interview coach giving honest, specific feedback.

QUESTION ASKED:
{question}

CANDIDATE'S ANSWER:
{answer}

Give direct, specific feedback -- name concrete gaps (missing details, vague claims,
things a real interviewer would push back on) rather than generic encouragement.
If the answer is genuinely strong, say so plainly, but still look for at least one
real way to sharpen it further.

Return ONLY a JSON object with this exact shape, no other text, no markdown fences:
{{
  "feedback": "specific, actionable feedback",
  "technical_score": a number from 0 to 100,
  "communication_score": a number from 0 to 100
}}
"""


def evaluate_interview_answer(question: str, answer: str) -> dict:
    """Asks the LLM to evaluate an interview answer, returns feedback + scores as a dict."""
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=FEEDBACK_PROMPT.format(question = question,answer = answer)
    )
    cleaned = clean_json_response(response.text)

    result = json.loads(cleaned)

    return result

class InterviewCoachState(TypedDict):
    job_id : int
    user_answer : str
    question: str
    feedback: str
    technical_score: float
    communication_score: float
    session_id: int


def interview_coach_node(state: InterviewCoachState) -> InterviewCoachState:
    db = SessionLocal()

    interview_que = generate_interview_question(db, state["job_id"])
    state['question'] = interview_que['question']

    interview_result = evaluate_interview_answer(state['question'], state['user_answer'])
    state['feedback'] = interview_result['feedback']
    state['technical_score'] = interview_result['technical_score']
    state['communication_score'] = interview_result['communication_score']

    state['session_id'] = save_interview_session(db, state['job_id'], state['user_answer'], state['feedback'],
        state['technical_score'], state['communication_score']
    )

    db.close()

    return state


graph = StateGraph(InterviewCoachState)
graph.add_node("interview_coach", interview_coach_node)
graph.add_edge(START, "interview_coach")
graph.add_edge("interview_coach", END)
app = graph.compile()