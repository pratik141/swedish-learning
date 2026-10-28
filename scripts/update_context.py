#!/usr/bin/env python3
"""Incrementally check and refresh the repository's curated AI context."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "docs" / "context"
MANIFEST = CONTEXT / "CONTEXT_MANIFEST.json"
MAP = CONTEXT / "CODEBASE_MAP.md"
SECTIONS = ("PROJECT_CONTEXT", "CODEBASE_MAP", "BUSINESS_LOGIC", "DATA_FLOW")
CONTEXT_DOCS = (
    Path("AGENTS.md"),
    Path("docs/context/PROJECT_CONTEXT.md"),
    Path("docs/context/CODEBASE_MAP.md"),
    Path("docs/context/BUSINESS_LOGIC.md"),
    Path("docs/context/DATA_FLOW.md"),
)
EXCLUDED_PREFIXES = (
    ".venv/",
    "instance/",
    "__pycache__/",
    "docs/context/",
    ".vscode/",
)
EXCLUDED_FILES = {
    "AGENTS.md",
    "scripts/update_context.py",
    "tests/test_context_update.py",
    "reports/vocabulary_suggestions.md",
}
CODE_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".py", ".ts", ".tsx", ".html", ".css"}
SENSITIVE_NAME = re.compile(r"(^\.env(?:\.|$)|secret|credential|\.pem$|\.key$)", re.IGNORECASE)


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout


def _is_source_path(path: str) -> bool:
    pure = Path(path)
    return (
        not path.startswith(EXCLUDED_PREFIXES)
        and path not in EXCLUDED_FILES
        and not any(SENSITIVE_NAME.search(part) for part in pure.parts)
    )


def source_paths(root: Path = ROOT) -> list[str]:
    """Return tracked and non-ignored project paths, excluding generated/private files."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    paths = {
        raw.decode("utf-8", errors="surrogateescape")
        for raw in result.stdout.split(b"\0")
        if raw
    }
    return sorted(path for path in paths if _is_source_path(path) and (root / path).is_file())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 128), b""):
            digest.update(block)
    return digest.hexdigest()


def source_hashes(paths: list[str], root: Path = ROOT) -> dict[str, str]:
    return {path: sha256_file(root / path) for path in paths}


def sections_for_path(path: str) -> set[str]:
    """Map a source path to the curated notes that may need review."""
    sections = {"CODEBASE_MAP"} if Path(path).suffix.lower() in CODE_SUFFIXES else set()

    if path in {
        "README.md", "requirements.txt", "Dockerfile", ".gitignore", ".dockerignore", ".gcloudignore",
        "server.py", "sprakverkstan/config.py", "sprakverkstan/__init__.py",
        "sprakverkstan/extensions.py", "docs/ROADMAP.md",
    } or path.startswith(".github/"):
        sections.add("PROJECT_CONTEXT")

    business_paths = (
        "sprakverkstan/models.py",
        "sprakverkstan/vocabulary_lookup.py",
        "sprakverkstan/routes/",
        "sprakverkstan/migrations/",
        "docs/data/",
        "docs/app.js",
        "docs/modules/",
        "scripts/import_wikidata_vocabulary.py",
    )
    if path.startswith(business_paths):
        sections.add("BUSINESS_LOGIC")

    data_flow_paths = (
        "sprakverkstan/",
        "server.py",
        "docs/app.js",
        "docs/modules/",
        "docs/data/",
        "scripts/migrate_database.py",
        "scripts/import_wikidata_vocabulary.py",
    )
    if path.startswith(data_flow_paths):
        sections.add("DATA_FLOW")

    if path.startswith(("scripts/", "tests/")):
        sections.add("CODEBASE_MAP")

    return sections


def _symbols(path: str, root: Path) -> list[str]:
    if not path.endswith(".py"):
        return []
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise RuntimeError(f"Cannot extract symbols from {path}: {error}") from error
    return [
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]


