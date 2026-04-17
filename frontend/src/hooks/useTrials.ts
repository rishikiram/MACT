// TanStack Query hook for trial data
import { useQuery } from "@tanstack/react-query";
import { fetchTrials } from "../api/trials";
import type { FetchTrialsParams } from "../api/trials";

export function useTrials(params: FetchTrialsParams) {
  return useQuery({
    queryKey: ["trials", params],
    queryFn: () => fetchTrials(params),
    enabled: Boolean(params.condition || params.term),
  });
}
