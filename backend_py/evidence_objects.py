import json

import backend_py.aact_ctti as aact
import backend_py.ctgov as ctgov
import backend_py.db as db

def get_nctids(conn, query_uid: str) -> list[str]:
    cursor = conn.cursor()
    cursor.execute(
        """
            SELECT studies.nct_id
            FROM studies
            JOIN study_queries ON studies.nct_id = study_queries.nct_id
            WHERE study_queries.query_uid = ?
        """,
        (query_uid,)
    )
    r = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return r


GROUP_TYPES = ("ACTIVE_COMPARATOR", "EXPERIMENTAL", "NO_INTERVENTION", "OTHER", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR")

def get_potential_comparator_groups_of_type(study_nctids: list[str], design_group_types: list[str]) -> list[dict]:
    assert isinstance(design_group_types, list) and set(design_group_types).issubset(GROUP_TYPES), "design_group_types must be a list of valid AACT group types."
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                rg.nct_id,
                MIN(rg.id)           AS result_group_id,
                MIN(dg.id)           AS design_group_id,
                dg.group_type,
                rg.title,
                MIN(rg.description)
            FROM result_groups AS rg
            JOIN design_groups AS dg 
                ON  dg.nct_id = rg.nct_id AND dg.title = rg.title
            WHERE rg.nct_id = ANY(%s) AND dg.group_type = ANY(%s)
            GROUP BY
                rg.nct_id,
                dg.group_type,
                rg.title
            """,
            (study_nctids, design_group_types)
        ) 
        rows = cur.fetchall()
    r = [{"nct_id": row[0], "result_group_id": row[1], "design_group_id": row[2], "group_type": row[3], "title": row[4], "description": row[5]} for row in rows]
    return r

def get_arms(nctid_list: list[str]):
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                rg.nct_id,
                rg.title,
                ARRAY_AGG(DISTINCT rg.result_type) AS result_types,
                ARRAY_AGG(DISTINCT dg.group_type) AS group_types,
                MIN(dg.id)          	AS design_group_id, -- only one is returned, so MIN is ok
                MAX(rg.description) 	AS description -- distict ones differ insignifigantly
            FROM result_groups AS rg
                LEFT JOIN design_groups AS dg
                    ON dg.nct_id = rg.nct_id AND dg.title = rg.title
            WHERE rg.nct_id = ANY(%s)
            GROUP BY
                rg.nct_id,
                rg.title
            """,
            (nctid_list,)
        ) 
        rows = cur.fetchall()
    r = [{"nct_id": row[0], "title": row[1], "result_types": row[2], "group_types": row[3], "design_group_id": row[4], "description": row[5]} for row in rows]
    return r

def get_endpoints(nctid_list: list[str]):
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                rg.nct_id,
                rg.title,
                ARRAY_AGG(DISTINCT rg.result_type) AS result_types,
                ARRAY_AGG(DISTINCT dg.group_type) AS group_types,
                MIN(dg.id)          	AS design_group_id, -- only one is returned, so MIN is ok
                MAX(rg.description) 	AS description -- distict ones differ insignifigantly
            FROM result_groups AS rg
                LEFT JOIN design_groups AS dg
                    ON dg.nct_id = rg.nct_id AND dg.title = rg.title
            WHERE rg.nct_id = ANY(%s)
            GROUP BY
                rg.nct_id,
                rg.title
            """,
            (nctid_list,)
        ) 
        rows = cur.fetchall()
    r = [{"nct_id": row[0], "title": row[1], "result_types": row[2], "group_types": row[3], "design_group_id": row[4], "description": row[5]} for row in rows]
    return r

def get_result_groups_and_endpoints(nct_ids):
    """Result groups are the groups that are results are reported for. 
    Different endpoints are reported split into different groups. 
    This list the exaustive list of groups, and the endpoints that are reported for each.
    """
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                rg.nct_id,
                rg.title,
                rg.ctgov_group_code,
                -- ARRAY_AGG(DISTINCT rg.result_type) AS result_types,
                ARRAY_AGG(DISTINCT o.title) AS endpoints,
                ARRAY_AGG(DISTINCT dg.group_type) 	AS group_types,
                ARRAY_AGG(DISTINCT dg.id)          	AS design_group_ids,
                MAX(rg.description) 	AS description
            FROM result_groups AS rg
                LEFT JOIN design_groups AS dg
                    ON dg.nct_id = rg.nct_id AND dg.title = rg.title
                JOIN outcomes AS o
                        ON rg.outcome_id = o.id
            WHERE rg.nct_id = ANY(%s)
            GROUP BY
                rg.ctgov_group_code,
                rg.title,
                rg.nct_id
            ORDER BY 
                rg.nct_id,
                rg.title,
                rg.ctgov_group_code
            """,
            (nct_ids,)
        )
        rows = cur.fetchall()
    r = [{"nct_id": row[0], "title": row[1], "ctgov_group_code": row[2], "measurements": row[3], "group_types": row[4], "design_group_ids": row[5], "description": row[6]} for row in rows]
    return r
