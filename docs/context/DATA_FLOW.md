# Data flow

- `server.py` creates the Flask app through `sprakverkstan.create_app`; it registers `/api` routes and serves the static app from `docs/`.
- In Cloud Run, `DATABASE_URL` and `SECRET_KEY` are injected from Secret Manager; local `.env` files are excluded from deployment build contexts.
- `scripts/migrate_database.py` applies ordered migrations. Migrations import checked-in vocabulary, grammar, and situation data into SQLAlchemy tables; later situation expansions append new scenario IDs to existing database content.
- Browser vocabulary requests go to `/api/vocabulary` with a category, set, IDs, or all selector and pagination/filter parameters. `/api/manifest`, `/api/grammar`, and `/api/situations` provide learning content.
- Registration/login establish a signed Flask session. `/api/me` reads it; `/api/progress` reads or replaces the user's JSON progress. The browser merges local and server progress when refreshing a profile.
- External vocabulary search uses Wikidata's SPARQL endpoint and stores returned lexemes separately from seeded vocabulary.

Inspect `sprakverkstan/__init__.py`, `sprakverkstan/routes/`, and `docs/modules/` for current request and response details.
