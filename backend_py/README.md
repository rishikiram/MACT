# Clinical Trial Traceability Database

## Core Components
- Database for tracking and connecting information for clinical trial feasibilty. 
- Programmable gaps, that realate requirements to claims. Allows automated gap assessment.
- Targeted evidence-object generation from historical data. Currently utilizes CTGov and AACT.

## Objects
### Primary Objects
#### Sources
 Perhaps the least rigrously defined, sourecs are defined to be the sources of information. All information should trace back to a source.
#### Evidence-Objects
Facts or statements taken from a source that can support a conclusion. In this case, they are used to support claims. 
#### Claims
Statements that are used to demonstrate adherence to requirements. Claims are required to be supported by evidence(-objects) and their veracity depends on their evidence.
#### Requirements
Standards that determine the feasibility of a clinical trial. Requirements are dictated by an authority, and are satisfied by a set of claims.
#### Gaps
Discrepencies between a requirement and a set of supporting claims. Gaps therefore depend on the veracity of its supporting claims, and are specific to one requirement.

### Secondary Objects
#### Queries
Queries represent a specific search of CTGov, and are linked to a set of studies that are the search results. Queries are how I am determining which studies might have relevant information to which claims.
#### Studies
Studies represent a registered study from CTGov. Right now, they are mostly unecessary other than tracking their nct_id. The actual data related to them is pulled from AACT, which has process the data into a rich relational database.