# inggest comparator groups into 
def get_comparator_outcome_measurments(study_nctids: list[str]) -> list[dict]:
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                om.nct_id,
                om.ctgov_group_code,
                o.title,
                o.outcome_type,
                om.param_type,
                om.param_value,
                om.dispersion_type,
                om.dispersion_value,
                om.units
            FROM outcome_measurements om
            JOIN outcomes o ON o.id = om.outcome_id
            WHERE om.nct_id = ANY(%s)
            ORDER BY om.nct_id, o.title
            """,
            (study_nctids,)
        )
        rows = cur.fetchall()
    return [
        {
            "nct_id":           row[0],
            "ctgov_group_code": row[1],
            "outcome_title":    row[2],
            "outcome_type":     row[3],
            "param_type":       row[4],
            "param_value":      row[5],
            "dispersion_type":  row[6],
            "dispersion_value": row[7],
            "units":            row[8],
        }
        for row in rows
    ]

def get_potential_comparator_endpoints(study_nctids: list[str]) -> list[dict]:
    with aact.connect_aact() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT t.nct_id, t.outcome_type, t.measure, t.timeframe, t.population, t.description FROM design_outcomes AS t 
            WHERE t.nct_id = ANY(%s)
            """,
            (study_nctids,)
        )
        rows = cur.fetchall()
    r = [{"nct_id": row[0], "outcome_type": row[1], "measure": row[2], "timeframe": row[3], "population": row[4], "description": row[5]} for row in rows]
    return r

# given ids, pull data from db.studies table or aact db.

# n reported events
    # reported_events event_count for all events
    # 
# table designs
#   masking 
#       subject_masked
#       caregiver_masked
#       investigator_masked
#       outcomes_assessor_masked

# table eligibilities
#   sampling_method

# NOTE: only one study related to KRAS G12C inhibitores has results in ctgov. 
#   6 others have publications, ["41037823", "40523897", "36399068", "41940628","41325755","40333694"]


"""
SELECT o.* FROM outcome_measurements as o 
WHERE o.nct_id IN 
('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205') 
"""

"""
SELECT COUNT(*) FROM reported_events as t 
WHERE event_type = 'serious' AND event_count > 0 AND
t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205') 
"""

"""
SELECT t.* FROM reported_event_totals as t 
WHERE t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205') 
"""

# potential comparators
"""
SELECT t.* FROM design_groups as t 
WHERE t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205') 
"""

# n withdrawals
"""
SELECT t.* FROM drop_withdrawals as t 
WHERE t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205')
"""

# eligibility criteria
"""
SELECT t.criteria FROM eligibilities as t 
WHERE t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205')
"""

