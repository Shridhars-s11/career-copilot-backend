FABRICATION_RED_FLAGS = [
    "years of experience", "extensive experience", "senior",
    "led a team", "managed a team", "proven track record",
    "expert in", "10+ years",
]

INJECTION_RED_FLAGS = [
    "ignore previous instructions", "ignore all previous",
    "system:", "you are now", "disregard the above", "new instructions:",
]


def check_resume_honesty(tailored_summary: str) -> dict:
    """Checks a tailored resume summary for fabricated-seniority red flags.
    Returns {"passed": bool, "flagged_terms": [...]}"""
    tailored_summary_lower = tailored_summary.lower()
    flagged_terms = []
    for term in FABRICATION_RED_FLAGS:
        if term in tailored_summary_lower:
            flagged_terms.append(term)
    return {"passed": len(flagged_terms) == 0, "flagged_terms": flagged_terms}


def check_prompt_injection(external_text: str) -> dict:
    """Checks external text (e.g. a job description) for prompt-injection
    attempts before it's included in an LLM prompt.
    Returns {"passed": bool, "flagged_terms": [...]}"""
    external_text_lower = external_text.lower()
    flagged_terms = []
    for term in INJECTION_RED_FLAGS:
        if term in external_text_lower:
            flagged_terms.append(term)
    return {"passed": len(flagged_terms) == 0, "flagged_terms": flagged_terms}