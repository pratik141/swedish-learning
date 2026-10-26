import json
from copy import deepcopy

from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0010_situations_expansion"


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        content = db.session.get(LearningContent, "situations")
        if content is None:
            raise RuntimeError("Apply the learning-content migration before the situations expansion.")

        source_path = app.config["SITE_DIRECTORY"] / "data" / "situations.json"
        with source_path.open(encoding="utf-8") as source:
            seed_situations = json.load(source)

        scenarios = deepcopy(content.data)
        existing_ids = {scenario["id"] for scenario in scenarios}
        additions = [
            scenario for scenario in seed_situations
            if scenario["id"] not in existing_ids
        ]
        scenarios.extend(additions)
        content.data = scenarios

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(additions), "already_applied": False}
