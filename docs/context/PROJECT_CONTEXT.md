# Project context

Språkverkstan is a Swedish-learning site: a static browser UI in `docs/` and an optional Flask/SQLAlchemy service in `sprakverkstan/`. The same checked-in vocabulary and lesson JSON is used as migration seed data; runtime API content comes from the database.

- Start points: `docs/index.html` for the browser app; `server.py` and `sprakverkstan.create_app` for Flask.
- Backend areas: JSON APIs, account sessions, SQLAlchemy models, and ordered migrations.
- Browser areas: vocabulary/practice UI, lesson data, and account/progress synchronization.
- Local checks and setup: `README.md`. Vocabulary validation runs through `.github/workflows/vocabulary-ci.yml`; pushes to `main` can deploy to Cloud Run through `.github/workflows/deploy-cloud-run.yml`.

Read `BUSINESS_LOGIC.md` for learner/account rules or `DATA_FLOW.md` for persistence and API paths. These notes are selective guides, not substitutes for the source.
