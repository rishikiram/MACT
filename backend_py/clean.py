import json
from datetime import datetime, timezone

NO_DATA_VALUE = "no data"

def process_ctgov_study(raw: dict) -> dict:
    ps = raw.get("protocolSection", {})

    nct_id = ps.get("identificationModule", {}).get("nctId")
    title = ps.get("identificationModule", {}).get("briefTitle")
    if not nct_id or not title:
        return {"error": "no nct_id or title"}

    status_mod = ps.get("statusModule", {})
    design_mod = ps.get("designModule", {})
    sponsor_mod = ps.get("sponsorCollaboratorsModule", {})
    conditions_mod = ps.get("conditionsModule", {})
    arms_mod = ps.get("armsInterventionsModule", {})
    eligibility_mod = ps.get("eligibilityModule", {})
    outcomes_mod = ps.get("outcomesModule", {})

    locations_mod = ps.get("contactsLocationsModule", {})
    locations = [
        {
            "facility": loc.get("facility"),
            "city": loc.get("city"),
            "state": loc.get("state"),
            "country": loc.get("country"),
            "lat": loc.get("geoPoint", {}).get("lat"),
            "lon": loc.get("geoPoint", {}).get("lon"),
        }
        for loc in locations_mod.get("locations", [])
    ]
    multicountry = len({loc.get("country") for loc in locations}) > 1

    #designModule
    enrollment_info = design_mod.get("enrollmentInfo", {})
    design_info = design_mod.get("designInfo", {})
    
    phases = design_mod.get("phases") or []
    phase1 = "PHASE1" in phases
    phase2 = "PHASE2" in phases
    phase3 = "PHASE3" in phases
    phase4 = "PHASE4" in phases
    phase_text = "/".join(p for p in phases) or None
    # phase_text = "NA" if phase_text in {"N/A", "NOT APPLICABLE", ""} else phase_text

    return {
        "nct_id": nct_id,
        "title": title,
        
        #statusModule
        "status": status_mod.get("overallStatus"),
        "start_date": (status_mod.get("startDateStruct") or {}).get("date"),
        "start_date_type": status_mod.get("startDateStruct", {}).get("type"),
        "primary_completion_date": (status_mod.get("primaryCompletionDateStruct") or {}).get("date"),
        "primary_completion_date_type": status_mod.get("primaryCompletionDateStruct", {}).get("type"),
        "completion_date": (status_mod.get("completionDateStruct") or {}).get("date"),
        "completion_date_type": status_mod.get("completionDateStruct", {}).get("type"),
        "last_update_post": status_mod.get("lastUpdatePostDateStruct", {}).get("date"),
        
        #sponsorCollaboratorsModule
        "sponsor": sponsor_mod.get("leadSponsor", {}).get("name"),
        "sponsor_class": sponsor_mod.get("leadSponsor", {}).get("class"),
        
        #conditionsModule
        "conditions": json.dumps(conditions_mod.get("conditions") or []),
        "condition_keywords": json.dumps(conditions_mod.get("keywords") or []),
        
        #designModule
        "phase1": phase1,
        "phase2": phase2,
        "phase3": phase3,
        "phase4": phase4,
        "phase_text": phase_text,
        "study_type": design_mod.get("studyType"),
        "enrollment": enrollment_info.get("count"),
        "enrollment_type": enrollment_info.get("type"),
        "masking": design_info.get("maskingInfo", {}).get("masking"),
        "allocation": design_info.get("allocation"),
        "intervention_model": design_info.get("interventionModel"),
        "primary_purpose": design_info.get("primaryPurpose"),
        
        #eligibilityModule
        "eligibility_criteria": eligibility_mod.get("eligibilityCriteria"),
        "healthy_volunteers": eligibility_mod.get("healthyVolunteers"), # true/false?
        "sex": eligibility_mod.get("sex"),
        "std_ages": json.dumps(eligibility_mod.get("stdAges", [])),
        
        #contactsLocationsModule
        "locations": json.dumps(locations),
        "multicountry": multicountry,
        
        #outcomesModule
        "primary_outcomes": json.dumps(outcomes_mod.get("primaryOutcomes", [])),
        "secondary_outcomes": json.dumps(outcomes_mod.get("secondaryOutcomes", [])),

        "has_results": raw.get("hasResults"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }

# Scrape Groups
def process_ctgov_arm_groups(raw: dict) -> list[dict]:
    arm_group_rows = []
    ps = raw.get("protocolSection", {})
    arms = ps.get("armsInterventionsModule", {}).get("armGroups", {})
    outcomes = raw.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    outcome_summary = [j["title"] for j in outcomes if j["type"] == "PRIMARY"] # TODO error here, 
    
    nct_id = ps.get("identificationModule", {}).get("nctId")
    idx = 0
    for arm in arms:
        arm_group_rows.append({
            "uid":      f"COMP-{nct_id}-{idx}",
            "nct_id":   nct_id,
            "group_code":   f"ARM{idx:03d}", 
            "title":	arm.get("label", "no data"),
            "type":	    arm.get("type", "no data"),
            "regimen":	arm.get("description", "no data"),
            "interventions":    json.dumps(arm.get("interventionNames", [])),
            "population_summary":   ps.get("eligibilityModule", {}).get("eligibilityCriteria", "no data"),
            "endpoint_summary":     json.dumps(outcome_summary),
            "current_version_author":   "data ingestion algorithm",
            "data_source":              "design_arm"
        })
        idx += 1
    return arm_group_rows

def process_ctgov_outcome_groups(raw: dict) -> list[dict]:
    outcome_groups = []
    nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    outcomes = raw.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    group_codes = set()
    for o in outcomes:
        groups = o.get("groups", [])
        for g in groups:
            if g.get("id") not in group_codes:
                outcome_groups.append({
                    "nct_id":       nct_id,
                    "group_code":   g.get("id"),
                    "title":	    g.get("title", "no data"),
                    "regimen":	    g.get("description", "no data"),
                    "current_version_author":   "data ingestion algorithm",
                    "data_source":              "outcome_group"
                })
                group_codes.add(g.get("id"))
                # assumes good data
    return outcome_groups

def process_ctgov_event_groups(raw: dict) -> list[dict]:
    event_group_rows = []
    nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    event_groups = raw.get("resultsSection", {}).get("adverseEventsModule", {}).get("eventGroups", [])    
    for eg in event_groups:
        event_group_rows.append({
            "nct_id":       nct_id,
            "group_code":   eg.get("id"),
            "title":	    eg.get("title", "no data"),
            "regimen":	    eg.get("description", "no data"),
            "current_version_author":   "data ingestion algorithm",
            "data_source":              "event_group"
        })
    return event_group_rows

def process_all_groups(raw: dict) -> list[dict]:
    return process_ctgov_arm_groups(raw) + process_ctgov_outcome_groups(raw) + process_ctgov_event_groups(raw)

# Scrape Outcomes
def process_ctgov_outcomes(raw: dict) -> list[dict]:
    outcome_rows = []
    nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    outcomes = raw.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    idx = 0
    for o in outcomes:
        outcome_rows.append({
            "uid":      f"OUT-{nct_id}-{idx}",
            "nct_id":   nct_id,
            "title":	o.get("title", "no data"),
            "type":	    o.get("type", "no data"),
            "description":  o.get("description", "no data"),
            "population_description":       o.get("populationDescription", "no data"),
            "units":        o.get("unitOfMeasure", "no data"),
            "time_frame":   o.get("timeFrame", "no data"),
            "p_value":      o.get("analyses", [{}])[0].get("pValue", NO_DATA_VALUE)
        })
        idx += 1
    return outcome_rows

def process_planned_outcomes(raw: dict) -> list[dict]:
    planned_outcome_rows = []
    nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    primary_outcomes = raw.get("protocolSection", {}).get("outcomesModule", {}).get("primaryOutcomes", [])
    secondary_outcomes = raw.get("protocolSection", {}).get("outcomesModule", {}).get("secondaryOutcomes", [])
    idx = 0
    for po in primary_outcomes:
        planned_outcome_rows.append({
            "uid":      f"PLOUT-{nct_id}-{idx}",
            "nct_id":   nct_id,
            "title":	po.get("measure", "no data"),
            "type":	    "PRIMARY",
            "description":  po.get("description", "no data"),
            "time_frame":   po.get("timeFrame", "no data"),
        })
        idx += 1
    for po in secondary_outcomes:
        planned_outcome_rows.append({
            "uid":      f"PLOUT-{nct_id}-{idx}",
            "nct_id":   nct_id,
            "title":	po.get("measure", "no data"),
            "type":	    "SECONDARY",
            "description":  po.get("description", "no data"),
            "time_frame":   po.get("timeFrame", "no data"),
        })
        idx += 1
    return planned_outcome_rows

# Scrape Events
def process_ctgov_events(raw: dict) -> list[dict]:
    # maybe in this function, I can check for whether event_groups allign with arm_groups or if they need to be reconciled.
    events_rows = []
    nct_id = raw.get("protocolSection", {}).get("identificationModule", {}).get("nctId")
    serious_events = raw.get("resultsSection", {}).get("adverseEventsModule", {}).get("seriousEvents", [])
    # other_events = raw.get("resultsSection", {}).get("adverseEventsModule", {}).get("seriousEvents", [])
    for e in serious_events:
        reported_events = []
        for report in e.get("stats", {}):
            reported_events.append({
                "group_code":     report.get("groupId", NO_DATA_VALUE),
                "num_events":   report.get("numEvents", None),
                "num_affected": report.get("numAffected", None),
                "num_at_risk":  report.get("numAtRisk", None),
                "is_serious_event": True
            })

        events_rows.append({
            "nct_id":       nct_id,
            "term":	        e.get("term", "no data"),
            "organ_system":	        e.get("organSystem", "no data"),
            "source_vocabulary":    e.get("sourceVocabulary", "no data"),
            "assessment_type":       e.get("assessmentType", "no data"),
            "reports":              reported_events
        })
    return events_rows


def build_group_mapping(raw: dict) -> dict:
    arms = process_ctgov_arm_groups(raw)
    ogs = process_ctgov_outcome_groups(raw)
    egs = process_ctgov_event_groups(raw)

    # {redundant_group_code: updated_group_code}
    group_map = {}
    for a in arms:
        for og in ogs:
            if a["title"] == og["title"] or a["regimen"] == og["regimen"]:
                group_map[og["group_code"]] = a["group_code"]
        for eg in egs:
            if a["title"] == eg["title"] or a["regimen"] == eg["regimen"]:
                group_map[eg["group_code"]] = a["group_code"]
    for eg in egs:
        if eg["title"] not in group_map:
            for og in ogs:
                if og["title"] == eg["title"] or og["regimen"] == eg["regimen"]:
                    group_map[eg["group_code"]] = og["group_code"]

    return group_map




def check_ctgov_study(raw: dict) -> list:
    log = []
    
    ## CHEKCING GROUPS
    # check if reported events groups are the same as comparator groups
    arms = process_ctgov_arm_groups(raw)
    ogs = process_ctgov_outcome_groups(raw)
    egs = process_ctgov_event_groups(raw)
    group_mapping = build_group_mapping(raw)

    if len(arms) != len(ogs) or len(arms) != len(egs) or len(ogs) != len(egs):
        log.append(f"[groups] Extra groups present: arms={len(arms)} outcome_groups={len(ogs)} event_groups={len(egs)}")

    arm_codes = {a["group_code"] for a in arms}
    og_codes = {og["group_code"] for og in ogs}
    eg_codes = {eg["group_code"] for eg in egs}

    for source_code, target_code in group_mapping.items():
        source_type = "outcome_group" if source_code in og_codes else "event_group" if source_code in eg_codes else "unknown_group"
        target_type = "arm" if target_code in arm_codes else "outcome_group" if target_code in og_codes else "unknown_group"
        log.append(f"[groups] {source_type} {source_code!r} mapped -> {target_type} {target_code!r}")

    unmapped_groups = [og["group_code"] for og in ogs if og["group_code"] not in group_mapping]
    unmapped_groups += [eg["group_code"] for eg in egs if eg["group_code"] not in group_mapping]
    if unmapped_groups:
        log.append(f"[groups] {len(unmapped_groups)} group(s) unmapped: {unmapped_groups}")


    ## CHECKING planned vs reported OUTCOMES
    # check if primary outcomes are consitently labeled primary outcomes.
    outcomes = process_ctgov_outcomes(raw) # uses outcomeMeasures
    planned_outcomes = process_planned_outcomes(raw)
    n_primary_o = sum([o["type"] == "PRIMARY" for o in outcomes])
    n_primary_po = sum([o["type"] == "PRIMARY" for o in planned_outcomes])
    if n_primary_o != n_primary_po:
        log.append("[outcomes] Number of primary outcomes varies between planned outcomes and reported outcome measures.")
    n_secondary_o = sum([o["type"] == "SECONDARY" for o in outcomes])
    n_secondary_po = sum([o["type"] == "SECONDARY" for o in planned_outcomes])
    if n_secondary_o != n_secondary_po:
        log.append("[outcomes] Number of secondary outcomes varies between planned outcomes and reported outcome measures.")

    outcome_map = [-1] * len(outcomes)
    for i,o in enumerate(outcomes):
        for j,po in enumerate(planned_outcomes):
            if o["title"] == po["title"] or o["description"] == po["description"]:
                outcome_map[i] = j
    n_matched = sum([j < 0 for j in outcome_map])
    if n_matched < len(outcome_map):
        log.append(f"[outcomes] {len(outcome_map) - n_matched}/{len(outcome_map)} measured outcome(s) could not be matched with any planned outcome.")


    return log


