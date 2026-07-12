import os
import httpx
from dotenv import load_dotenv

load_dotenv()


def normalize_adzuna_job(raw_job: dict) -> dict:
    """Flattens one raw Adzuna job result into our standard job shape."""
    return {
        "source": "adzuna",
        "external_id": raw_job['id'],   # which key in raw_job is this?
        "title": raw_job['title'],
        "company": raw_job['company'].get('display_name','Not specified'),       # careful -- this one's nested
        "location": raw_job['location'].get('display_name','fallback'),      # careful -- this one's nested too
        "description": raw_job['description'],
        "url": raw_job['redirect_url'],           # which key had the actual link?
    }

def normalize_jsearch_job(raw_job: dict) -> dict:
    """Flattens one raw JSearch job result into our standard job shape."""
    return {
        "source": "jsearch",
        "external_id": raw_job['job_id'],   # which key?
        "title": raw_job['job_title'],
        "company": raw_job['employer_name'],
        "location": raw_job['job_location'],
        "description": raw_job['job_description'],
        "url": raw_job['job_apply_link'],           # careful: there are two link-like fields here, which is the right one to apply through?
    }

def fetch_adzuna_jobs(query: str, results_per_page: int = 10) -> list[dict]:
    """Searches Adzuna for jobs matching `query`, returns a list of normalized job dicts."""
    response = httpx.get(
        "https://api.adzuna.com/v1/api/jobs/in/search/1",
        params={
            "app_id": os.environ["ADZUNA_APP_ID"],          # from env -- which variable name did we set this as?
            "app_key": os.environ["ADZUNA_APP_KEY"],         # from env
            "results_per_page": results_per_page,
            "what": query,
        },
    )
    data = response.json()                     # turn the response into a Python dict -- which method did we use in test_apis.py?
    raw_jobs = data['results']                  # which key in `data` holds the actual list of job results? (check the JSON you saw earlier)
    return [normalize_adzuna_job(job) for job in raw_jobs]


def fetch_jsearch_jobs(query: str) -> list[dict]:
    """Searches JSearch for jobs matching `query`, returns a list of normalized job dicts."""
    response = httpx.get(
        "https://jsearch.p.rapidapi.com/search",
        params={"query": query, "num_pages": "1"},
        headers={
            "X-RapidAPI-Key": os.environ["RAPIDAPI_KEY"],     # from env
            "X-RapidAPI-Host": os.environ["JSEARCH_HOST"],    # from env
        },
        timeout=30,
    )
    data = response.json()
    raw_jobs = data['data']               # careful -- JSearch's top-level key for the job list is different from Adzuna's. Check the JSON you pasted earlier.
    return [normalize_jsearch_job(job) for job in raw_jobs]


def fetch_all_jobs(query: str) -> list[dict]:
    """Combines Adzuna + JSearch results into one job pool."""
    # adzuna_job_list = fetch_adzuna_jobs(query)
    # jsearch_job_list = fetch_jsearch_jobs(query)
    combined_jobs = fetch_adzuna_jobs(query) + fetch_jsearch_jobs(query)
    return combined_jobs