def render_code_map(
    paths: list[str],
    root: Path = ROOT,
    hashes: dict[str, str] | None = None,
    cached_symbols: dict[str, dict] | None = None,
) -> tuple[str, dict[str, dict]]:
    hashes = hashes or {}
    cached_symbols = cached_symbols or {}
    symbols_cache = {}
    rows: list[str] = []
    for path in paths:
        if not path.startswith("sprakverkstan/") or not path.endswith(".py"):
            continue
        if path.startswith("sprakverkstan/migrations/"):
            continue
        cached = cached_symbols.get(path, {})
        if hashes.get(path) and cached.get("sha256") == hashes[path]:
            symbols = cached.get("symbols", [])
        else:
            symbols = _symbols(path, root)
        symbols_cache[path] = {"sha256": hashes.get(path), "symbols": symbols}
        detail = f" — {', '.join(f'`{name}`' for name in symbols)}" if symbols else ""
        rows.append(f"- `{path}`{detail}")
    backend = "\n".join(rows) or "- No backend Python modules found."

    browser_paths = [
        path for path in paths
        if path.startswith("docs/modules/") and Path(path).suffix.lower() in CODE_SUFFIXES
    ]
    browser = "\n".join(f"- `{path}`" for path in browser_paths) or "- No browser modules found."
    text = MAP.read_text(encoding="utf-8")
    text = re.sub(
        r"(?<=<!-- CONTEXT_MAP:PYTHON -->).*?(?=<!-- /CONTEXT_MAP:PYTHON -->)",
        f"\n{backend}\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"(?<=<!-- CONTEXT_MAP:BROWSER -->).*?(?=<!-- /CONTEXT_MAP:BROWSER -->)",
        f"\n{browser}\n",
        text,
        flags=re.DOTALL,
    )
    return text, symbols_cache


def _current_section_hashes(paths: list[str], hashes: dict[str, str]) -> dict[str, dict[str, str]]:
    mapped = {section: {} for section in SECTIONS}
    for path in paths:
        for section in sections_for_path(path):
            mapped[section][path] = hashes[path]
    return mapped


def _fingerprint(files: dict[str, str]) -> str:
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _changed(old: dict[str, str], new: dict[str, str]) -> list[str]:
    return sorted(path for path in old.keys() | new.keys() if old.get(path) != new.get(path))


def _current_doc_hashes() -> dict[str, str]:
    return {
        path.as_posix(): sha256_file(ROOT / path)
        for path in CONTEXT_DOCS
        if (ROOT / path).is_file()
    }


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", value)
    if not match:
        raise ValueError(f"Invalid semantic version in manifest: {value}")
    return tuple(map(int, match.groups()))


