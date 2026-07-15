import sqlite3
import datetime
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
    
    interventions           TEXT,   -- JSON array
    arm_groups              TEXT,   -- JSON array -- TODO, sturcture data in comparators table

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
    text                    TEXT,
    datetime_ingested       TEXT
);

CREATE TABLE IF NOT EXISTS comparators (
    id                      INTEGER PRIMARY KEY,
    uid                     TEXT,
    nct_id                  TEXT,
    regimen                 TEXT,
    population_summary      TEXT, 
    endpoint_summary        TEXT,
    is_approved             BOOLEAN,
    previous_version_id     INTEGER,
    current_version_author  TEXT,

    FOREIGN KEY (nct_id)
        REFERENCES studies(nct_id),
    FOREIGN KEY (previous_version_id)
        REFERENCES comparators(id)
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
        row["datetime_ingested"] = str(datetime.datetime.now())
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys()) 
        crsr.execute(
            f"""
            INSERT INTO queries ({cols})
            VALUES ({placeholders})
            ON CONFLICT(uid) DO UPDATE SET 
                text = excluded.text, 
                datetime_ingested = excluded.datetime_ingested;
            """,
            row,
        )
    return len(queries)

def upsert_studies(conn, studies: list[dict], query: dict) -> int:
    # query requires {"uid": "...", "text": "..."}
    crsr = conn.cursor()
    crsr.execute(
        """
        INSERT INTO queries (uid, text) VALUES (:uid, :text)
        ON CONFLICT(uid) DO UPDATE SET text = excluded.text; -- add datetime of text update
        """,
        query
    )
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

def insert_comparators(conn, comparators: list[dict]) -> int:
    # Each dict: {uid, text}
    allowed_cols = ("uid", "nct_id", "regimen", "population_summary", "endpoint_summary", "is_approved", "previous_version_id", "current_version_author", )
    crsr = conn.cursor()
    for comparator in comparators:
        row = {k: comparator[k] for k in allowed_cols if k in comparator}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys()) 
        crsr.execute(
            f"""
            INSERT INTO comparators ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
    return len(comparators)

def query(conn, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    # TODO, does this cause a connection to never close?
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor.fetchall()

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

