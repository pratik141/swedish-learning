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

```bash
gcloud builds submit --tag REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/sprakverkstan
gcloud run deploy sprakverkstan --image REGION-docker.pkg.dev/PROJECT_ID/REPOSITORY/sprakverkstan --region REGION --allow-unauthenticated --set-env-vars COOKIE_SECURE=true --set-secrets SECRET_KEY=SECRET_NAME:latest,DATABASE_URL=DATABASE_URL_SECRET:latest
```

Cloud Run supplies the `PORT` environment variable; the included Gunicorn command binds to it automatically.

## Data layout

Vocabulary records are imported into the database by the versioned migrations. The browser calls `GET /api/vocabulary?category=<slug>` and receives only that category; quick reference, search, filters, and review IDs are also resolved by the API. Responses are paged in batches of 50 and append only when requested. Only pronunciation explicitly walks all pages; grammar and situation documents are fetched from database APIs when their tabs are opened.

To add more words from the internet, run `scripts.import_wikidata_vocabulary`. It fetches Swedish lemmas and English sense glosses from Wikidata's SPARQL endpoint, which publishes structured data under CC0, skips existing lemmas, and stores the source Lexeme URL and license with each record. Review imported entries before treating their translations as classroom-quality; Wikidata does not guarantee completeness or pedagogy.

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
