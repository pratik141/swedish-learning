import hashlib
import json
import unicodedata
import urllib.parse
import urllib.request

from sqlalchemy import select

from sprakverkstan import create_app
from sprakverkstan.extensions import db
from sprakverkstan.migrations import upgrade_all
from sprakverkstan.models import ExternalVocabularyWord, VocabularyWord


SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
LICENSE = "CC0-1.0"
QUERY = """
SELECT DISTINCT ?lexeme ?lemma ?gloss WHERE {
  ?lexeme dct:language wd:Q9027;
          wikibase:lemma ?lemma;
          ontolex:sense ?sense.
  ?sense skos:definition ?gloss.
  FILTER(LANG(?gloss) = "en")
  FILTER(REGEX(STR(?lemma), "^[A-Za-zÅÄÖåäö][A-Za-zÅÄÖåäö'-]{1,39}$"))
  FILTER(STRLEN(STR(?gloss)) <= 100)
}
ORDER BY LCASE(STR(?lemma))
LIMIT 2500
"""


def fetch_lexemes():
    url = f"{SPARQL_ENDPOINT}?{urllib.parse.urlencode({'query': QUERY, 'format': 'json'})}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": "SprakverkstanVocabularyImporter/1.0 (open CC0 lexical data)",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return payload["results"]["bindings"]


app = create_app({"AUTO_CREATE_TABLES": False})
upgrade_all(app)
bindings = fetch_lexemes()
with app.app_context():
    existing_words = db.session.execute(select(VocabularyWord.data["sv"])).scalars().all()
    existing_words.extend(db.session.execute(select(ExternalVocabularyWord.data["sv"])).scalars().all())
    seen_lemmas = {word.casefold() for word in existing_words if word}
    existing_keys = set(db.session.execute(select(ExternalVocabularyWord.source_key)).scalars())
    next_id = max(
        db.session.scalar(select(db.func.max(VocabularyWord.id))) or 0,
        db.session.scalar(select(db.func.max(ExternalVocabularyWord.id))) or 1000000,
    ) + 1

    additions = []
    for binding in bindings:
        lemma = binding["lemma"]["value"].strip()
        gloss = binding["gloss"]["value"].strip()
        lexeme_uri = binding["lexeme"]["value"]
        source_key = f"{lexeme_uri}|{gloss.casefold()}"
        if not lemma or not gloss or lemma.casefold() in seen_lemmas or source_key in existing_keys:
            continue

        source_digest = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:16]
        item = {
            "id": next_id,
            "kind": "word",
            "sv": lemma,
            "plural": "",
            "en": gloss,
            "hi": "",
            "pron": "",
            "category": "🌐 Open vocabulary",
            "categoryLabel": "🌐 Open vocabulary",
            "categorySlug": "open-vocabulary",
            "level": "B1",
            "forms": "",
            "source": {
                "name": "Wikidata Lexemes",
                "uri": lexeme_uri,
                "license": LICENSE,
            },
        }
        additions.append(ExternalVocabularyWord(
            id=next_id,
            source_key=source_digest,
            source_uri=lexeme_uri,
            data=item,
            search_text=" " + " ".join(
                "".join(
                    char for char in unicodedata.normalize("NFKD", " ".join((lemma, gloss)).casefold())
                    if not unicodedata.combining(char)
                ).split()
            ) + " ",
        ))
        seen_lemmas.add(lemma.casefold())
        existing_keys.add(source_key)
        next_id += 1

    db.session.add_all(additions)
    db.session.commit()
    print(f"Wikidata CC0 lexemes fetched: {len(bindings)}")
    print(f"New Swedish entries imported: {len(additions)}")
    print(f"Already-known lemmas skipped: {len(bindings) - len(additions)}")