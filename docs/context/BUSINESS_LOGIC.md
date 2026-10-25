# Business logic

- Vocabulary is seeded from `docs/data/` by versioned migrations. The browser requests a category at a time; list responses are paged, while pronunciation can request all pages.
- Vocabulary search checks stored words first. If no stored match exists, the API may query Wikidata and persist new CC0 entries as open vocabulary. Imported glosses are not guaranteed to be classroom-quality.
- Grammar and situation lessons are migrated into `learning_content` and loaded only when their views are opened.
- Progress is available locally in the browser; a signed-in learner can sync the JSON progress object to their account. Account identity is server-session based.
- Account registration requires a non-empty name, a valid-looking email and an eight-character minimum password. Email is normalized to lowercase; duplicate email registration is rejected.

Verify behavior in `sprakverkstan/routes/`, `sprakverkstan/migrations/`, and `docs/app.js` before changing these rules.
