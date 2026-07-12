"""
Extracts raw text from an uploaded resume (PDF or DOCX), then asks Claude
to turn that messy raw text into a clean, structured profile — a summary,
a skills list, and a list of projects — which is what we'll actually embed
for job matching (cleaner signal than embedding the raw, noisy resume text).
"""
from pathlib import Path

import pypdf
import docx
from anthropic import Anthropic
from google import genai
from dotenv import load_dotenv


gemini_client = genai.Client()  # reads GEMINI_API_KEY from env automatically

client = Anthropic()  # reads ANTHROPIC_API_KEY from env automatically

load_dotenv()


MODEL = "claude-haiku-4-5-20251001"


def extract_raw_text(file_path: str) -> str:
    """Pulls plain text out of a .pdf or .docx resume file."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        reader = pypdf.PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if suffix == ".docx":
        document = docx.Document(str(path))
        return "\n".join(p.text for p in document.paragraphs)

    raise ValueError(f"Unsupported resume format: {suffix} (use .pdf or .docx)")


PROFILE_PROMPT = """You are helping build a clean, structured profile from a resume, for job-matching purposes.

Below is the raw extracted text of someone's resume. Some formatting noise (headers, \
dates, contact info) may be present -- ignore it. The person may also mention skills \
they learned on their own that aren't formally listed anywhere on the resume -- if \
they're given below under ADDITIONAL SELF-TAUGHT SKILLS, include those in the skills list too.

Return ONLY a JSON object with this exact shape, no other text, no markdown fences:
{{
  "summary": "2-3 sentence professional summary",
  "skills": ["skill1", "skill2"],
  "projects": [
    {{"name": "...", "description": "...", "tech_used": ["...", "..."]}}
  ]
}}

RAW RESUME TEXT:
{raw_text}

ADDITIONAL SELF-TAUGHT SKILLS (may be empty):
{extra_skills}
"""

def clean_json_response(text: str) -> str:
    """Strips markdown code fences some LLMs wrap JSON in, despite being told not to."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


def build_structured_profile(raw_text: str, extra_skills: str = "") -> str:
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=PROFILE_PROMPT.format(raw_text=raw_text, extra_skills=extra_skills),
    )
    return clean_json_response(response.text)  # or message.content[0].text, whichever you're using

# def build_structured_profile(raw_text: str, extra_skills: str = "") -> str:
#     """Calls Claude Haiku to turn raw resume text into a structured JSON profile.
#     Returns the raw JSON string as text -- caller parses it with json.loads()."""
#     message = client.messages.create(
#         model=MODEL,
#         max_tokens=1000,
#         messages=[
#             {
#                 "role": "user",
#                 "content": PROFILE_PROMPT.format(raw_text=raw_text, extra_skills=extra_skills),
#             }
#         ],
#     )
#     return message.content[0].text