from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0006_grammar_expansion"


NEW_GROUP = {
    "group": "More sentence building",
    "intro": "Patterns for connecting ideas, asking indirectly, and talking about ownership and actions.",
    "lessons": [
        {
            "title": "Indirect questions",
            "rule": "In an embedded question, keep statement order after the question word: Jag vet inte var hon bor. Yes/no embedded questions use om: Jag undrar om han kommer.",
            "why": "An indirect question is part of a larger sentence, so the embedded clause does not use the verb-subject inversion of a direct question.",
            "commonMistakes": [
                "Using direct-question order inside the clause: Jag vet inte var bor hon.",
                "Forgetting om in an embedded yes/no question.",
            ],
            "examples": [
                {"sv": "Kan du säga var stationen ligger?", "en": "Can you say where the station is?"},
                {"sv": "Jag vet inte om bussen går nu.", "en": "I do not know whether the bus is running now."},
            ],
            "exceptions": ["A direct question keeps inversion: Var ligger stationen? An embedded question does not: Jag frågar var stationen ligger."],
            "exercise": {
                "prompt": "Choose the correct embedded question.",
                "options": ["Jag vet var hon bor.", "Jag vet var bor hon.", "Jag vet hon var bor.", "Jag vet var hon bo."],
                "answer": "Jag vet var hon bor.",
                "explanation": "The embedded clause uses subject before finite verb: hon bor.",
            },
        },
        {
            "title": "Reflexive possessives: sin, sitt, sina",
            "rule": "Use sin, sitt, or sina when the possessor is the subject of the same clause. Match the form to the owned noun: sin bil, sitt hus, sina nycklar.",
            "why": "The reflexive possessive points back to the clause subject and distinguishes that owner's item from another person's item.",
            "commonMistakes": [
                "Using sin for a plural owned noun instead of sina.",
                "Using sin when the owner is not the clause subject; use hans, hennes, deras, or another possessive instead.",
            ],
            "examples": [
                {"sv": "Erik tar sin jacka.", "en": "Erik takes his own jacket."},
                {"sv": "Erik tar hans jacka.", "en": "Erik takes another man's jacket."},
            ],
            "exceptions": ["Sin, sitt, and sina are not used as subjects. Use the ordinary possessive form in phrases such as hans bil."],
            "exercise": {
                "prompt": "Anna hämtar ___ barn. Choose the form that refers to Anna's own children.",
                "options": ["sina", "sin", "sitt", "hennes"],
                "answer": "sina",
                "explanation": "Barn is plural here, so use sina for the subject's own children.",
            },
        },
        {
            "title": "Infinitives with att",
            "rule": "Many verbs take att before a following infinitive: Jag hoppas att kunna komma. Modal verbs take the infinitive without att: Jag kan komma.",
            "why": "The verb before the infinitive determines whether att is needed. Learning common verb patterns helps avoid adding or omitting it by guesswork.",
            "commonMistakes": [
                "Adding att after a modal verb: Jag kan att komma.",
                "Leaving out att after verbs that normally require it: Jag hoppas kunna komma.",
            ],
            "examples": [
                {"sv": "Hon försöker att läsa varje dag.", "en": "She tries to read every day."},
                {"sv": "Hon vill läsa varje dag.", "en": "She wants to read every day."},
            ],
            "exceptions": ["Some verbs allow variation in everyday Swedish, including börja (att) läsa. Learn the pattern with the verb."],
            "exercise": {
                "prompt": "Complete the sentence: Vi hoppas ___ träffa dig snart.",
                "options": ["att", "om", "för", "till"],
                "answer": "att",
                "explanation": "Hoppas is followed by att plus the infinitive in this pattern.",
            },
        },
        {
            "title": "Coordinating conjunctions",
            "rule": "Och, men, eller, and för can connect two main clauses. Each clause keeps main-clause word order, including V2: Jag är trött, men jag arbetar.",
            "why": "A coordinating conjunction joins ideas of equal grammatical status. The clause after it remains a main clause rather than switching to subordinate order.",
            "commonMistakes": [
                "Moving inte before the finite verb in the second main clause.",
                "Treating men like eftersom and applying subordinate-clause word order.",
            ],
            "examples": [
                {"sv": "Hon ringer, och jag svarar.", "en": "She calls, and I answer."},
                {"sv": "Vi går nu, för bussen kommer snart.", "en": "We are leaving now, because the bus is coming soon."},
            ],
            "exceptions": ["Conjunction choice affects meaning: men contrasts, eller offers a choice, and för introduces an explanation."],
            "exercise": {
                "prompt": "Which sentence keeps normal main-clause order after men?",
                "options": ["Jag vill följa med, men jag kan inte.", "Jag vill följa med, men kan jag inte.", "Jag vill följa med, men inte jag kan.", "Jag vill följa med, men jag inte kan."],
                "answer": "Jag vill följa med, men jag kan inte.",
                "explanation": "The second coordinated clause keeps subject-verb order, with inte after the finite verb.",
            },
        },
        {
            "title": "S-passive and bli-passive",
            "rule": "The s-passive often describes a general process or formal action: Dörren öppnas klockan åtta. Bli plus supine often presents a particular event or change: Mötet blev inställt.",
            "why": "Both forms can make the action more important than the person doing it. The choice often depends on whether you describe a process/state or a particular event.",
            "commonMistakes": [
                "Treating the two passive forms as interchangeable in every context.",
                "Forgetting the supine after bli in a completed-event passive.",
            ],
            "examples": [
                {"sv": "Biljetter säljs på nätet.", "en": "Tickets are sold online."},
                {"sv": "Matchen blev avbruten av regnet.", "en": "The match was interrupted by the rain."},
            ],
            "exceptions": ["Usage varies with verb and context. The active form is often clearer when the person doing the action matters."],
            "exercise": {
                "prompt": "Choose the natural s-passive for a routine: Butiken ___ klockan nio.",
                "options": ["öppnas", "blir öppnade", "öppnar sig", "öppnade blir"],
                "answer": "öppnas",
                "explanation": "The s-passive is a natural way to describe a regular opening time.",
            },
        },
    ],
}


def upgrade(app):
    with app.app_context():
        db.create_all()
        if db.session.get(SchemaMigration, REVISION):
            return {"revision": REVISION, "imported": 0, "already_applied": True}

        content = db.session.get(LearningContent, "grammar")
        if content is None:
            raise RuntimeError("Apply the learning-content migration before grammar expansion.")

        groups = list(content.data)
        if not any(group.get("group") == NEW_GROUP["group"] for group in groups):
            groups.append(NEW_GROUP)
            content.data = groups

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(NEW_GROUP["lessons"]), "already_applied": False}