import json
from datetime import datetime, timezone


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

def process_ctgov_comparator_arms(raw: dict) -> list[dict]:
    comparator_arm_rows = []
    ps = raw.get("protocolSection", {})
    arms = ps.get("armsInterventionsModule", {}).get("armGroups", {})
    outcomes = raw.get("resultsSection", {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
    outcome_summary = [j["title"] for j in outcomes if j["type"] == "PRIMARY"] # TODO error here, 
    
    nct_id = ps.get("identificationModule", {}).get("nctId")
    idx = 0
    for arm in arms:
        comparator_arm_rows.append({
            "uid":      f"COMP-{nct_id}-{idx}",
            "nct_id":   nct_id,
            "title":	arm.get("label", "no data"),
            "type":	    arm.get("type", "no data"),
            "regimen":	arm.get("description", "no data"),
            "interventions":    json.dumps(arm.get("interventionNames", [])),
            "population_summary":   ps.get("eligibilityModule", {}).get("eligibilityCriteria", "no data"),
            "endpoint_summary":     json.dumps(outcome_summary)
        })
        idx += 1
    return comparator_arm_rows


def check_ctgov_study(raw: dict) -> list:
    problems = []
    # check if reported events groups are the same as comparator groups
    # check if primary outcomes are consitently labeled primary outcomes.
    return problems