def _bumped(version: str, level: str) -> str:
    major, minor, patch = _version_tuple(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def _append_changelog(version: str, note: str) -> None:
    path = CONTEXT / "CONTEXT_CHANGELOG.md"
    text = path.read_text(encoding="utf-8") if path.exists() else "# Context changelog\n"
    entry = f"- {datetime.now(timezone.utc).date().isoformat()} — {version}: {note}.\n"
    if entry not in text:
        path.write_text(text.rstrip() + "\n" + entry, encoding="utf-8")


def _write_manifest(manifest: dict) -> None:
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _load_manifest() -> dict | None:
    if not MANIFEST.exists():
        return None
    try:
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Cannot read context manifest: {error}") from error
    if payload.get("schema_version") != 3:
        raise RuntimeError("Unsupported context manifest schema; update it manually before continuing.")
    return payload


def _revision() -> str:
    return _git("rev-parse", "HEAD").strip()


def _unmapped(paths: list[str]) -> list[str]:
    return [path for path in paths if not sections_for_path(path)]


def _stale_sections(
    manifest: dict,
    current: dict[str, dict[str, str]],
    generated_map_changed: bool,
) -> dict[str, list[str]]:
    stale = {}
    fingerprints = manifest.get("section_hashes", {})
    source_snapshot = manifest.get("source_hashes", {})
    pending = manifest.get("pending_files", {})
    for section in SECTIONS:
        prior = {
            path: source_snapshot[path]
            for path in source_snapshot
            if section in sections_for_path(path)
        }
        changed = sorted(set(_changed(prior, current[section])) | set(pending.get(section, [])))
        out_of_date = fingerprints.get(section) != _fingerprint(current[section])
        if section == "CODEBASE_MAP":
            out_of_date = generated_map_changed
        if out_of_date:
            stale[section] = changed or ["Generated map differs."]
    return stale


def check() -> int:
    manifest = _load_manifest()
    if manifest is None:
        print("Context manifest is missing; run `python scripts/update_context.py --update`.")
        return 1
    paths = source_paths()
    hashes = source_hashes(paths)
    current_sections = _current_section_hashes(paths, hashes)
    generated_map, _ = render_code_map(
        paths, hashes=hashes, cached_symbols=manifest.get("symbols", {})
    )
    generated_map_changed = generated_map != MAP.read_text(encoding="utf-8")
    stale = _stale_sections(manifest, current_sections, generated_map_changed)
    unmapped = _unmapped(paths)

    if not stale and not unmapped:
        print("Context is current.")
        return 0
    for section, changed in stale.items():
        print(f"Stale {section}: {', '.join(changed)}")
    if unmapped:
        print(f"Unmapped files (classify in update_context.py): {', '.join(unmapped)}")
    print("Refresh generated context with `--update`; review and acknowledge manual sections explicitly.")
    return 1


def update() -> int:
    paths = source_paths()
    hashes = source_hashes(paths)
    unmapped = _unmapped(paths)
    if unmapped:
        print(f"Unmapped files (classify in update_context.py first): {', '.join(unmapped)}")
        return 2

    current_sections = _current_section_hashes(paths, hashes)
    old = _load_manifest()
    generated_map, symbols = render_code_map(
        paths,
        hashes=hashes,
        cached_symbols=old.get("symbols", {}) if old else {},
    )
    map_changed = generated_map != MAP.read_text(encoding="utf-8")
    if map_changed:
        MAP.write_text(generated_map, encoding="utf-8")

    if old is None:
        initial = {
            "schema_version": 3,
            "version": "1.0.0",
            "source_revision": _revision(),
            "source_hashes": hashes,
            "section_hashes": {key: _fingerprint(value) for key, value in current_sections.items()},
            "pending_files": {},
            "symbols": symbols,
            "context_hashes": _current_doc_hashes(),
            "stale_sections": [],
            "complete": True,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _append_changelog("1.0.0", "initial context baseline")
        initial["context_hashes"] = _current_doc_hashes()
        _write_manifest(initial)
        print("Initialized context baseline (v1.0.0).")
        return 0

    stale = _stale_sections(old, current_sections, map_changed)
    stale.pop("CODEBASE_MAP", None)
    section_hashes = dict(old.get("section_hashes", {}))
    pending_files = dict(old.get("pending_files", {}))
    for section, files in current_sections.items():
        if section == "CODEBASE_MAP" or section not in stale:
            section_hashes[section] = _fingerprint(files)
            pending_files.pop(section, None)
        else:
            old_section = {
                path: old.get("source_hashes", {})[path]
                for path in old.get("source_hashes", {})
                if section in sections_for_path(path)
            }
            pending_files[section] = sorted(
                set(pending_files.get(section, [])) | set(_changed(old_section, files))
            )
    current_docs = _current_doc_hashes()
    docs_changed = current_docs != old.get("context_hashes", {})
    added_paths = set(hashes) - set(old.get("source_hashes", {}))
    bump = "minor" if added_paths and docs_changed else "patch"
    version = old["version"]
    if docs_changed:
        version = _bumped(version, bump)
        note = "refreshed generated map and context notes" if map_changed else "updated context notes"
        _append_changelog(version, note)
        current_docs = _current_doc_hashes()

    payload = {
        **old,
        "version": version,
        "source_revision": _revision(),
        "source_hashes": hashes,
        "section_hashes": section_hashes,
        "pending_files": pending_files,
        "symbols": symbols,
        "context_hashes": current_docs,
        "stale_sections": sorted(stale),
        "complete": not stale,
    }
    if docs_changed:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_manifest(payload)
    if stale:
        for section, changed in stale.items():
            print(f"Review required for {section}: {', '.join(changed)}")
    elif not map_changed and not docs_changed and payload == old:
        print("Context unchanged.")
        return 0
    else:
        print(f"Context updated (v{version}); all sections are current.")
    return 0


def acknowledge(sections: list[str], bump: str | None) -> int:
    manifest = _load_manifest()
    if manifest is None:
        print("Context manifest is missing; run `--update` first.")
        return 1
    paths = source_paths()
    unmapped = _unmapped(paths)
    if unmapped:
        print(f"Unmapped files (classify in update_context.py first): {', '.join(unmapped)}")
        return 2

    hashes = source_hashes(paths)
    current_sections = _current_section_hashes(paths, hashes)
    generated_map, symbols = render_code_map(
        paths, hashes=hashes, cached_symbols=manifest.get("symbols", {})
    )
    if generated_map != MAP.read_text(encoding="utf-8"):
        print("Generated code map is stale; run `--update` before acknowledging manual sections.")
        return 1

    unknown = set(sections) - set(SECTIONS) - {"CODEBASE_MAP"}
    if unknown:
        print(f"Unknown section(s): {', '.join(sorted(unknown))}")
        return 2
    selected = set(sections)
    current_stale = _stale_sections(manifest, current_sections, False)
    selected_stale = set(current_stale) & selected
    if "CODEBASE_MAP" in selected:
        print("CODEBASE_MAP is generated; use `--update` to refresh it.")
        return 2
    if not selected_stale:
        print("No selected stale sections; no changes made.")
        return 0

    section_hashes = dict(manifest.get("section_hashes", {}))
    pending_files = dict(manifest.get("pending_files", {}))
    for section in selected_stale:
        section_hashes[section] = _fingerprint(current_sections[section])
        pending_files.pop(section, None)

    docs = _current_doc_hashes()
    docs_changed = docs != manifest.get("context_hashes", {})
    version = manifest["version"]
    if docs_changed:
        version = _bumped(version, bump or "patch")
        _append_changelog(version, f"reviewed {', '.join(sorted(selected_stale))}")
        docs = _current_doc_hashes()
    remaining = _stale_sections(manifest, current_sections, False)
    remaining = {section: changes for section, changes in remaining.items() if section not in selected_stale}
    payload = {
        **manifest,
        "version": version,
        "source_revision": _revision(),
        "source_hashes": hashes,
        "section_hashes": section_hashes,
        "pending_files": pending_files,
        "symbols": symbols,
        "context_hashes": docs,
        "stale_sections": sorted(remaining),
        "complete": not remaining,
    }
    if docs_changed:
        payload["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _write_manifest(payload)
    print(f"Acknowledged {', '.join(sorted(selected_stale))}; context {'is current' if not remaining else 'still has stale sections'}.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="check freshness without writing")
    mode.add_argument("--update", action="store_true", help="refresh generated map and manifest")
    mode.add_argument("--acknowledge", nargs="+", metavar="SECTION", help="mark reviewed manual sections current")
    parser.add_argument("--bump", choices=("patch", "minor", "major"), help="semantic version bump when acknowledging")
    args = parser.parse_args()
    if args.bump and not args.acknowledge:
        parser.error("--bump is only valid with --acknowledge")
    try:
        if args.check:
            return check()
        if args.update:
            return update()
        return acknowledge(args.acknowledge, args.bump)
    except (OSError, subprocess.CalledProcessError, RuntimeError, ValueError) as error:
        print(f"Context update failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
