import json
import urllib.error
import urllib.parse
import urllib.request


SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
USER_AGENT = "SprakverkstanVocabularySearch/1.0 (open CC0 lexical data)"


class WikidataLookupError(Exception):
    pass


def search_wikidata_lexemes(search):
    query = f"""
SELECT DISTINCT ?lexeme ?lemma ?gloss WHERE {{
  ?lexeme dct:language wd:Q9027;
          wikibase:lemma ?lemma;
          ontolex:sense ?sense.
  ?sense skos:definition ?gloss.
  FILTER(LANG(?gloss) = "en")
  FILTER(STRLEN(STR(?lemma)) <= 40)
  FILTER(STRLEN(STR(?gloss)) <= 100)
  BIND(LCASE({json.dumps(search)}) AS ?needle)
  FILTER(CONTAINS(LCASE(STR(?lemma)), ?needle) || CONTAINS(LCASE(STR(?gloss)), ?needle))
}}
ORDER BY LCASE(STR(?lemma))
LIMIT 10
"""
    url = f"{SPARQL_ENDPOINT}?{urllib.parse.urlencode({'query': query, 'format': 'json'})}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/sparql-results+json",
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.load(response)
        bindings = payload["results"]["bindings"]
        if not isinstance(bindings, list):
            raise TypeError("Wikidata bindings must be a list.")
        results = []
        for binding in bindings:
            lexeme_uri = binding["lexeme"]["value"]
            lemma = binding["lemma"]["value"]
            gloss = binding["gloss"]["value"]
            if not all(isinstance(value, str) for value in (lexeme_uri, lemma, gloss)):
                raise TypeError("Wikidata lexical fields must be strings.")
            lemma = lemma.strip()
            gloss = gloss.strip()
            if lemma and gloss:
                results.append({"lexeme_uri": lexeme_uri, "lemma": lemma, "gloss": gloss})
        return results
    except (
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        UnicodeError,
        AttributeError,
    ) as error:
        raise WikidataLookupError("Could not retrieve vocabulary from Wikidata.") from error
