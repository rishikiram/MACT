import sqlite3
import datetime
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "clinical_trials.db"



TABLES_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS studies (
    nct_id                  TEXT PRIMARY KEY,
    title                   TEXT,
    
    status                  TEXT,
    phase1                  BOOLEAN,
    phase2                  BOOLEAN,
    phase3                  BOOLEAN,
    phase4                  BOOLEAN,
    phase_text              TEXT,
    enrollment              INTEGER,
    enrollment_type         TEXT,
    masking                 TEXT,
    allocation              TEXT,
    intervention_model      TEXT,
    primary_purpose         TEXT,

    study_type              TEXT,
    start_date              TEXT,
    start_date_type         TEXT,
    primary_completion_date TEXT,
    primary_completion_date_type TEXT,
    completion_date         TEXT,
    completion_date_type    TEXT,
    last_update_post        TEXT,
    
    sponsor                 TEXT,
    sponsor_class           TEXT,
    
    conditions              TEXT,   -- JSON array
    condition_keywords      TEXT,   -- JSON array

    eligibility_criteria    TEXT,
    healthy_volunteers      TEXT,
    sex                     TEXT,
    std_ages                TEXT,   -- JSON array

    locations               TEXT,   -- JSON array of [facility, city, state, country, lat, lon]
    multicountry            BOOLEAN,
    primary_outcomes        TEXT,   -- JSON array
    secondary_outcomes      TEXT,   -- JSON array

    has_results             BOOLEAN,
    ingested_at             TEXT
);

CREATE TABLE IF NOT EXISTS queries (
    uid                     TEXT PRIMARY KEY,
    text                    TEXT    -- JSON array
    -- datetime_ingested       TEXT    -- removed because this should be the dt of the ctgov query, not the ingestion into this database
);

CREATE TABLE IF NOT EXISTS comparator_groups (
    id                      INTEGER PRIMARY KEY,
    uid                     TEXT,
    nct_id                  TEXT,
    group_code              TEXT,
    title                   TEXT,
    type                    TEXT,
    regimen                 TEXT,
    interventions           TEXT, -- JSON array
    population_summary      TEXT, 
    endpoint_summary        TEXT,
    data_source             TEXT, -- should be in [design_arm, outcome_group, event_group]. redundant with group code techincally

    is_approved             BOOLEAN DEFAULT FALSE,
        -- inked list to track edits or combine redundant groups. Most current should have next_version_id == NULL, 
    next_version_id         INTEGER DEFAULT NULL,
    current_version_author  TEXT,   -- not sure this is necessary

    UNIQUE(nct_id, group_code, next_version_id), -- allows multiple versions per group_code.
    FOREIGN KEY (nct_id)
        REFERENCES studies(nct_id),
    FOREIGN KEY (next_version_id)
        REFERENCES comparator_groups(id)
);

CREATE TABLE IF NOT EXISTS outcomes (
    id                      INTEGER PRIMARY KEY,
    uid                     TEXT,
    nct_id                  TEXT,
    title                   TEXT,
    type                    TEXT,
    description             TEXT,
    population_description  TEXT,
    units                   TEXT,
    time_frame              TEXT,
    p_value                 REAL,

    FOREIGN KEY (nct_id)
        REFERENCES studies(nct_id)
);

CREATE TABLE IF NOT EXISTS adverse_events (
    id                      INTEGER PRIMARY KEY,
    term                    TEXT NOT NULL,
    organ_system            TEXT NOT NULL,
    source_vocabulary       TEXT NOT NULL,
    assessment_type         TEXT NOT NULL,

    UNIQUE(term, organ_system, source_vocabulary, assessment_type)
);

"""

RELATIONSHIPS_SCHEMA = """
-- Many to many 
CREATE TABLE IF NOT EXISTS study_queries (
    nct_id                  TEXT,
    query_uid               TEXT,

    PRIMARY KEY (nct_id, query_uid),
    FOREIGN KEY (nct_id)
        REFERENCES studies(nct_id),
    FOREIGN KEY (query_uid)
        REFERENCES queries(uid)
);

