import { useState } from "react";
// import { useTrials } from "./hooks/useTrials";
import { useAllTrials } from "./hooks/useAllTrials";
import { TrialTable } from "./components/TrialTable";
import { UsStatesMap } from "./components/maps/UsStatesMap";
import { ONCOLOGY, NSCLC, RECRUITING_DIABETES } from "./api/queries";
import type { FetchTrialsParams } from "./api/trials";

const PRESETS: { label: string; params: FetchTrialsParams }[] = [
  { label: "Oncology", params: ONCOLOGY },
  { label: "NSCLC", params: NSCLC },
  { label: "Recruiting Diabetes (Phase 2)", params: RECRUITING_DIABETES },
];

export default function App() {
  const [selected, setSelected] = useState(0);
  const { data, isLoading, isError } = useAllTrials(PRESETS[selected].params);

  const trials = data?.trials ?? [];

  return (
    <div style={{ padding: "24px", textAlign: "left" }}>
      <h1 style={{ marginTop: 0 }}>Clinical Trial Explorer</h1>

      <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
        {PRESETS.map((p, i) => (
          <button
            key={p.label}
            onClick={() => setSelected(i)}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "2px solid var(--accent-border)",
              background: selected === i ? "var(--accent-bg)" : "none",
              color: "var(--text-h)",
              cursor: "pointer",
              font: "inherit",
              fontWeight: selected === i ? 600 : 400,
            }}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading && <p>Loading trials…</p>}
      {isError && <p style={{ color: "red" }}>Failed to load trials.</p>}

      {!isLoading && !isError && (
        <>
          <p style={{ marginBottom: "16px", color: "var(--text)" }}>
            {trials.length} trial{trials.length !== 1 ? "s" : ""}
          </p>

          <UsStatesMap trials={trials} />

          <div style={{ marginTop: "24px", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden" }}>
            <TrialTable trials={trials} />
          </div>
        </>
      )}
    </div>
  );
}
