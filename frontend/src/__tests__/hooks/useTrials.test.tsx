import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { useTrials } from "../../hooks/useTrials";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useTrials", () => {
  it("resolves with data on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          studies: [
            {
              protocolSection: {
                identificationModule: { nctId: "NCT001", briefTitle: "Test" },
                statusModule: { overallStatus: "RECRUITING" },
                designModule: { phases: [] },
                conditionsModule: { conditions: ["Diabetes"] },
                contactsLocationsModule: { locations: [] },
                descriptionModule: { briefSummary: "" },
              },
            },
          ],
        }),
      })
    );

    const { result } = renderHook(() => useTrials({ condition: "diabetes" }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.trials).toHaveLength(1);
    expect(result.current.data?.trials[0].nctId).toBe("NCT001");
  });

  it("sets isError when fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 500 })
    );

    const { result } = renderHook(() => useTrials({ condition: "cancer" }), {
      wrapper,
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("does not fetch when no condition or term is provided", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderHook(() => useTrials({}), { wrapper });

    expect(fetchMock).not.toHaveBeenCalled();
  });
});
