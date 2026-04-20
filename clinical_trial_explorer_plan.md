# Clinical Trial Explorer

A local web app that fetches clinical trial data from ClinicalTrials.gov and displays it as an interactive list and map.

## How it runs

Two terminals:

| | Command | URL |
|---|---|---|
| Frontend | `npm run dev` in `/frontend` | `http://localhost:3000` |
| Backend | `npm run dev` in `/backend` | `http://localhost:3001` |

## Architecture

The frontend never calls ClinicalTrials.gov directly. All requests go through the Express backend, which forwards them to the CT.gov v2 API and pipes the response back.

```
Browser → localhost:3001/api/trials?... → clinicaltrials.gov/api/v2/studies?...
```

Preset queries are defined in `frontend/src/api/queries.ts` as named `FetchTrialsParams` objects (e.g. `ONCOLOGY`, `NSCLC`, `RECRUITING_DIABETES`). The user selects one via toggle buttons in `App.tsx`, which drives `useTrials` — a TanStack Query hook wrapping `fetchTrials`.

## Components

**`TrialTable.tsx`** — renders trials as an expandable list. Click a row to see NCT ID, phase, conditions, site count, and brief summary.

**`MapShell.tsx`** — thin MapLibre GL wrapper. Accepts `sources`, `layers`, and an `onLoad` callback that hands back the live map instance.

**`UsStatesMap.tsx`** — choropleth of trials per US state. `aggregateByState` counts trials per state (one count per trial regardless of how many sites it has there), enriches the bundled GeoJSON with that count, and passes it to `MapShell`. Hovering a state shows a popup with the state name and trial count. When `trials` changes, `source.setData()` updates the map in place without remounting.

## Adding a new map

Create a new file in `frontend/src/components/maps/`. Accept `trials: Trial[]` as a prop, transform the data, and pass GeoJSON sources and MapLibre layer configs to `MapShell`.

## Tech stack

React + Vite · TanStack Query · MapLibre GL JS · Node.js + Express · TypeScript throughout

## Tests

- **Backend** (Jest + Supertest): proxy forwards correctly, responds 502 on upstream error
- **Frontend** (Vitest): `fetchTrials` URL and response mapping, `useTrials` success/error/disabled states, `TrialTable` render and expand/collapse, `aggregateByState` count logic

## ClinicalTrials.gov API

- https://clinicaltrials.gov/data-api/api
-  

---

# Things to Implement

## making a dataset from a query

Adds a new `GET /api/trials/all` endpoint to the backend. It accepts the same query parameters as `/api/trials` but paginates through every page of CT.gov results and returns them combined in a single response.

### How it works

1. The frontend calls `/api/trials/all` with the same params used for single-page queries (condition, status, phase, etc.).
2. The backend forces `pageSize=1000` (the maximum) and runs a pagination loop:
   - Fetch page → accumulate `studies` array → check for `nextPageToken`
   - If `nextPageToken` is present, repeat with `pageToken=<token>`
   - Stop when no `nextPageToken` is returned
3. Return `{ studies: [...all pages combined], totalCount: number }` as a single JSON response.

### Backend changes (`backend/server.ts`)

- Add a `fetchAllPages(baseParams: URLSearchParams)` async helper using Node's native `fetch` (Node 18+) — simpler than streaming `https.get` for JSON accumulation.
- Register `GET /api/trials/all` as a new route that calls `fetchAllPages` and sends the combined result.
- The existing `/api/trials` single-page route is unchanged.
- Add a hard cap (e.g. 20 pages = 20,000 studies) to prevent runaway loops.
- Log each page fetch to the console so progress is visible in the terminal.

### Frontend changes (`frontend/src/api/trials.ts`)

- Add a `fetchAllTrials(params)` function alongside the existing `fetchTrials` — calls `/api/trials/all` and returns the same `FetchTrialsResult` type.
- Add a `useAllTrials(params)` hook in `hooks/` that wraps `fetchAllTrials` with TanStack Query.
- Any preset in `queries.ts` that needs the full dataset (e.g. `ONCOLOGY`, `NSCLC`) can be passed to `useAllTrials` instead of `useTrials`.

### Constraints

- The frontend waits for the full response before rendering — the existing `isLoading` state in `useAllTrials` already handles this. For large queries this could take several seconds.
- `pageToken` should be stripped from any params passed to `/api/trials/all` since pagination is managed internally by the backend.

## make a scatter map
- every study is given a point that is somewhat transparent. Dense points should overlap and create a more intense color.
- hovering over a point should display some basic information about the study.

## make a heatmap
- use mapbox gl js heatmap tool