# published results
"""
SELECT t.* FROM study_references as t 
WHERE t.nct_id IN ('NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205')
"""
"['NCT07416058', 'NCT05769764', 'NCT05002270', 'NCT05786924', 'NCT05578092', 'NCT06119581', 'NCT05480865', 'NCT06026410', 'NCT06793215', 'NCT05485974', 'NCT05853575', 'NCT06447662', 'NCT04975256', 'NCT04699188', 'NCT05375994', 'NCT07601048', 'NCT06497556', 'NCT06300177', 'NCT07288034', 'NCT04330664', 'NCT05492045', 'NCT05840510', 'NCT06481813', 'NCT04585035', 'NCT07543172', 'NCT05074810', 'NCT04967079', 'NCT05585320', 'NCT06130254', 'NCT05374538', 'NCT05358249', 'NCT05288205']"
"['NCT00005037', 'NCT00005093', 'NCT00021008', 'NCT00022022', 'NCT00022243', 'NCT00029003', 'NCT00030420', 'NCT00030641', 'NCT00033722', 'NCT00039091', 'NCT00040885', 'NCT00045006', 'NCT00047840', 'NCT00054184', 'NCT00062101', 'NCT00064012', 'NCT00066768', 'NCT00073008', 'NCT00074204', 'NCT00075751', 'NCT00077415', 'NCT00114192', 'NCT00139711', 'NCT00160043', 'NCT00160069', 'NCT00161187', 'NCT00228358', 'NCT00238849', 'NCT00268489', 'NCT00278187', 'NCT00300586', 'NCT00305786', 'NCT00327288', 'NCT00343720', 'NCT00346645', 'NCT00359450', 'NCT00362882', 'NCT00388206', 'NCT00398138', 'NCT00400829', 'NCT00445952', 'NCT00447057', 'NCT00454194', 'NCT00499733', 'NCT00519831', 'NCT00520845', 'NCT00528281', 'NCT00530621', 'NCT00532155', 'NCT00534209', 'NCT00538850', 'NCT00638937', 'NCT00693992', 'NCT00697060', 'NCT00698815', 'NCT00738335', 'NCT00738881', 'NCT00754923', 'NCT00777309', 'NCT00989690', 'NCT01022671', 'NCT01057212', 'NCT01068587', 'NCT01107444', 'NCT01124669', 'NCT01168973', 'NCT01183858', 'NCT01204697', 'NCT01210053', 'NCT01248247', 'NCT01344824', 'NCT01362296', 'NCT01395758', 'NCT01438307', 'NCT01526928', 'NCT01620190', 'NCT01630733', 'NCT01658813', 'NCT01664533', 'NCT01708993', 'NCT01717105', 'NCT01725165', 'NCT01750281', 'NCT01773109', 'NCT01783197', 'NCT01783834', 'NCT01784640', 'NCT01846416', 'NCT01866410', 'NCT01915524', 'NCT01933932', 'NCT01982955', 'NCT01999673', 'NCT02041468', 'NCT02069418', 'NCT02132884', 'NCT02134990', 'NCT02152631', 'NCT02208843', 'NCT02250326', 'NCT02298153', 'NCT02330367', 'NCT02346370', 'NCT02424617', 'NCT02451865', 'NCT02463994', 'NCT02503358', 'NCT02520778', 'NCT02546986', 'NCT02592577', 'NCT02613507', 'NCT02623595', 'NCT02658097', 'NCT02673814', 'NCT02750215', 'NCT02823990', 'NCT02879760', 'NCT02950038', 'NCT02959437', 'NCT02967133', 'NCT02976740', 'NCT02981108', 'NCT03023423', 'NCT03048500', 'NCT03053297', 'NCT03085069', 'NCT03087448', 'NCT03133546', 'NCT03138889', 'NCT03158883', 'NCT03168464', 'NCT03176173', 'NCT03273790', 'NCT03285763', 'NCT03288870', 'NCT03304093', 'NCT03370159', 'NCT03382912', 'NCT03452592', 'NCT03468985', 'NCT03469960', 'NCT03502850', 'NCT03512847', 'NCT03669523', 'NCT03735121', 'NCT03801304', 'NCT03854227', 'NCT03922997', 'NCT03976375', 'NCT04023617', 'NCT04036682', 'NCT04044170', 'NCT04069936', 'NCT04154956', 'NCT04207775', 'NCT04303780', 'NCT04331626', 'NCT04364620', 'NCT04394624', 'NCT04413227', 'NCT04471415', 'NCT04471428', 'NCT04612673', 'NCT04614103', 'NCT04619004', 'NCT04640935', 'NCT04644237', 'NCT04656652', 'NCT04667234', 'NCT04685135', 'NCT04790682', 'NCT04811001', 'NCT04816214', 'NCT04868877', 'NCT04878107', 'NCT04884282', 'NCT05195632', 'NCT05255302', 'NCT05361174', 'NCT05364073', 'NCT05378763', 'NCT05403385', 'NCT05407155', 'NCT05488314', 'NCT05555732', 'NCT05577715', 'NCT05599789', 'NCT05631249', 'NCT05661240', 'NCT05796726', 'NCT05834348', 'NCT05862194', 'NCT05935774', 'NCT06048705', 'NCT06068153', 'NCT06106802', 'NCT06279728', 'NCT06388031', 'NCT06394674', 'NCT06487156', 'NCT06497556', 'NCT06523673', 'NCT06542731', 'NCT06555263', 'NCT06557967', 'NCT06558799', 'NCT06667076', 'NCT06668103', 'NCT06686771', 'NCT06690671', 'NCT06759857', 'NCT06761976', 'NCT06809764', 'NCT06813664', 'NCT06929936', 'NCT06933329', 'NCT07111104', 'NCT07130032', 'NCT07140016', 'NCT07144280', 'NCT07154368', 'NCT07164170', 'NCT07174388', 'NCT07185997', 'NCT07193160', 'NCT07213076', 'NCT07242274', 'NCT07246863', 'NCT07288034', 'NCT07363811', 'NCT07420439', 'NCT07463677', 'NCT07609251']"

