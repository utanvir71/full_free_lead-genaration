# Release checklist

- [ ] Use Python 3.12 and install `.[dev]`.
- [ ] Run the full pytest suite, Ruff, mypy, and the Playwright suite.
- [ ] Start Uvicorn with `--host 127.0.0.1`; do not expose the server remotely.
- [ ] Confirm the run form, evidence review, manual notes/statuses, local draft
      copy action, and both CSV downloads work from a fresh browser.
- [ ] Confirm no page or route exposes Gmail, SMTP, sending, scheduling, or
      guessed contacts.
- [ ] Confirm Host, Origin, CSRF, CSP, URL/redirect safety, robots, and draft
      grounding tests pass.
- [ ] Restart the app and confirm the SQLite database, drafts, and registered
      CSV projections remain available.

## Optional live smoke procedure

This is opt-in and is not part of automated verification. Use one city, a
candidate limit of one, and initiate only one run. Confirm that exactly one
Overpass discovery request occurs, then inspect the resulting local run. Do not
create Gmail drafts, send email, probe SMTP, or take any outreach action.

## Recovery

After an interruption, restart the same local application. Persisted jobs are
reconciled from SQLite: recoverable expired jobs return to pending and completed
stages remain intact. Review typed errors from the run and lead pages before
manually retrying recoverable work.
