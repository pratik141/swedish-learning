import json
import unicodedata

from sqlalchemy import func, select

from ..extensions import db
from ..models import SchemaMigration, VocabularyWord


REVISION = "0001_vocabulary"


def _search_text(item):
    parts = []

    def collect(value):
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(item)
    normalized = unicodedata.normalize("NFKD", " ".join(parts).casefold())
    normalized_text = " ".join("".join(char for char in normalized if not unicodedata.combining(char)).split())
    return f" {normalized_text} "


def upgrade(app):
    """Create the app schema and import the initial vocabulary corpus once."""
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        data_directory = app.config["SITE_DIRECTORY"] / "data"
        with (data_directory / "manifest.json").open(encoding="utf-8") as source:
            manifest = json.load(source)
        quick_ids = set(manifest["quickIds"])
        rows = []

        for chapter in manifest["chapters"]:
            chunk_path = data_directory / "chunks" / f"{chapter['slug']}.json"
            with chunk_path.open(encoding="utf-8") as source:
                chunk = json.load(source)
            if chunk["chapter"]["slug"] != chapter["slug"]:
                raise ValueError(f"Vocabulary chunk slug mismatch: {chunk_path.name}")
            if len(chunk["items"]) != chapter["count"]:
                raise ValueError(f"Vocabulary count mismatch: {chunk_path.name}")

            for item in chunk["items"]:
                rows.append({
                    "id": item["id"],
                    "category_slug": item["categorySlug"],
                    "level": item["level"],
                    "kind": item["kind"],
                    "is_quick_reference": item["id"] in quick_ids,
                    "data": item,
                    "search_text": _search_text(item),
                })

        if len(rows) != manifest["meta"]["total"]:
            raise ValueError("Manifest total does not match vocabulary chunk contents.")
        if len({row["id"] for row in rows}) != len(rows):
            raise ValueError("Vocabulary chunks contain duplicate word IDs.")

        existing_count = db.session.scalar(select(func.count()).select_from(VocabularyWord))
        if existing_count:
            raise RuntimeError(
                "Vocabulary table contains data but migration history is missing; "
                "refusing to overwrite it."
            )

        for offset in range(0, len(rows), 100):
            db.session.execute(db.insert(VocabularyWord), rows[offset:offset + 100])

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(rows), "already_applied": False}