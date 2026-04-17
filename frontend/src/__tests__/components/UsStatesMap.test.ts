import { describe, it, expect } from "vitest";
import { aggregateByState } from "../../components/maps/UsStatesMap";
import type { Trial } from "../../api/trials";

const trial = (
  nctId: string,
  locations: { state?: string; country?: string }[]
): Trial => ({
  nctId,
  briefTitle: "",
  overallStatus: "",
  phases: [],
  conditions: [],
  briefSummary: "",
  locations,
});

describe("aggregateByState", () => {
  it("counts one trial per state regardless of how many sites it has in that state", () => {
    const trials = [
      trial("NCT001", [
        { state: "Massachusetts", country: "United States" },
        { state: "Massachusetts", country: "United States" }, // duplicate — should not double-count
        { state: "California", country: "United States" },
      ]),
    ];
    const result = aggregateByState(trials);
    expect(result["Massachusetts"]).toBe(1);
    expect(result["California"]).toBe(1);
  });

  it("counts across multiple trials", () => {
    const trials = [
      trial("NCT001", [{ state: "Texas", country: "United States" }]),
      trial("NCT002", [{ state: "Texas", country: "United States" }]),
    ];
    const result = aggregateByState(trials);
    expect(result["Texas"]).toBe(2);
  });

  it("excludes non-US locations", () => {
    const trials = [
      trial("NCT001", [
        { state: "Ontario", country: "Canada" },
        { state: "California", country: "United States" },
      ]),
    ];
    const result = aggregateByState(trials);
    expect(result["Ontario"]).toBeUndefined();
    expect(result["California"]).toBe(1);
  });

  it("returns an empty object for trials with no locations", () => {
    expect(aggregateByState([trial("NCT001", [])])).toEqual({});
  });
});