CREATE TABLE IF NOT EXISTS reported_events (
    comparator_group_id     INTEGER,
    adverse_event_id        INTEGER,
    num_events              INTEGER,
    num_affected            INTEGER,
    num_at_risk             INTEGER,
    is_serious_event        BOOLEAN, -- this is an important distinction
    is_info_verified        BOOLEAN,

    PRIMARY KEY (comparator_group_id, adverse_event_id),
    FOREIGN KEY (comparator_group_id)
        REFERENCES comparator_groups(id),
    FOREIGN KEY (adverse_event_id)
        REFERENCES adverse_events(id)
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    # row_factory enables dict-like row access. PostgreSQL equivalent: psycopg2.extras.RealDictCursor
    conn.row_factory = sqlite3.Row

    # DIALECT NOTE: PRAGMA is SQLite-specific. Remove for PostgreSQL.
    conn.cursor().execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    # print("conn isolation level:",(conn.isolation_level is None))
    return conn


def init_db() -> None:
    with connect() as conn:
        cursor = conn.cursor()
        cursor.executescript(TABLES_SCHEMA)
        cursor.executescript(RELATIONSHIPS_SCHEMA)
    print(f"[db] initialized at {DB_PATH}")

def insert_queries(conn, queries: list[dict]) -> int:
    # Each dict: {uid, text}
    allowed_cols = ("uid", "text")
    crsr = conn.cursor()
    for query in queries:
        row = {k: query[k] for k in allowed_cols if k in query}
        # row["datetime_ingested"] = str(datetime.datetime.now())
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys()) 
        crsr.execute(
            f"""
            INSERT INTO queries ({cols})
            VALUES ({placeholders})
            ON CONFLICT(uid) DO UPDATE SET 
                -- datetime_ingested = excluded.datetime_ingested,
                text = excluded.text;
            """,
            row,
        )
    crsr.close()
    return len(queries)

def upsert_studies(conn, studies: list[dict], query: dict) -> int:
    # query requires {"uid": "...", "text": "..."}
    # insert_queries(conn, [query])

    crsr = conn.cursor()
    for study in studies:
        cols = ", ".join(study.keys())
        placeholders = ", ".join(f":{k}" for k in study.keys())
        crsr.execute(
            f"INSERT OR REPLACE INTO studies ({cols}) VALUES ({placeholders})",
            study,
        )
        crsr.execute(
            """
            INSERT INTO study_queries (nct_id, query_uid) VALUES (?, ?)
            ON CONFLICT(nct_id, query_uid) DO NOTHING;
            """,
            (study["nct_id"], query["uid"])
        )
    crsr.close()
    return len(studies)

