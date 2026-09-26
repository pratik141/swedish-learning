from copy import deepcopy

from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0008_supine_example"


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        content = db.session.get(LearningContent, "grammar")
        if content is None:
            raise RuntimeError("Apply the learning-content migration before grammar example correction.")

        groups = deepcopy(content.data)
        lesson = next(
            lesson
            for group in groups
            for lesson in group["lessons"]
            if lesson["title"] == "Supine and past participle"
        )
        lesson["examples"][1] = {
            "sv": "Brevet är skrivet på svenska.",
            "en": "The letter is written in Swedish.",
        }
        content.data = groups

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": 1, "already_applied": False}