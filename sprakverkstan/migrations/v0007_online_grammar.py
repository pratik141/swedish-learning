from ..extensions import db
from ..models import LearningContent, SchemaMigration


REVISION = "0007_online_grammar"


NEW_GROUP = {
    "group": "More Swedish patterns",
    "intro": "Useful extensions for describing, comparing, and connecting everyday ideas.",
    "lessons": [
        {
            "title": "Adjectives used as adverbs",
            "rule": "When an adjective describes how an action is done, the neuter form is commonly used: snabb bil, ett snabbt tåg, tåget går snabbt.",
            "why": "The same adjective may describe a noun or explain the manner of an action. The neuter ending often marks the adverb use.",
            "commonMistakes": [
                "Using the common-gender adjective after a verb: tåget går snabb.",
                "Changing an adverb to agree with the subject instead of using its adverb form.",
            ],
            "examples": [
                {"sv": "Hon sjunger vackert.", "en": "She sings beautifully."},
                {"sv": "Barnet springer fort.", "en": "The child runs fast."},
            ],
            "exceptions": ["Some adverbs have their own forms or do not use -t. Learn frequent adjective-adverb pairs as vocabulary."],
            "exercise": {
                "prompt": "Complete the sentence: Bilen kör ___ på den våta vägen.",
                "options": ["långsamt", "långsam", "långsamma", "långsammare"],
                "answer": "långsamt",
                "explanation": "The word describes how the car is driven, so use the adverb form långsamt.",
            },
            "source": {
                "title": "Swedish grammar: Adverbs",
                "url": "https://en.wikipedia.org/wiki/Swedish_grammar#Adverbs",
                "license": "CC BY-SA 4.0",
            },
        },
        {
            "title": "Supine and past participle",
            "rule": "Use the supine after har or hade: Hon har skrivit ett brev. Use a past participle as an adjective or with a passive construction: brevet är skrivet.",
            "why": "English often uses one past-participle form for both jobs, but Swedish distinguishes the supine used with ha from participles that describe a noun or result.",
            "commonMistakes": [
                "Using the participle after har when the verb has a different supine: har skrivit, not har skriven.",
                "Assuming every verb makes its supine by adding the same ending.",
            ],
            "examples": [
                {"sv": "De har öppnat fönstret.", "en": "They have opened the window."},
                {"sv": "Fönstret är öppet.", "en": "The window is open."},
            ],
            "exceptions": ["For many regular verbs, supine and neuter participle look alike; strong verbs often make the difference clearer, such as skrivit versus skrivet."],
            "exercise": {
                "prompt": "Choose the correct form: Vi har ___ maten.",
                "options": ["ätit", "äten", "ätet", "ätna"],
                "answer": "ätit",
                "explanation": "After har, use the supine form ätit.",
            },
            "source": {
                "title": "Swedish grammar: Supine form",
                "url": "https://en.wikipedia.org/wiki/Swedish_grammar#Supine_form",
                "license": "CC BY-SA 4.0",
            },
        },
        {
            "title": "Definite nouns with adjectives",
            "rule": "A definite noun phrase with an adjective normally uses a front article and a definite noun ending: den röda bilen, det stora huset, de nya skorna.",
            "why": "Swedish marks definiteness both before the adjective and on the noun in this common pattern. The article and adjective agree with the noun phrase.",
            "commonMistakes": [
                "Leaving off the front article: röda bilen.",
                "Using the wrong front article for an ett-word or plural noun.",
            ],
            "examples": [
                {"sv": "Den lilla butiken är öppen.", "en": "The small shop is open."},
                {"sv": "Det gamla huset ligger nära stationen.", "en": "The old house is near the station."},
            ],
            "exceptions": ["Possessives usually use adjective -a without the extra definite article: min röda bil, mitt stora hus."],
            "exercise": {
                "prompt": "Choose the standard definite phrase for 'the new letter' (ett brev).",
                "options": ["det nya brevet", "den nya brevet", "ett nya brev", "de nya brevet"],
                "answer": "det nya brevet",
                "explanation": "Use det for an ett-word, adjective -a, and the definite noun form brevet.",
            },
            "source": {
                "title": "Swedish grammar: Articles and definite forms",
                "url": "https://en.wikipedia.org/wiki/Swedish_grammar#Articles_and_definite_forms",
                "license": "CC BY-SA 4.0",
            },
        },
        {
            "title": "Motion and location adverbs",
            "rule": "Some Swedish adverbs distinguish movement toward a place from being at that place: gå hem means 'go home', while vara hemma means 'be at home'.",
            "why": "The choice can encode direction or location directly, where English often uses the same word for both meanings.",
            "commonMistakes": [
                "Using hemma for an intended destination after a motion verb when hem is needed.",
                "Using a directional form when describing a fixed location.",
            ],
            "examples": [
                {"sv": "Efter jobbet går jag hem.", "en": "After work I go home."},
                {"sv": "På kvällen är jag hemma.", "en": "In the evening I am at home."},
                {"sv": "Vi går ut nu, men vi är ute redan.", "en": "We are going out now, but we are already outside."},
            ],
            "exceptions": ["The pairs are lexical and not all adverbs form a perfectly regular set. Common pairs include hem/hemma, ut/ute, and in/inne."],
            "exercise": {
                "prompt": "Complete the location sentence: Efter resan är de ___.",
                "options": ["hemma", "hem", "hemåt", "hemland"],
                "answer": "hemma",
                "explanation": "The sentence describes where they are, so use the location form hemma.",
            },
            "source": {
                "title": "Swedish grammar: Directional adverbs",
                "url": "https://en.wikipedia.org/wiki/Swedish_grammar#Directional_adverbs",
                "license": "CC BY-SA 4.0",
            },
        },
        {
            "title": "Irregular adjective comparisons",
            "rule": "Many adjectives use -are and -ast, but common adjectives can be irregular: bra, bättre, bäst; dålig, sämre, sämst; liten, mindre, minst.",
            "why": "Comparatives and superlatives let you compare things, but the most frequent comparison words do not always follow the regular ending pattern.",
            "commonMistakes": [
                "Adding regular endings to an irregular adjective, such as braare.",
                "Forgetting the -e form often used in a definite superlative phrase: den bästa dagen.",
            ],
            "examples": [
                {"sv": "Den här vägen är bättre.", "en": "This route is better."},
                {"sv": "Det var den bästa dagen.", "en": "It was the best day."},
            ],
            "exceptions": ["Some adjectives allow more than one comparison pattern or have meaning-dependent forms. Check a dictionary when unsure."],
            "exercise": {
                "prompt": "Choose the correct comparative: Den här lösningen är ___ än den förra.",
                "options": ["bättre", "bäst", "braare", "godast"],
                "answer": "bättre",
                "explanation": "Bättre is the comparative form of bra.",
            },
            "source": {
                "title": "Swedish grammar: Comparatives and superlatives",
                "url": "https://en.wikipedia.org/wiki/Swedish_grammar#Comparatives_and_superlatives",
                "license": "CC BY-SA 4.0",
            },
        },
        {
            "title": "Paired conjunctions",
            "rule": "Some conjunctions work as pairs: både ... och (both ... and), antingen ... eller (either ... or), and varken ... eller (neither ... nor).",
            "why": "The first part signals how the listener should interpret the second part, so using both pieces makes alternatives and combinations clear.",
            "commonMistakes": [
                "Using och instead of eller in the second half of an either-or choice.",
                "Forgetting that varken already makes the phrase negative; do not add inte to the same clause in standard usage.",
            ],
            "examples": [
                {"sv": "Hon talar både svenska och engelska.", "en": "She speaks both Swedish and English."},
                {"sv": "Vi kan antingen gå eller ta bussen.", "en": "We can either walk or take the bus."},
                {"sv": "Han dricker varken kaffe eller te.", "en": "He drinks neither coffee nor tea."},
            ],
            "exceptions": ["The paired words connect matching kinds of elements or clauses; keep the structures parallel when possible."],
            "exercise": {
                "prompt": "Complete the either-or pair: Vi kan ___ stanna hemma ___ gå ut.",
                "options": ["antingen ... eller", "både ... eller", "varken ... och", "inte ... men"],
                "answer": "antingen ... eller",
                "explanation": "Antingen ... eller introduces two alternatives.",
            },
            "source": {
                "title": "Swedish Grammar: Conjunctions",
                "url": "https://www.swedishgrammar.com/conjunctions.html",
                "license": "Original explanation and examples; source consulted",
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
            raise RuntimeError("Apply the learning-content migration before online grammar migration.")

        groups = list(content.data)
        if not any(group.get("group") == NEW_GROUP["group"] for group in groups):
            groups.append(NEW_GROUP)
            content.data = groups

        db.session.add(SchemaMigration(revision=REVISION))
        db.session.commit()
        return {"revision": REVISION, "imported": len(NEW_GROUP["lessons"]), "already_applied": False}