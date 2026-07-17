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
        
        outcomes = clean.process_ctgov_outcomes(raw)
        db.insert_outcomes(conn, outcomes)

        events = clean.process_ctgov_events(raw)
        for e in events:
            for r in e["reports"]:
                db.insert_and_link_adverse_events(conn, [e | r], e["nct_id"], r["group_code"])


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

def test(conn) -> None:
    nct_ids = ["NCT03515837", "NCT03515837", "NCT03515837"]
    original_group_codes = ["OG001", "OG000", "ARM001"]
    updated_group_codes = ["ARM001", "ARM000", "ARM001"]

    prev = db.get_most_recent_group_id(conn, nct_ids[0], original_group_codes[0])
    print("Testing for updating group pointer \nBEFORE: ", prev)

    for nct_id, original_group_code, updated_group_code in zip(nct_ids, original_group_codes, updated_group_codes):
        original_id = db.get_most_recent_group_id(conn, nct_id, original_group_code)
        updated_id = db.get_most_recent_group_id(conn, nct_id, updated_group_code)
        db.set_next_version_pointer(conn, original_id, updated_id)

    after = db.get_most_recent_group_id(conn, nct_ids[0], original_group_codes[0])
    print("AFTER: ", after)

    db.set_next_version_pointer(conn, after, prev)
    return

def verify_data(params: dict, ):
    raw_studies = ctgov.fetch_all_pages(params)
    raw_studies = [r for r in raw_studies if r["hasResults"]]
    print("---------------")
    for raw in raw_studies:
        probelms = clean.check_ctgov_study(raw)
        print("Study: ", raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId"))
        for p in probelms:
            print(p)
        print("")
        clean.build_group_mapping(raw)
        print("---------------")

def run():
    db.init_db()
    with db.connect() as conn:
        ctgov_queries = ["nsclc_ppp"]
        print("Using queries: ", ctgov_queries)
        with open(QUERIES_FILE) as f:
            queries = yaml.safe_load(f)
        
        for uid,params in queries.items():
            if uid in ctgov_queries:    
                verify_data(params)

        if not os.path.isfile(db.DB_PATH):
            for uid,params in queries.items():
                if uid in ctgov_queries:
                    ingest_ctgov_data(conn, uid, params)
            
        else:
            print(f"Database file already exists at {db.DB_PATH}. Script will only run tests.")

        test(conn)
    
    conn.close()

if __name__ == "__main__":
    run()