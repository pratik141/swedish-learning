import json

from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0002_learning_content"


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        data_directory = app.config["SITE_DIRECTORY"] / "data"
        documents = {}
        for key, filename in (
            ("manifest", "manifest.json"),
            ("grammar", "grammar.json"),
            ("situations", "situations.json"),
        ):
            with (data_directory / filename).open(encoding="utf-8") as source:
                documents[key] = json.load(source)

        db.session.add_all(
            LearningContent(key=key, data=data)
            for key, data in documents.items()
        )
        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(documents), "already_applied": False}