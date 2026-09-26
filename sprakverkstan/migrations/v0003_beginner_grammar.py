from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0003_beginner_grammar"


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        manifest = db.session.get(LearningContent, "manifest")
        grammar = db.session.get(LearningContent, "grammar")
        if manifest is None or grammar is None:
            raise RuntimeError("Apply the learning-content migration before beginner grammar migration.")

        beginner_group = {
            "group": "Core foundations",
            "intro": "The patterns every beginner needs first.",
            "lessons": [{
                "title": note["title"],
                "rule": note["body"],
                "why": "Learn the complete Swedish pattern instead of translating one word at a time.",
                "examples": [],
                "commonMistakes": [],
                "exceptions": [],
            } for note in manifest.data.get("notes", [])],
        }
        groups = grammar.data
        if not groups or groups[0].get("group") != beginner_group["group"]:
            grammar.data = [beginner_group, *groups]

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(beginner_group["lessons"]), "already_applied": False}