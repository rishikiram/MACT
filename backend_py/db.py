import sqlite3
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
    text                    TEXT
    -- last_ingested           TEXT
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

def insert_queries(conn, queries: list[dict]) -> int:
    # Each dict: {uid, text}
    allowed_cols = ("uid", "text")
    crsr = conn.cursor()
    for query in queries:
        row = {k: query[k] for k in allowed_cols if k in query}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"""
            INSERT INTO queries ({cols})
            VALUES ({placeholders})
            ON CONFLICT(uid) DO UPDATE SET text = excluded.text;
            """,
            row,
        )
    return len(queries)

def insert_sources(conn, sources: list[dict]) -> int:
    allowed_cols = ("uid", "type", "title", "url", "target_evidence_types", "how_to_recreate")
    crsr = conn.cursor()
    for source in sources:
        row = {k: source[k] for k in allowed_cols if k in source}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"""
            INSERT INTO sources ({cols})
            VALUES ({placeholders});
            """,
            row,
        )
    return len(sources)

def insert_and_link_EOs(conn, evidence_objs: list[dict]) -> list:
    # Each dict: {uid, type, statement, normalized_value, confidence, source_uids: [...]}
    allowed_cols = ("uid", "type", "statement", "nct_id", "normalized_value", "confidence")
    crsr = conn.cursor()
    eo_ids = [-1] * len(evidence_objs)
    i = 0
    for eo in evidence_objs:
        row = {k: eo[k] for k in allowed_cols if k in eo}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"INSERT INTO evidence_objects ({cols}) VALUES ({placeholders}) RETURNING id;",
            row,
        )
        eo_id = crsr.fetchall()[0][0]
        eo_ids[i] = eo_id
        i+=1
        for source_uid in eo.get("source_uids", []):
            source_id = get_id(conn, "sources", source_uid)
            crsr.execute(
                """
                INSERT OR IGNORE INTO evidence_object_sources (
                    source_id, evidence_object_id
                ) VALUES (?, ?)
                """,
                (source_id, eo_id),
            )
    return eo_ids

def insert_claims(conn, claims: list[dict]) -> int:
    # Each dict: {uid, statement, support_status, review_status, risk_note,}
    allowed_cols = ("uid", "statement", "type", "support_status", "review_status", "risk_note")
    crsr = conn.cursor()
    for claim in claims:
        row = {k: claim[k] for k in allowed_cols if k in claim}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"""
            INSERT INTO claims ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
    return len(claims)

def link_EOs_to_claims_of_type(conn, eo_ids: list, claim_type: str) -> int:
    cursor = conn.cursor()
    temp = query("SELECT id FROM claims WHERE type = ?", (claim_type,), conn=conn)
    claim_ids = [row[0] for row in temp]
    i = 0
    for eo_id in eo_ids:
        for claim_id in claim_ids:
            cursor.execute(
                    """
                    INSERT OR IGNORE INTO claim_evidence_objects (
                        evidence_object_id, claim_id
                    ) VALUES (?, ?)
                    """,
                    (eo_id, claim_id)
                )
            i += 1
    return i

def insert_and_link_claims(conn, claims: list[dict]) -> int:
    # Each dict: {uid, statement, status, risk_note, evidence_object_uids: [...]}
    insert_claims(conn, claims)
    crsr = conn.cursor()
    for claim in claims:
        claim_id = get_id(conn, "claims", claim["uid"])
        for eo_uid in claim.get("evidence_object_uids", []):
            eo_id = get_id(conn, "evidence_objects", eo_uid)
            crsr.execute(
                """
                INSERT INTO claim_evidence_objects (
                    claim_id, evidence_object_id
                ) VALUES (?, ?)
                """,
                (claim_id, eo_id),
            )
    return len(claims)

def insert_requirements(conn, requirements: list[dict]) -> int:
    # TODO: shift pk generation to RDBM, and enable row replacement
    # Each dict: {uid, jurisdiction, domain, requirement_text}
    allowed_cols = [col_dict["name"] for col_dict in get_table_columns(conn, "requirements")]
    crsr = conn.cursor()
    for req in requirements:
        row = {k: req[k] for k in allowed_cols if k in req}
        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"""
            INSERT INTO requirements ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
    return len(requirements)

def insert_and_link_gaps(conn, gaps: list[dict]) -> int:
    # allowed_cols = ('uid', 'type', 'jurisdiction', 'rationale', 'severity', 'recommended_action')
    allowed_cols = [col_dict["name"] for col_dict in get_table_columns(conn, "gaps")]
    crsr = conn.cursor()
    for gap in gaps:
        row = {k: gap[k] for k in allowed_cols if k in gap}

        if "requirement_uid" in gap:
            row["requirement_id"] = get_id(conn, "requirements", gap["requirement_uid"])

        cols = ", ".join(row.keys())
        placeholders = ", ".join(f":{k}" for k in row.keys())
        crsr.execute(
            f"""
            INSERT INTO gaps ({cols})
            VALUES ({placeholders})
            """,
            row,
        )
        
        for claim_uid in gap["claim_uids"]:
            claim_id = get_id(conn, "claims", claim_uid)
            gap_id = get_id(conn, "gaps", gap["uid"])
            crsr.execute(
                """
                INSERT OR IGNORE INTO gap_claims (
                    claim_id, gap_id
                ) VALUES (?, ?)
                """,
                (claim_id, gap_id),
            )
    return len(gaps)

def update_gap(conn, gap) -> None:
    allowed_cols = [col_dict["name"] for col_dict in get_table_columns(conn, "gaps")]
    crsr = conn.cursor()
    row = {k: gap[k] for k in allowed_cols if k in gap}

    if "requirement_uid" in gap:
        row["requirement_id"] = get_id(conn, "requirements", gap["requirement_uid"])

    col_keys = ", ".join(f"{k} = :{k}" for k in row.keys())
    crsr.execute(
        f"""
        UPDATE gaps SET {col_keys} 
        WHERE uid = :uid
        """,
        row,
    )

def query(sql: str, params: tuple = (), conn = connect()) -> list[sqlite3.Row]:
    # TODO, does this cause a connection to never close?
    cursor = conn.cursor()
    cursor.execute(sql, params)
    return cursor.fetchall()
# def query(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
#     # TODO, does this cause a connection to never close?
#     with connect() as conn:
#         cursor = conn.cursor()
#         cursor.execute(sql, params)
#         return cursor.fetchall()


def count(table = "studies") -> int:
    return query(f"SELECT COUNT(*) FROM {table}")[0][0]


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
    return query(f"SELECT id FROM {table_name} WHERE uid = ?", params = (uid,), conn = conn)[0][0]

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

