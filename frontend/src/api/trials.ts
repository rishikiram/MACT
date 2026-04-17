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
  phase?: string;
  pageSize?: number;
  pageToken?: string;
}

export interface FetchTrialsResult {
  trials: Trial[];
  nextPageToken?: string;
}

export async function fetchTrials(
  params: FetchTrialsParams
): Promise<FetchTrialsResult> {
  const query = new URLSearchParams();
  if (params.condition) query.set("query.cond", params.condition);
  if (params.term) query.set("query.term", params.term);
  if (params.status) query.set("filter.overallStatus", params.status);
  if (params.phase) query.set("filter.phase", params.phase);
  if (params.pageSize) query.set("pageSize", String(params.pageSize));
  if (params.pageToken) query.set("pageToken", params.pageToken);

  const res = await fetch(`/api/trials?${query.toString()}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data: any = await res.json();

  const trials: Trial[] = (data.studies ?? []).map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (study: any): Trial => {
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
  );

  return { trials, nextPageToken: data.nextPageToken };
}
