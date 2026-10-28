# Språkverkstan Swedish learning studio

Interactive Swedish-English-Hindi learning website with vocabulary, grammar notes, pronunciation practice, sentence examples, and quick tests.

## Run locally

The site can still be opened as a static website from `docs/index.html`. To run the service locally, set a session secret and start Flask:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python server.py
```

The app is served at `http://localhost:8080`. The backend uses an application factory with separate configuration, model, authentication, and learning API modules. It provides registration, login, signed sessions, and per-user progress synchronization. Apply the initial schema and vocabulary import before starting the service:

```bash
.venv/bin/python -m scripts.migrate_database
.venv/bin/python -m scripts.import_wikidata_vocabulary
```

SQLite is the default and stores its database in `instance/sprakverkstan.db`. Set `DATABASE_URL` to a SQLAlchemy PostgreSQL URL to use PostgreSQL instead, for example `postgresql://USER:PASSWORD@HOST:5432/DBNAME`; the PostgreSQL driver is included in `requirements.txt`. Cloud Run enables secure session cookies automatically; set `COOKIE_SECURE=true` for other HTTPS deployments. SQLite files on Cloud Run are ephemeral and are not shared between instances, so use PostgreSQL for persistent multi-instance deployment.

## Deploy to Cloud Run

The deployment uses the `DATABASE_URL` Secret Manager secret rather than copying the local `.env` file. Keep `.env` local; `.gitignore`, `.dockerignore`, and `.gcloudignore` exclude it from Git and build contexts. Grant the Cloud Run runtime service account access to both `DATABASE_URL` and `SECRET_KEY`. The container runs database migrations at startup.

The GitHub Actions workflow in `.github/workflows/deploy-cloud-run.yml` runs the Python tests and deploys every push to `main`; it can also be started manually from the Actions tab. It builds and publishes the Docker image to `us-central1-docker.pkg.dev/pratik151/cloud-run-source-deploy/sprakverkstan` and deploys the public `sprakverkstan` service in `us-central1`. The container runs database migrations on startup and reads `DATABASE_URL` and `SECRET_KEY` from Secret Manager.

Configure Workload Identity Federation to trust this repository and grant the service account permission to build and publish images, deploy Cloud Run services, and act as the Cloud Run runtime service account. Enable the Cloud Build, Artifact Registry, and Cloud Run APIs, and create the Artifact Registry repository `cloud-run-source-deploy` in `us-central1`. The Cloud Run runtime service account needs Secret Manager access to the `SECRET_KEY` secret, which the workflow binds as an environment variable; the workflow enables secure cookies.

For a one-time manual deployment, use:

```bash
gcloud builds submit --project pratik151 --tag us-central1-docker.pkg.dev/pratik151/cloud-run-source-deploy/sprakverkstan .
gcloud run deploy sprakverkstan --project pratik151 --image us-central1-docker.pkg.dev/pratik151/cloud-run-source-deploy/sprakverkstan --region us-central1 --allow-unauthenticated --set-env-vars COOKIE_SECURE=true,DATABASE_URL=sqlite:////app/instance/sprakverkstan.db --set-secrets SECRET_KEY=SECRET_KEY:latest
```

Cloud Run supplies the `PORT` environment variable; the included Gunicorn command binds to it automatically.

## Data layout

Vocabulary records are imported into the database by the versioned migrations. The browser calls `GET /api/vocabulary?category=<slug>` and receives only that category; quick reference, search, filters, and review IDs are also resolved by the API. Responses are paged in batches of 50 and append only when requested. Only pronunciation explicitly walks all pages; grammar and situation documents are fetched from database APIs when their tabs are opened.

Visitors can explore the first 20 beginner phrases and three introductory grammar lessons. Signing in or creating an account unlocks the full vocabulary, grammar guide, and other study activities. These limits are enforced by the API as well as the interface; unauthenticated vocabulary searches do not trigger the online lookup.

When a vocabulary search has no local match, the API searches Wikidata Lexemes for Swedish lemmas and English glosses, then saves new matches in the database under the attributed `open-vocabulary` category. The source publishes structured data under CC0; each saved entry includes its Lexeme URL and license. These entries are also available to later searches and under the open-vocabulary category. Review entries before treating translations as classroom-quality; Wikidata does not guarantee completeness or pedagogy. To import a larger batch ahead of time, run `scripts.import_wikidata_vocabulary`.

The latest grammar expansion was cross-checked against [Swedish grammar](https://en.wikipedia.org/wiki/Swedish_grammar) and [SwedishGrammar.com](https://www.swedishgrammar.com/). Lesson wording and examples were written for this app; each new lesson links its reference, and Wikipedia-derived references are identified as CC BY-SA 4.0.

Checked-in seed and lesson data is organized as:

- `docs/data/manifest.json`, `docs/data/chunks/*.json`, `docs/data/grammar.json`, and `docs/data/situations.json` are checked-in migration seeds; runtime content is served from the database.

## Checks

Run:

```bash
node scripts/validate-vocabulary.mjs
node scripts/suggest-new-words.mjs
```

GitHub Actions runs the same validation on pull requests, pushes, and a weekly schedule. The weekly job creates a `vocabulary_suggestions.md` artifact with candidate words to review before adding them.

## AI coding context

Start with `AGENTS.md`, then open only the relevant note under `docs/context/`. Check context freshness with:

```bash
python scripts/update_context.py --check
```

After source changes, run `python scripts/update_context.py --update` to refresh the deterministic code map and manifest. If it reports stale curated notes, update those notes from source and acknowledge each reviewed section, for example `python scripts/update_context.py --acknowledge BUSINESS_LOGIC DATA_FLOW`. Use `PROJECT_CONTEXT`, `BUSINESS_LOGIC`, and `DATA_FLOW` as section names. `--check` is read-only; acknowledgements update coverage only after review. The updater does not invoke an LLM.
