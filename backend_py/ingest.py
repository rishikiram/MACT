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

from backend_py.clean import process_ctgov_studies
import backend_py.ctgov as ctgov
import backend_py.db as db
import backend_py.evidence_objects as eos

QUERIES_FILE = Path(__file__).parent / "queries_ctgov.yaml"


def ingest_ctgov_studies(conn, query_uid: str, params: dict) -> None:
    print(f"[ingest] query params: {params}")

    # db.init_db()
    # before = db.count()

    print("[ingest] fetching from CT.gov...")
    raw_studies = ctgov.fetch_all_pages(params)
    print(f"[ingest] fetched {len(raw_studies)} studies")

    cleaned, dropped = process_ctgov_studies(raw_studies)
    print(f"[ingest] cleaned: {len(cleaned)}, dropped (missing id/title): {dropped}")

    query = {"uid":query_uid, "text":json.dumps(params)}
    db.upsert_studies(conn, cleaned, query)
    # after = db.count()
    # print(f"[ingest] done — db grew from {before} → {after} studies")
    
# ----------------

def comparator_test():
    import os
    queries_to_use = ["nsclc_ppp"]
    if not os.path.isfile(db.DB_PATH):
        with db.connect() as conn:
            # ingest sources
            print("Using queries: ", queries_to_use)
            with open(QUERIES_FILE) as f:
                queries = yaml.safe_load(f)
            for uid,params in queries.items():
                if uid in queries_to_use:
                    ingest_ctgov_studies(conn, uid, params)
        conn.close()
    
    with db.connect() as conn:
        nct_ids = eos.get_nctids(conn, queries_to_use[0])
        evidence_list = eos.get_result_groups_and_endpoints(nct_ids)

        # json_file = Path(__file__).parent.parent / "data" / "result_groups.json"
        # with open(json_file, "w") as f:
        #     json.dump(evidence_list, f, indent=2)
        
        import csv
        # edit this mapping to rename columns in the output CSV (old_name -> new_name)
        column_renames = {
            "nct_id": "nct_id", 
            "title": "group_title", 
            "measurements": "reported_measurement_titles", 
            "group_types": "matching_design_group_label", 
            # "design_group_ids": row[5], 
            "description": "group_description",
            "ctgov_group_code": "ctgov_group_code", 
        }
        csv_file = Path(__file__).parent.parent / "data" / "result_groups.csv"
        with open(csv_file, "w", newline="") as f:
            fieldnames = [column_renames.get(k, k) for k in evidence_list[0].keys()]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in evidence_list:
                row = {**row, "measurements": json.dumps(row["measurements"])}
                row = {column_renames.get(k, k): v for k, v in row.items()}
                writer.writerow(row)
    conn.close()



if __name__ == "__main__":
    # build_traceable_stack_v2()
    comparator_test()