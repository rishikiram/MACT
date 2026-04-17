import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchTrials } from "../../api/trials";

const mockStudy = {
  protocolSection: {
    identificationModule: { nctId: "NCT001", briefTitle: "Diabetes Study" },
    statusModule: { overallStatus: "RECRUITING" },
    designModule: { phases: ["PHASE2"] },
    conditionsModule: { conditions: ["Diabetes"] },
    contactsLocationsModule: {
      locations: [{ city: "Boston", state: "Massachusetts", country: "United States" }],
    },
    descriptionModule: { briefSummary: "A study on diabetes." },
  },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("fetchTrials", () => {
  it("calls the correct URL and returns mapped trials", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ studies: [mockStudy], nextPageToken: "tok123" }),
      })
    );

    const result = await fetchTrials({ condition: "diabetes" });

    expect(fetch).toHaveBeenCalledWith("/api/trials?query.cond=diabetes");
    expect(result.trials).toHaveLength(1);
    expect(result.trials[0]).toEqual({
      nctId: "NCT001",
      briefTitle: "Diabetes Study",
      overallStatus: "RECRUITING",
      phases: ["PHASE2"],
      conditions: ["Diabetes"],
      locations: [{ city: "Boston", state: "Massachusetts", country: "United States" }],
      briefSummary: "A study on diabetes.",
    });
    expect(result.nextPageToken).toBe("tok123");
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: false, status: 502 })
    );

    await expect(fetchTrials({ condition: "diabetes" })).rejects.toThrow(
      "Request failed: 502"
    );
  });
});
