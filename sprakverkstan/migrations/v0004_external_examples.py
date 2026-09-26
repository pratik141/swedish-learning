from sqlalchemy import select

from ..extensions import db
from ..models import ExternalVocabularyWord, SchemaMigration


REVISION = "0004_external_examples"


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        rows = db.session.execute(select(ExternalVocabularyWord)).scalars().all()
        updated = 0
        for row in rows:
            if "example" in row.data:
                payload = dict(row.data)
                payload.pop("example", None)
                row.data = payload
                updated += 1

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": updated, "already_applied": False}