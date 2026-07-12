import numpy as np
from app.tools.embeddings import embed_text


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Returns a score from -1 to 1 -- higher means more similar in meaning."""
    a = np.array(vec_a)
    b = np.array(vec_b)
    cosine_sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    return float(cosine_sim)


def keyword_score(description: str, skills: list[str]) -> float:
    """Returns the fraction of `skills` that literally appear in `description` (case-insensitive)."""
    description_lower = description.lower()
    count = 0
    for skill in skills:
        if skill.lower() in description_lower:
            count +=1
    matched = count
    return matched / len(skills)



def rank_jobs(profile_text: str, skills: list[str], jobs: list[dict], top_n: int = 10) -> list[dict]:
    """Returns the top_n jobs from `jobs`, sorted by a blend of semantic + keyword match (best first).
    Each returned job dict gets extra 'match_score' (final blended score) and 'semantic_score' keys added."""
    profile_vector = embed_text(profile_text)

    for job in jobs:
        job_vector = embed_text(job['description'])
        semantic = cosine_similarity(profile_vector, job_vector)
        keyword = keyword_score(job['description'], skills)
        job['keyword_score'] = keyword
        job['semantic_score'] = semantic
        job['match_score'] = 0.7 * semantic + 0.3 * keyword

    jobs = [x for x in jobs if x['keyword_score'] > 0]

    jobs.sort(key=lambda x: x['match_score'], reverse=True)
    return jobs[:top_n]