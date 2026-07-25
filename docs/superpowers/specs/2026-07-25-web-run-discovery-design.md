# Web Run Discovery Design

## Goal

Make a run started from the local web form perform a real, bounded restaurant
discovery instead of remaining `running` with zero counters.

## Scope

When the operator starts a run, the application will launch one local
background task for that run. The task will make one Overpass request for the
selected Census place and state, respecting the existing candidate limit. It
will reconcile the returned restaurant candidates into SQLite, crawl only
official URLs supplied by OpenStreetMap, extract public role-based business
emails and evidence, score each lead, write local review drafts, and create
qualified and rejected CSV projections.

If Overpass fails or the selected place cannot be resolved, the run will become
`failed` and show a typed, human-readable error. A downstream website failure
is persisted for that restaurant while the rest of the run continues. A run
that finds no matching restaurants will become `completed` with a discovered
count of zero.

## Architecture

- `RunService` remains responsible for creating and cancelling runs.
- A web-run orchestration service composes the existing Overpass client,
  crawler, extractors, scoring, local Ollama/fallback drafting, and CSV export
  services.
- The `/runs` route schedules that service with FastAPI's local background-task
  mechanism only after the run record has been created.
- The orchestration service checks whether the run was cancelled before writing
  results and never changes a cancelled run to completed.
- The run-detail query reads persisted candidates from SQLite and renders their
  names, website, and phone only when those values came from OpenStreetMap.

## Boundaries

- One Overpass discovery request per run; no paid providers.
- Crawl only the OpenStreetMap-provided official site, honor robots and the
  existing six-page budget, and never guess contacts.
- Draft files and SQLite drafts are local review artifacts only: no Gmail,
  SMTP, sending, or scheduling.
- The local Uvicorn process is the only worker; no external queue or daemon is
  introduced.

## Verification

- Unit tests cover successful discovery, empty discovery, provider failure, and
  cancellation before results are persisted.
- Web tests prove a new run schedules orchestration and that the detail page
  renders persisted candidates.
- Browser coverage uses a local, deterministic provider fake; the automated
  suite never calls Overpass.
- A separate opt-in manual smoke run may use one place and a limit of one.
