"""
Fetch studies from CT.gov, clean them, and write to SQLite.

Usage:
    python ingest.py <preset>        # run a named preset from queries_ctgov.yaml
    python ingest.py --list          # show available presets

Presets are defined in queries_ctgov.yaml.
"""

import argparse
from pathlib import Path
import yaml
import json
import os

import backend_py.clean as clean
import backend_py.ctgov as ctgov
import backend_py.db as db
import backend_py.evidence_objects as eos

QUERIES_FILE = Path(__file__).parent / "queries_ctgov.yaml"


def ingest_ctgov_data(conn, query_uid: str, params: dict) -> None:
    print(f"[ingest] query params: {params}")

    # before = db.count()

    print("[ingest] fetching from CT.gov...")
    raw_studies = ctgov.fetch_all_pages(params)
    print(f"[ingest] fetched {len(raw_studies)} studies")

    query = {"uid":query_uid, "text":json.dumps(params)}
    db.insert_queries(conn, [query])

    raw_studies = [r for r in raw_studies if r["hasResults"]]
    for raw in raw_studies:
        # run verification function here
        study = clean.process_ctgov_study(raw)
        db.upsert_studies(conn, [study], query)
        all_groups = clean.process_all_groups(raw)
        db.insert_comparator_groups(conn, all_groups)

        # population = process_ctgov_population
        # outcomes = process_ctgov_outcomes


    # after = db.count()
    # print(f"[ingest] done — db grew from {before} → {after} studies")
    
# ----------------

# def ingest_comparator_groups(ctgov_queries: list, must_have_results=False):
#     if not os.path.isfile(db.DB_PATH):
#         # ingest sources
#         print("Using queries: ", ctgov_queries)
#         with open(QUERIES_FILE) as f:
#             queries = yaml.safe_load(f)
#         with db.connect() as conn:
#             for uid,params in queries.items():
#                 if uid in ctgov_queries:
#                     ingest_ctgov_data(conn, uid, params)
#         conn.close()

def run():
    if os.path.isfile(db.DB_PATH):
        print(f"Database file already exists at {db.DB_PATH}. Script will now exit.")
        return
    
    ctgov_queries = ["nsclc_ppp"]
    print("Using queries: ", ctgov_queries)
    with open(QUERIES_FILE) as f:
        queries = yaml.safe_load(f)
    
    db.init_db()
    with db.connect() as conn:
        for uid,params in queries.items():
            if uid in ctgov_queries:
                ingest_ctgov_data(conn, uid, params)
    conn.close()


if __name__ == "__main__":
    run()