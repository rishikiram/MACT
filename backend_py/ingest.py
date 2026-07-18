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
import logging
import datetime

import backend_py.ctgov_transform as ctgov_transform
import backend_py.ctgov as ctgov
import backend_py.db as db

QUERIES_FILE = Path(__file__).parent / "queries_ctgov.yaml"

VERIFY_LOG_FILE = Path(__file__).parent.parent / "data" / "verify_data.log"
VERIFY_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

verify_logger = logging.getLogger("verify_data")
verify_logger.setLevel(logging.INFO)
verify_logger.addHandler(logging.FileHandler(VERIFY_LOG_FILE))


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
        study = ctgov_transform.process_study(raw)
        db.upsert_studies(conn, [study], query)
        
        all_groups = ctgov_transform.process_all_groups(raw)
        db.insert_comparator_groups(conn, all_groups)
        
        outcomes = ctgov_transform.process_outcomes(raw)
        db.insert_outcomes(conn, outcomes)

        events = ctgov_transform.process_events(raw)
        for e in events:
            for r in e["reports"]:
                db.insert_and_link_adverse_events(conn, [e | r], e["nct_id"], r["group_code"])
        
        nct_id = study["nct_id"]
        group_code_map = ctgov_transform.build_group_mapping(raw)
        for original_group_code, updated_group_code in group_code_map.items():
            original_id = db.get_most_recent_group_id(conn, nct_id, original_group_code)
            updated_id = db.get_most_recent_group_id(conn, nct_id, updated_group_code)
            db.set_next_version_pointer(conn, original_id, updated_id)

        # population = process_population
        # outcomes = process_outcomes

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
#                     ingest_data(conn, uid, params)
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

def verify_data(params: dict):
    verify_logger.info(f"Verification Ran at {datetime.datetime.now()}")
    raw_studies = ctgov.fetch_all_pages(params)
    raw_studies = [r for r in raw_studies if r["hasResults"]]
    for raw in raw_studies:
        probelms = ctgov_transform.check_study(raw)
        nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
        verify_logger.info(f"-------------- Study: {nct_id} --------------------")
        for p in probelms:
            verify_logger.info(p)
        verify_logger.info("")
    verify_logger.info("\n\n###########################################################################\n\n")

def run():

    ctgov_queries = ["nsclc_ppp"]
    print("Using queries: ", ctgov_queries)
    with open(QUERIES_FILE) as f:
        queries = yaml.safe_load(f)
    
    for uid,params in queries.items():
        if uid in ctgov_queries:    
            verify_data(params)


    if not os.path.isfile(db.DB_PATH):
        db.init_db()
        with db.connect() as conn:
            for uid,params in queries.items():
                if uid in ctgov_queries:
                    ingest_ctgov_data(conn, uid, params)
            
    else:
        print(f"Database file already exists at {db.DB_PATH}. Script will only run tests.")
        with db.connect() as conn:
            test(conn)
    
    conn.close()

if __name__ == "__main__":
    run()