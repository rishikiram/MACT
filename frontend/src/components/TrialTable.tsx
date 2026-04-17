import { useState } from "react";
import type { Trial } from "../api/trials";

interface Props {
  trials: Trial[];
}

export function TrialTable({ trials }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (trials.length === 0) {
    return <p style={{ padding: "16px", color: "var(--text)" }}>No trials to display.</p>;
  }

  return (
    <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {trials.map((trial) => {
        const isOpen = expandedId === trial.nctId;
        return (
          <li
            key={trial.nctId}
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <button
              onClick={() => setExpandedId(isOpen ? null : trial.nctId)}
              style={{
                width: "100%",
                textAlign: "left",
                padding: "14px 16px",
                background: "none",
                border: "none",
                cursor: "pointer",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "12px",
                color: "var(--text-h)",
                font: "inherit",
              }}
            >
              <span style={{ flex: 1 }}>{trial.briefTitle}</span>
              <span
                style={{
                  fontSize: "12px",
                  color: "var(--text)",
                  whiteSpace: "nowrap",
                }}
              >
                {trial.overallStatus}
              </span>
              <span style={{ fontSize: "12px", color: "var(--text)" }}>
                {isOpen ? "▲" : "▼"}
              </span>
            </button>

            {isOpen && (
              <div
                style={{
                  padding: "0 16px 16px",
                  textAlign: "left",
                  fontSize: "15px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "8px",
                }}
              >
                <div>
                  <strong>ID:</strong> {trial.nctId}
                </div>
                {trial.phases.length > 0 && (
                  <div>
                    <strong>Phase:</strong> {trial.phases.join(", ")}
                  </div>
                )}
                {trial.conditions.length > 0 && (
                  <div>
                    <strong>Conditions:</strong> {trial.conditions.join(", ")}
                  </div>
                )}
                {trial.locations.length > 0 && (
                  <div>
                    <strong>Sites:</strong> {trial.locations.length} location
                    {trial.locations.length !== 1 ? "s" : ""}
                  </div>
                )}
                {trial.briefSummary && (
                  <div>
                    <strong>Summary:</strong>
                    <p style={{ margin: "4px 0 0", color: "var(--text)" }}>
                      {trial.briefSummary}
                    </p>
                  </div>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
