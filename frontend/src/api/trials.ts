// Fetch calls — points to /api/trials (proxied to localhost:3001 by Vite)

export interface TrialLocation {
  city?: string;
  state?: string;
  country?: string;
  facility?: string;
}

export interface Trial {
  nctId: string;
  briefTitle: string;
  overallStatus: string;
  phases: string[];
  conditions: string[];
  locations: TrialLocation[];
  briefSummary: string;
}

export interface FetchTrialsParams {
  condition?: string;
  term?: string;
  status?: string;
  // phase?: string;
  filterAdvanced?: string; 
  pageSize?: number;
  pageToken?: string;
}

export interface FetchTrialsResult {
  trials: Trial[];
  nextPageToken?: string;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapStudy(study: any): Trial {
  const p = study.protocolSection ?? {};
  return {
    nctId: p.identificationModule?.nctId ?? "",
    briefTitle: p.identificationModule?.briefTitle ?? "",
    overallStatus: p.statusModule?.overallStatus ?? "",
    phases: p.designModule?.phases ?? [],
    conditions: p.conditionsModule?.conditions ?? [],
    locations: p.contactsLocationsModule?.locations ?? [],
    briefSummary: p.descriptionModule?.briefSummary ?? "",
  };
}

function buildQuery(params: FetchTrialsParams): URLSearchParams {
  const query = new URLSearchParams();
  if (params.condition) query.set("query.cond", params.condition);
  if (params.term) query.set("query.term", params.term);
  if (params.status) query.set("filter.overallStatus", params.status);
  if (params.filterAdvanced) query.set("filter.advanced", params.filterAdvanced);
  return query;
}

export async function fetchTrials(
  params: FetchTrialsParams
): Promise<FetchTrialsResult> {
  const query = buildQuery(params);
  if (params.pageSize) query.set("pageSize", String(params.pageSize));
  if (params.pageToken) query.set("pageToken", params.pageToken);

  const res = await fetch(`/api/trials?${query.toString()}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any = await res.json();
  return { trials: (data.studies ?? []).map(mapStudy), nextPageToken: data.nextPageToken };
}

// Fetches all pages via the backend's /api/trials/all endpoint.
// pageSize and pageToken are managed by the backend — do not pass them here.
export async function fetchAllTrials(
  params: FetchTrialsParams
): Promise<FetchTrialsResult> {
  const query = buildQuery(params);

  const res = await fetch(`/api/trials/all?${query.toString()}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any = await res.json();
  return { trials: (data.studies ?? []).map(mapStudy) };
}
