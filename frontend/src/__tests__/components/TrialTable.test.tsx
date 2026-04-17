import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TrialTable } from "../../components/TrialTable";
import type { Trial } from "../../api/trials";

const MOCK_TRIALS: Trial[] = [
  {
    nctId: "NCT001",
    briefTitle: "Diabetes Study Alpha",
    overallStatus: "RECRUITING",
    phases: ["PHASE2"],
    conditions: ["Diabetes"],
    locations: [{ city: "Boston", state: "Massachusetts", country: "United States" }],
    briefSummary: "A study on diabetes treatments.",
  },
  {
    nctId: "NCT002",
    briefTitle: "Cancer Study Beta",
    overallStatus: "COMPLETED",
    phases: ["PHASE3"],
    conditions: ["Cancer"],
    locations: [],
    briefSummary: "A study on cancer.",
  },
];

describe("TrialTable", () => {
  it("renders a row for each trial", () => {
    render(<TrialTable trials={MOCK_TRIALS} />);
    expect(screen.getByText("Diabetes Study Alpha")).toBeInTheDocument();
    expect(screen.getByText("Cancer Study Beta")).toBeInTheDocument();
  });

  it("expands a row on click and shows details", () => {
    render(<TrialTable trials={MOCK_TRIALS} />);
    fireEvent.click(screen.getByText("Diabetes Study Alpha"));
    expect(screen.getByText("NCT001")).toBeInTheDocument();
    expect(screen.getByText("A study on diabetes treatments.")).toBeInTheDocument();
  });

  it("collapses an expanded row on second click", () => {
    render(<TrialTable trials={MOCK_TRIALS} />);
    fireEvent.click(screen.getByText("Diabetes Study Alpha"));
    expect(screen.getByText("NCT001")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Diabetes Study Alpha"));
    expect(screen.queryByText("NCT001")).not.toBeInTheDocument();
  });

  it("shows a fallback message when trials is empty", () => {
    render(<TrialTable trials={[]} />);
    expect(screen.getByText("No trials to display.")).toBeInTheDocument();
  });
});
