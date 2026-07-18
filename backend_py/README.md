# Clinical Trial Traceability Database

## Core Components
- Database for comparator groups in clinical trials, processsing data from ClinicalTrials.gov. 
- Entities designed to handle overlapping 'groups' of patients within a study, and relate information accuratly and traceably
- Designed to be able to track expert input

## Objects
### Primary Objects
#### Comparator Groups 
Groups defined in one of three sections of CTGov data: 1) planned comparator arms (found in armsInterventionsModule), 2) reported outcomes groups (found in outcomeMeasuresModule), and 3) reported event groups (found in adverseEventsModule). These groups can be redundant, or not. Most studies report results according to different groups that how the document the comparator arms. This table contains all of the reported groups, and allows pointers to be made from a redundant group to an singular group (see  comparator_groups.next_version_id). This feature can also be used point an outdated row to an updated row, say after an expert review.
#### Adverse Events 
All events reported in the data ingested. Many studies have a large number of different events reported
#### Reported Events
A link between (a comparator group) and (an adverse event), and associated numbers of reported events.
#### Outcomes
Outcomes are endpoints or measurments that a study reports to test their hypothesis. Many studies in the same domain will measure similar outcomes, but the specific methods, units, or descriptons used by each study often differ. This table stores all reported outcomes from the data.

### Secondary Objects
#### Queries
Queries represent a specific search of CTGov, and are linked to a set of studies that are the search results. Queries are why any particular study in the database was ingested
#### Studies
Studies represent a registered study from CTGov. Right now, they are mostly there because they are easy to store.