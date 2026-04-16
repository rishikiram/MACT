# Clinical Trial Explorer — Project Plan

## What this app does

- Fetches clinical trial data from the ClinicalTrials.gov v2 REST API via a lightweight local backend
- Displays a searchable table of trials
- Displays maps defined as reusable code components

---

## Tech stack

- **React + Vite** — frontend
- **TanStack Query** — data fetching
- **MapLibre GL JS** — map rendering
- **Node.js + Express** — lightweight backend/proxy
- **TypeScript** throughout

---

## How it runs locally

Two terminal windows:

| Terminal | Command | URL |
|---|---|---|
| 1 — Frontend | `npm run dev` (inside `/frontend`) | `http://localhost:3000` |
| 2 — Backend | `node server.ts` (inside `/backend`) | `http://localhost:3001` |

The frontend never calls the NIH API directly. It calls `localhost:3001`, and the backend forwards the request to ClinicalTrials.gov and returns the result.

---

## Folder structure

```
clinical-trial-explorer/
├── frontend/
│   └── src/
│       ├── api/
│       │   └── trials.ts         # All fetch calls — points to localhost:3001
│       ├── components/
│       │   ├── TrialTable.tsx    # Searchable table
│       │   └── maps/
│       │       ├── MapShell.tsx  # Reusable MapLibre wrapper
│       │       └── UsStatesMap.tsx  # First map: choropleth by state
│       ├── hooks/
│       │   └── useTrials.ts      # TanStack Query hook
│       └── App.tsx
│
└── backend/
    └── server.ts                 # Express proxy — forwards requests to CT.gov
```

---

## Backend (`backend/server.ts`)

A minimal Express server with one job: receive requests from the frontend, forward them to the ClinicalTrials.gov API, and return the response. Add caching or extra logic here later if needed.

```ts
GET /api/trials?query.cond=diabetes&pageSize=20
→ forwards to https://clinicaltrials.gov/api/v2/studies?query.cond=diabetes&pageSize=20
```

---

## ClinicalTrials.gov v2 API

Base URL: `https://clinicaltrials.gov/api/v2/studies`

Useful query parameters:
- `query.cond` — condition (e.g. `diabetes`)
- `query.term` — keyword search
- `filter.overallStatus` — e.g. `RECRUITING`, `COMPLETED`
- `filter.phase` — e.g. `PHASE1`, `PHASE2`, `PHASE3`
- `pageSize` — results per page (max 1000)
- `pageToken` — cursor for next page

Key response fields per study (inside `protocolSection`):
- `.identificationModule.nctId`
- `.identificationModule.briefTitle`
- `.statusModule.overallStatus`
- `.designModule.phases[]`
- `.conditionsModule.conditions[]`
- `.contactsLocationsModule.locations[]` — array of `{ city, state, country, facility }`
- `.descriptionModule.briefSummary`

---

## Frontend components

### `TrialTable.tsx`
- Text input to search by condition/keyword
- Table columns: title, status, phase, conditions, location count
- Click a row to expand: shows summary, all sites, eligibility

### `MapShell.tsx`
- Thin wrapper around a MapLibre GL JS instance
- Accepts `sources` and `layers` as props
- All map components are built on top of this

### Map components (`src/components/maps/`)
Each map is a self-contained file that:
1. Receives `trials` as a prop
2. Transforms the data (e.g. count trials per US state)
3. Passes GeoJSON sources + MapLibre layer configs to `MapShell`

To add a new map, create a new file in this folder. The API returns location as text strings (city, state, country) — no coordinates. The first map component matches state name strings against a bundled static US states GeoJSON file to render a choropleth.

---

## Unit testing plan

**Backend** — Jest + Supertest. Mock `https` so no real network calls are made.

Two tests in `backend/__tests__/server.test.ts`:
1. `GET /api/trials?query.cond=diabetes` — confirm the upstream URL is built correctly and the response body is piped back.
2. Upstream error — when the mocked `https.get` emits `error`, the route responds 502.

**Frontend** — Vitest (built into Vite, zero extra config). Mock `fetch` with `vi.stubGlobal`.

One test file per module, one or two assertions each:
- `api/trials.ts` — `fetchTrials({ condition: "diabetes" })` calls the right URL and returns parsed JSON.
- `hooks/useTrials.ts` — hook resolves with data on success, sets `isError` on failure.
- `TrialTable.tsx` — given mock trials, rows render; typing in the search box filters them.
- `UsStatesMap.tsx` — extract `aggregateByState` as a pure function and test the count logic directly (no rendering needed). Mock `MapShell` to avoid WebGL.

---

## Implementation order

1. Scaffold both `frontend/` and `backend/` with TypeScript
2. Build the Express proxy in `backend/server.ts` — confirm it forwards CT.gov requests correctly
3. Build `api/trials.ts` and `useTrials.ts` — confirm data flows frontend → backend → CT.gov → back
4. Build `TrialTable.tsx` with search and expandable rows
5. Add MapLibre, build `MapShell.tsx`
6. Build `UsStatesMap.tsx` as the first map component