def insert_comparator_groups(conn, comparator_groups: list[dict]) -> int:
    # Each dict: {uid, text}
    allowed_cols = ("uid", "nct_id", "group_code", "title", "interventions", "regimen", "population_summary", "endpoint_summary", "is_approved", "next_version_id", "current_version_author")
    crsr = conn.cursor()
    for comparator in comparator_groups:
        row = {k: comparator[k] for k in allowed_cols if k in comparator}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys()) 
        crsr.execute(
            f"""
            INSERT INTO comparator_groups ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
    crsr.close()
    return len(comparator_groups)

def insert_outcomes(conn, outcomes: list[dict]) -> int:
    # Each dict: {uid, text}
    allowed_cols = ("uid", "nct_id", "title", "type", "description", "population_description", "units", "time_frame", "p_value") 
    crsr = conn.cursor()
    for o in outcomes:
        row = {k: o[k] for k in allowed_cols if k in o}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys()) 
        crsr.execute(
            f"""
            INSERT INTO outcomes ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
    crsr.close()
    return len(outcomes)

def insert_and_link_adverse_events(conn, events: list[dict], nct_id: str, group_code: str) -> int:
    # finds the most recent arm row id (based on title and nct_id)
    most_recent_group_id = get_most_recent_group_id(conn, nct_id, group_code)
    
    # Each e dict: {term, organ_system, source_vocabulary, assessment_type, num_events, num_affected, num_at_risk, is_serious_event}
    allowed_cols_ae = ("term", "organ_system", "source_vocabulary", "assessment_type")
    allowed_cols_re = ("num_events", "num_affected", "num_at_risk", "is_serious_event")
    crsr = conn.cursor()
    e_ids = []
    for e in events:
        row = {k: e.get(k) for k in allowed_cols_ae}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        #inserts (if needed) the adverse event
        crsr.execute(
            f"""
            INSERT INTO adverse_events ({cols})
            VALUES ({placeholders})
            ON CONFLICT(term, organ_system, source_vocabulary, assessment_type) DO NOTHING;
            """,
            row,
        )
        # get the adverse event id
        crsr.execute(
            """
            SELECT id FROM adverse_events
            WHERE term = :term AND organ_system = :organ_system 
              AND source_vocabulary = :source_vocabulary AND assessment_type = :assessment_type;
            """,
            row,
        )
        ae_id = crsr.fetchall()[0][0] 

        row2 = {k: e.get(k) for k in allowed_cols_re}
        row2["comparator_group_id"] = most_recent_group_id
        row2["adverse_event_id"] = ae_id
        cols2 = ", ".join(row2.keys())
        placeholders2 = ", ".join(f":{k}" for k in row2.keys())
        # insert the AE <--> arm link, AKA a reported event
        crsr.execute(
            f"""
            INSERT INTO reported_events ({cols2})
            VALUES ({placeholders2});
            """,
            row2,
        )

    crsr.close()
    return len(events)

def get_most_recent_group_id(conn, nct_id: str, group_code: str) -> int:
    row = query(conn, "SELECT id, next_version_id FROM comparator_groups WHERE nct_id = ? AND group_code = ?", (nct_id, group_code))[0]
    # check for loop
    # also check for a cycle
    p1, p2 = row[0], row[1]
    p2_prev = p1
    a_switch = True # alternates on off
    while p2 and p1:
        p2_prev = p2
        p2 = query(conn, "SELECT next_version_id FROM comparator_groups WHERE id = ?", (p2,))[0][0]
        
        if a_switch: 
            p1 = query(conn, "SELECT next_version_id FROM comparator_groups WHERE id = ?", (p1,))[0][0]
        a_switch = not a_switch
        
        if p1 == p2:
            raise Exception(f"A cycle was found in comparator_groups! Cycle contained row where nct_id = {nct_id}, group_code = {group_code}, id = {p1}.")
    
    return p2_prev

def set_next_version_pointer(conn, original_id: int, updated_id: int) -> None:
    # check for identity
    if original_id == updated_id:
        print(f"WARNING: cannot set next_version_id to reference itself (tried on id={original_id}).")
        return None
    # check if a cycle is created if connected
    p2 = updated_id
    while p2:
        p2 = query(conn, "SELECT next_version_id FROM comparator_groups WHERE id = ?", (p2,))[0][0]
        if p2 == original_id:
            print(f"WARNING: a cycle was attempted to be made in comparator_groups by connecting row id:[{original_id}] to id:[{updated_id}]. The set was aborted.")
            return None
    
    cursor = conn.cursor()
    cursor.execute("UPDATE comparator_groups SET next_version_id = ? WHERE id = ?", (updated_id, original_id))
    # find all reported_events where comparator_group_id = old_id, and update to new id
    cursor.execute("UPDATE reported_events SET comparator_group_id = ? WHERE comparator_group_id = ?", (updated_id, original_id))
    cursor.close()
    return None

def query(conn, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    cursor = conn.cursor()
    cursor.execute(sql, params)
    to_return = cursor.fetchall()
    cursor.close()
    return to_return

def count(table = "studies") -> int:
    with connect() as conn:
        to_return  = query(conn, f"SELECT COUNT(*) FROM {table}")[0][0]
    conn.close()
    return to_return

def get_table_columns(conn, table_name: str) -> list[dict]:
    """
    Returns [{name, type, notnull}, ...] for each column in table_name.

    DIALECT NOTE: uses SQLite PRAGMA table_info.
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}')")
    rows = cursor.fetchall()
    return [{"name": r["name"], "type": r["type"], "notnull": bool(r["notnull"])} for r in rows]

def get_id(conn, table_name, uid) -> int:
    # NOTE: security risk, can be improved later
    return query(conn, f"SELECT id FROM {table_name} WHERE uid = ?", params = (uid,))[0][0]

# def get_query_params(conn, query_uid) -> dict:
#     text = query(conn, "SELECT text FROM queries WHERE uid = ?", (query_uid,))[0][0]
#     return json.loads(text)

def build_data_dictionary(table_name: str = "studies") -> None:
    """
    Bootstrap entry point. Creates the DataDictionary table if needed, then
    replaces all rows for table_name with the current schema — existing annotations
    are wiped. Delegates all SQL to dictionary_repo so this function needs no changes
    when switching databases (only connect() and get_table_columns() above change).
    """
    from backend_py.data_dictionary import build_dataDictionary, build_from_table
    with connect() as conn:
        build_dataDictionary(conn)
        n = build_from_table(conn, table_name)
    print(f"[db] DataDictionary built for '{table_name}' — {n} columns registered")