nsclc_ppp = "['NCT02142738', 'NCT02220894', 'NCT02578680', 'NCT03515837', 'NCT03631199', 'NCT03645928', 'NCT03774732', 'NCT03850444', 'NCT03950674', 'NCT03976323', 'NCT04094909', 'NCT04194944', 'NCT04222972', 'NCT04547504', 'NCT04619797', 'NCT04736173', 'NCT04956692', 'NCT05048797', 'NCT05226598', 'NCT05255302', 'NCT05502237', 'NCT05555732', 'NCT05687266', 'NCT05722015', 'NCT05775289', 'NCT05791097', 'NCT05979818', 'NCT06008093', 'NCT06151574', 'NCT06212752', 'NCT06236438', 'NCT06311721', 'NCT06627647', 'NCT06687369', 'NCT06711900', 'NCT06726265', 'NCT06772623', 'NCT06793215', 'NCT06840782', 'NCT06875310', 'NCT06899126', 'NCT07178795', 'NCT07524257']"
ppp2 = "['NCT03976323', 'NCT04194944', 'NCT02142738', 'NCT06212752', 'NCT05775289', 'NCT05722015', 'NCT02220894', 'NCT03850444', 'NCT02578680', 'NCT03425643', 'NCT04956692', 'NCT03631199', 'NCT02591615', 'NCT04619797', 'NCT04524689', 'NCT05226598', 'NCT03950674', 'NCT03515837', 'NCT04222972']"
# Im only getting 9 studies with extractible comparator data, totalling to 16 arms.
# currently im joining to get the 'group_type' of the comparator arm, but I should instead just pull all arms with results and keep the desctiptions.


# stable arm UID; 
# linked study UID and NCT ID;
# arm title and type;
# regimen;
# provisional role;
# population summary;
# endpoint summary;
# source field and source text;
# extraction method;
# confidence;
# review status.
"""
SELECT
    rg.nct_id,
    rg.ctgov_group_code,
    rg.title,
    rg.result_type,
    dg.group_type,
    MIN(dg.id)              AS design_group_id,
    MIN(rg.description)     AS description
FROM result_groups AS rg
    LEFT JOIN design_groups AS dg
        ON dg.nct_id = rg.nct_id AND dg.title = rg.title
WHERE rg.nct_id = ANY(%s)
GROUP BY
    rg.nct_id,
    rg.ctgov_group_code,
    rg.title,
    dg.group_type,
    rg.result_type
"""

"""
WITH arms AS (
	SELECT
		rg.nct_id,
		rg.title,
		ARRAY_AGG(DISTINCT rg.result_type) AS result_types,
		ARRAY_AGG(DISTINCT dg.group_type) 	AS group_types,
		ARRAY_AGG(DISTINCT dg.id)          	AS design_group_ids,
		MAX(rg.description) 	AS description
	FROM result_groups AS rg
		LEFT JOIN design_groups AS dg
			ON dg.nct_id = rg.nct_id AND dg.title = rg.title
	WHERE rg.nct_id = ANY(ARRAY['NCT03976323', 'NCT04194944', 'NCT02142738', 'NCT06212752', 'NCT05775289', 'NCT05722015', 'NCT02220894', 'NCT03850444', 'NCT02578680', 'NCT03425643', 'NCT04956692', 'NCT03631199', 'NCT02591615', 'NCT04619797', 'NCT04524689', 'NCT05226598', 'NCT03950674', 'NCT03515837', 'NCT04222972'])
	GROUP BY
		rg.nct_id,
		rg.title
	)
SELECT
	arms.nct_id,
	arms.title as arm_title,
	rg.ctgov_group_code as rg_gc,
	o.title AS outcome_title,
	-- o.id as o_id,
	om.ctgov_group_code as om_gc,
	om.units,
	om.param_value
	
	-- om.classification,
	-- -- om.description AS om_desc,
	-- om.param_type,
-- FROM outcomes as o
-- 	JOIN outcome_measurements AS om
-- 		ON om.outcome_id = o.id
-- 	JOIN result_groups as rg
-- 		ON rg.outcome_id = o.id
-- 	RIGHT JOIN arms
-- 		ON rg.nct_id = arms.nct_id AND rg.title = arms.title
FROM arms
	LEFT JOIN result_groups as rg
		ON rg.nct_id = arms.nct_id AND rg.title = arms.title
	JOIN outcomes as o
		ON rg.outcome_id = o.id
	JOIN outcome_measurements AS om
		ON om.outcome_id = o.id AND rg.ctgov_group_code = om.ctgov_group_code
ORDER BY arms.nct_id, arms.title, o.title
TACT/backend_py/evidence_objects.py
"""

studies_view_link = "https://clinicaltrials.gov/expert-search?term=NCT03976323%0ANCT04194944%0ANCT02142738%0ANCT06212752%0ANCT05775289%0ANCT05722015%0ANCT02220894%0ANCT03850444%0ANCT02578680%0ANCT03425643%0ANCT04956692%0ANCT03631199%0ANCT02591615%0ANCT04619797%0ANCT04524689%0ANCT05226598%0ANCT03950674%0ANCT03515837%0ANCT04222972&page=2"