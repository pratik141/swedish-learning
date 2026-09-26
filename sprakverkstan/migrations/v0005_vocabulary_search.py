import unicodedata

from sqlalchemy import inspect, select, text

from ..extensions import db
from ..models import ExternalVocabularyWord, SchemaMigration, VocabularyWord


REVISION = "0005_vocabulary_search"


def _flatten_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from _flatten_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _flatten_strings(child)


def normalize_search_text(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    normalized_text = " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())
    return f" {normalized_text} "


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        inspector = inspect(db.engine)
        for table_name in ("vocabulary_words", "external_vocabulary_words"):
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "search_text" not in columns:
                db.session.execute(text(
                    f"ALTER TABLE {table_name} ADD COLUMN search_text TEXT NOT NULL DEFAULT ''"
                ))
        db.session.commit()

        updated = 0
        for model in (VocabularyWord, ExternalVocabularyWord):
            records = db.session.execute(select(model)).scalars().all()
            for record in records:
                record.search_text = normalize_search_text(" ".join(_flatten_strings(record.data)))
                updated += 1

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": updated, "already_applied": False}