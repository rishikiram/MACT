# Toolkit and Application for Clinical Trials (TACT)

A toolkit for exploring ClinicalTrials.gov data — a Python pipeline for ingesting and structuring studies into a local SQLite database, paired with a web app for interactive mapping and visualization.

```
TACT/
├── backend_py/          # Python data pipeline — see backend_py/README.md
├── data/
│   └── clinical_trials.db
├── frontend/             # React + Vite web app
│   └── src/
└── backend/              # Node.js + Express API proxy
```

## Python Data Pipeline

See [`backend_py/README.md`](backend_py/README.md) for the data model. From the repo root:

```bash
pip install -r backend_py/requirements.txt
make ingest         # fetch from CT.gov, write to data/clinical_trials.db (presets: backend_py/queries_ctgov.yaml)
```

Or `make dev` to start the frontend, Node backend, and FastAPI backend together.

## Web App

| | Command | URL |
|---|---|---|
| Frontend | `npm run dev` in `/frontend` | `http://localhost:5173` |
| Backend | `npm run dev` in `/backend` | `http://localhost:3001` |

The frontend never calls ClinicalTrials.gov directly — it goes through the Express backend, which forwards to the CT.gov v2 API and caches responses to disk (`backend/cache/`).

```
frontend (React + Vite) → backend (Node.js + Express) → ClinicalTrials.gov
```

Preset queries live in `frontend/src/api/queries.ts`. Key components: `TrialTable.tsx` (results list), `MapShell.tsx` (MapLibre wrapper), `UsStatesMap.tsx` / `ScatterMap.tsx` / `HeatMap.tsx` (map views).

## Tech stack

Python 3 · SQLite · pandas · Jupyter · React + Vite · TanStack Query · MapLibre GL JS · Node.js + Express · TypeScript

## References

- [ClinicalTrials.gov API docs](https://clinicaltrials.gov/data-api/api)
