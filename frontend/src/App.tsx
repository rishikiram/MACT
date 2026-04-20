import { useState } from "react";
import { useAllTrials } from "./hooks/useAllTrials";
import { TrialTable } from "./components/TrialTable";
import { UsStatesMap } from "./components/maps/UsStatesMap";
import { HeatMap } from "./components/maps/HeatMap";
import { ScatterMap } from "./components/maps/ScatterMap";
import { ONCOLOGY, NSCLC, RECRUITING_DIABETES } from "./api/queries";
import type { FetchTrialsParams } from "./api/trials";

const PRESETS: { label: string; params: FetchTrialsParams }[] = [
  { label: "Oncology", params: ONCOLOGY },
  { label: "NSCLC", params: NSCLC },
  { label: "Recruiting Diabetes (Phase 2)", params: RECRUITING_DIABETES },
];

const MAPS = ["Choropleth", "Heatmap", "Scatter"] as const;
type MapView = typeof MAPS[number];

function ToggleBar<T extends string>({
  options,
  selected,
  onSelect,
}: {
  options: readonly T[];
  selected: T;
  onSelect: (v: T) => void;
}) {
  return (
    <div style={{ display: "flex", gap: "8px" }}>
      {options.map((opt) => (
        <button
          key={opt}
          onClick={() => onSelect(opt)}
          style={{
            padding: "6px 14px",
            borderRadius: "6px",
            border: "2px solid var(--accent-border)",
            background: selected === opt ? "var(--accent-bg)" : "none",
            color: "var(--text-h)",
            cursor: "pointer",
            font: "inherit",
            fontWeight: selected === opt ? 600 : 400,
          }}
        >
          {opt}
        </button>
      ))}
    </div>
  );
}

export default function App() {
  const [presetIdx, setPresetIdx] = useState(0);
  const [mapView, setMapView] = useState<MapView>("Choropleth");

  const { data, isLoading, isError } = useAllTrials(PRESETS[presetIdx].params);
  const trials = data?.trials ?? [];

  return (
    <div style={{ padding: "24px", textAlign: "left" }}>
      <h1 style={{ marginTop: 0 }}>Clinical Trial Explorer</h1>

      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "24px" }}>
        <ToggleBar
          options={PRESETS.map((p) => p.label) as unknown as readonly string[]}
          selected={PRESETS[presetIdx].label}
          onSelect={(label) => setPresetIdx(PRESETS.findIndex((p) => p.label === label))}
        />
        <ToggleBar options={MAPS} selected={mapView} onSelect={setMapView} />
      </div>

      {isLoading && <p>Loading trials…</p>}
      {isError && <p style={{ color: "red" }}>Failed to load trials.</p>}

      {!isLoading && !isError && (
        <>
          <p style={{ marginBottom: "16px", color: "var(--text)" }}>
            {trials.length} trial{trials.length !== 1 ? "s" : ""}
          </p>

          {mapView === "Choropleth" && <UsStatesMap trials={trials} />}
          {mapView === "Heatmap" && <HeatMap trials={trials} />}
          {mapView === "Scatter" && <ScatterMap trials={trials} />}

          <div style={{ marginTop: "24px", border: "1px solid var(--border)", borderRadius: "8px", overflow: "hidden" }}>
            <TrialTable trials={trials} />
          </div>
        </>
      )}
    </div>
  );
}
