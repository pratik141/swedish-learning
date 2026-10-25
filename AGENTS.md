# Repository context

- Start with the index in `docs/context/PROJECT_CONTEXT.md`; open only the context note for the affected area.
- Use `docs/context/CODEBASE_MAP.md` to locate modules, then inspect the relevant implementation before relying on its summary.
- After changing code, run `python scripts/update_context.py --check`. If context is stale, update generated metadata with `--update`, revise affected notes, then acknowledge them with `--acknowledge SECTION`.
- Run the checks relevant to the code you changed; see `README.md` for project checks.
- After feature development is complete and relevant checks pass, commit the feature. Stage only files for that feature; never include unrelated worktree changes.
