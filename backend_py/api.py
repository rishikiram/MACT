"""
FastAPI skeleton for serving clinical trial data (backend_py/db.py) to a frontend.

This file intentionally contains no real query logic — it's a starting point
sketching out what endpoints a frontend would likely need, and which db.py
helpers each one would build on. Fill in the TODOs.

Relevant db.py tables: studies, comparator_groups, outcomes, adverse_events,
reported_events (comparator_group <-> adverse_event), queries, study_queries.
Relevant db.py helpers: connect(), query(conn, sql, params), count(table),
get_table_columns(conn, table_name), get_id(conn, table_name, uid).
data_dictionary.get_annotations(conn, table_name) has column-level metadata.
"""

from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend_py.db import connect, DB_PATH

app = FastAPI(title="TACT DB API", description="Serves clinical trial data from local SQLite")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _require_db() -> None:
    if not DB_PATH.exists():
        raise HTTPException(status_code=503, detail=f"Database not found at {DB_PATH}. Run ingest.py first.")


@app.get("/db/trials")
def list_trials(
    condition: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    phases: Optional[str] = Query(None, description="Comma-separated phase numbers, e.g. '2,3'"),
):
    """List/filter studies. TODO: build a WHERE clause from the filters and query the studies table."""
    _require_db()
    raise NotImplementedError


@app.get("/db/trial/{nct_id}")
def get_trial(nct_id: str):
    """Fetch one study by nct_id, likely joined with its comparator_groups/outcomes/adverse_events."""
    _require_db()
    raise NotImplementedError


@app.get("/db/trial/{nct_id}/comparator-groups")
def get_comparator_groups(nct_id: str):
    """List comparator_groups for a study (arms, outcome groups, event groups + version history)."""
    _require_db()
    raise NotImplementedError


@app.get("/db/trial/{nct_id}/adverse-events")
def get_adverse_events(nct_id: str):
    """List adverse events reported for a study, via reported_events -> comparator_groups."""
    _require_db()
    raise NotImplementedError



