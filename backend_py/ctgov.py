import hashlib
import time
import requests

import backend_py.cache as cache

CT_GOV_BASE = "https://clinicaltrials.gov/api/v2/studies"
PAGE_CAP = 10  # max 10,000 studies per request

def fetch_all_nctids(params: dict) -> list[dict]:
    params["fields"] = ",".join(["NCTId", "OverallStatus"])
    return fetch_all_pages(params)

def fetch_all_pages(params: dict) -> list[dict]:
    """Fetch all paginated results from the CT.gov API for a given query."""
    hash_ = hash_params(params)
    cached = cache.cache_get(hash_)
    if cached is not None:
        print(f"[ctgov] cache hit: {hash_}")
        return cached

    params = {**params, "pageSize": 1000}
    params.pop("pageToken", None)

    all_studies = []
    page_token = None
    page = 0

    while True:
        page += 1
        req_params = {**params}
        if page_token:
            req_params["pageToken"] = page_token

        print(f"[ctgov] page {page} — params: {req_params}")
        response = requests.get(CT_GOV_BASE, params=req_params, headers={"Accept": "application/json"})
        response.raise_for_status()

        data = response.json()
        studies = data.get("studies", [])
        all_studies.extend(studies)
        page_token = data.get("nextPageToken")

        print(f"[ctgov] page {page}: {len(studies)} studies (running total: {len(all_studies)})")

        if not page_token or page >= PAGE_CAP:
            break

        time.sleep(0.1)  # be polite to the API

    if page_token and page >= PAGE_CAP:
        print(f"[ctgov] WARNING: hit {PAGE_CAP}-page cap — results may be incomplete")

    cache.cache_set(hash_, all_studies)
    return all_studies

def hash_params(params: dict) -> str:
    sorted_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return hashlib.md5(sorted_str.encode()).hexdigest()