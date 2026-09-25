# Everyday Swedish Vocabulary website

Interactive static website generated from the Swedish-English-Hindi vocabulary book.

## Data layout

The site no longer ships one large `data.js` bundle. It uses:

- `dist/data/manifest.json` for category metadata, grammar notes, and quick-reference IDs.
- `dist/data/chunks/*.json` for one vocabulary component/category per file.
- `dist/app.js` lazy-loads only the selected category. It loads all chunks only when the final `All categories` option is selected or when the quick reference needs all items.

## Checks

Run:

```bash
node scripts/validate-vocabulary.mjs
node scripts/suggest-new-words.mjs
```

GitHub Actions runs the same validation on pull requests, pushes, and a weekly schedule. The weekly job creates a `vocabulary_suggestions.md` artifact with candidate words to review before adding them.
