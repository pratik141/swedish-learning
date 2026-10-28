import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sprakverkstan import create_app
from sprakverkstan.extensions import db
from sprakverkstan.migrations import upgrade_all
from sprakverkstan.migrations.v0010_situations_expansion import (
    REVISION as SITUATIONS_EXPANSION_REVISION,
    upgrade as upgrade_situations_expansion,
)
from sprakverkstan.models import (
    ExternalVocabularyWord,
    LearningContent,
    SchemaMigration,
    VocabularyWord,
)
from sprakverkstan.vocabulary_lookup import WikidataLookupError, search_wikidata_lexemes


class VocabularyApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "AUTO_CREATE_TABLES": False,
        })
        self.migration_results = upgrade_all(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_directory.cleanup()

    def register_user(self):
        response = self.client.post("/api/register", json={
            "name": "Test learner",
            "email": "learner@example.com",
            "password": "secure-pass-123",
        })
        self.assertEqual(response.status_code, 201)

    def test_initial_migration_imports_complete_dataset_once(self):
        self.assertEqual(self.migration_results[0]["imported"], 760)
        self.assertFalse(self.migration_results[0]["already_applied"])
        self.assertEqual(self.migration_results[1]["imported"], 3)
        self.assertGreater(self.migration_results[2]["imported"], 0)
        self.assertEqual(self.migration_results[3]["imported"], 0)
        self.assertEqual(self.migration_results[4]["imported"], 760)
        self.assertEqual(self.migration_results[5]["imported"], 5)
        self.assertEqual(self.migration_results[6]["imported"], 6)
        self.assertEqual(self.migration_results[7]["imported"], 1)
        self.assertEqual(self.migration_results[8]["imported"], 1)
        self.assertEqual(self.migration_results[9]["imported"], 0)
        repeat_results = upgrade_all(self.app)
        self.assertTrue(all(result["already_applied"] for result in repeat_results))
        with self.app.app_context():
            self.assertEqual(db.session.query(VocabularyWord).count(), 760)
            self.assertEqual(db.session.query(LearningContent).count(), 3)

    def test_api_serves_only_requested_vocabulary(self):
        self.register_user()
        category = self.client.get("/api/vocabulary?category=01-fruits")
        self.assertEqual(category.status_code, 200)
        self.assertEqual(category.json["count"], 20)
        self.assertTrue(all(item["categorySlug"] == "01-fruits" for item in category.json["items"]))

        quick = self.client.get("/api/vocabulary?set=quick")
        self.assertEqual(quick.json["count"], 500)
        self.assertEqual(len(quick.json["items"]), 50)
        self.assertTrue(quick.json["hasMore"])
        second_page = self.client.get("/api/vocabulary?set=quick&offset=50&limit=50")
        self.assertEqual(second_page.json["items"][0]["id"], quick.json["items"][-1]["id"] + 1)

        search = self.client.get("/api/vocabulary?category=01-fruits&q=banana")
        self.assertEqual(search.json["count"], 1)
        self.assertEqual(search.json["items"][0]["sv"], "en banan")

        example_search = self.client.get("/api/vocabulary?category=01-fruits&q=I%20have%20an%20apple")
        self.assertEqual(example_search.json["count"], 1)
        self.assertEqual(example_search.json["items"][0]["id"], 1)

        decomposed_diacritic = self.client.get("/api/vocabulary?category=01-fruits&q=ett%20a%CC%88pple")
        self.assertTrue(any(item["id"] == 1 for item in decomposed_diacritic.json["items"]))

        selected_ids = [category.json["items"][0]["id"], category.json["items"][-1]["id"]]
        selected = self.client.get(f"/api/vocabulary?ids={selected_ids[0]},{selected_ids[1]}")
        self.assertEqual(selected.json["count"], 2)
        self.assertEqual([item["id"] for item in selected.json["items"]], selected_ids)

    def test_api_requires_explicit_selector(self):
        self.assertEqual(self.client.get("/api/vocabulary").status_code, 400)
        self.assertEqual(self.client.get("/api/vocabulary?category=../../users").status_code, 400)

    def test_learning_documents_come_from_database(self):
        self.register_user()
        manifest = self.client.get("/api/manifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertNotIn("notes", manifest.json)
        self.assertEqual(manifest.json["meta"]["total"], 760)

        grammar = self.client.get("/api/grammar")
        self.assertEqual(grammar.status_code, 200)
        self.assertEqual(grammar.json[0]["group"], "Core foundations")
        self.assertGreater(len(grammar.json), 1)
        expanded = next(group for group in grammar.json if group["group"] == "More sentence building")
        self.assertEqual(len(expanded["lessons"]), 5)
        researched = next(group for group in grammar.json if group["group"] == "More Swedish patterns")
        self.assertEqual(len(researched["lessons"]), 6)
        self.assertTrue(all(lesson.get("source", {}).get("url") for lesson in researched["lessons"]))
        supine = next(lesson for lesson in researched["lessons"] if lesson["title"] == "Supine and past participle")
        self.assertEqual(supine["examples"][1]["sv"], "Brevet är skrivet på svenska.")

        situations = self.client.get("/api/situations")
        self.assertEqual(situations.status_code, 200)
        self.assertEqual(len(situations.json), 15)
        self.assertEqual(
            {scenario["id"] for scenario in situations.json[-5:]},
            {"restaurant", "pharmacy", "hotel", "library", "hairdresser"},
        )
        for scenario in situations.json:
            self.assertIn(scenario["answer"], scenario["options"])
            self.assertTrue(all(line["sv"] and line["en"] and line["hi"] for line in scenario["dialogue"]))
        self.assertEqual(self.client.get("/data/manifest.json").status_code, 404)
        self.assertEqual(self.client.get("/data/grammar.json").status_code, 404)

    def test_situations_expansion_migration_adds_missing_scenarios_once(self):
        self.register_user()
        with self.app.app_context():
            content = db.session.get(LearningContent, "situations")
            content.data = content.data[:10]
            db.session.delete(db.session.get(SchemaMigration, SITUATIONS_EXPANSION_REVISION))
            db.session.commit()

        result = upgrade_situations_expansion(self.app)
        self.assertEqual(result["imported"], 5)
        self.assertFalse(result["already_applied"])
        self.assertEqual(len(self.client.get("/api/situations").json), 15)

        repeated = upgrade_situations_expansion(self.app)
        self.assertEqual(repeated["imported"], 0)
        self.assertTrue(repeated["already_applied"])

    def test_external_open_licensed_words_are_separate_and_attributed(self):
        self.register_user()
        item = {
            "id": 1000001,
            "sv": "provord",
            "en": "test word",
            "hi": "",
            "categorySlug": "open-vocabulary",
        }
        with self.app.app_context():
            db.session.add(ExternalVocabularyWord(
                id=1000001,
                source_key="test-source-key",
                source_uri="https://www.wikidata.org/entity/L123456",
                data={**item, "source": {"name": "Wikidata Lexemes", "uri": "https://www.wikidata.org/entity/L123456", "license": "CC0-1.0"}},
            ))
            db.session.commit()

        manifest = self.client.get("/api/manifest").json
        self.assertEqual(manifest["chapters"][-1]["slug"], "open-vocabulary")
        self.assertEqual(manifest["meta"]["total"], 761)
        external = self.client.get("/api/vocabulary?category=open-vocabulary")
        self.assertEqual(external.json["items"][0]["source"]["license"], "CC0-1.0")
        self.assertEqual(external.json["items"][0]["sv"], "provord")
        self.assertNotIn("example", external.json["items"][0])

    def test_guest_access_is_limited_to_free_vocabulary_and_grammar(self):
        manifest = self.client.get("/api/manifest")
        self.assertEqual(manifest.json["meta"]["total"], 20)
        self.assertEqual(len(manifest.json["chapters"]), 1)
        self.assertEqual(manifest.json["chapters"][0]["slug"], "20-essential-everyday-expressions")
        self.assertEqual(manifest.headers["Cache-Control"], "private, no-store")

        free_words = self.client.get("/api/vocabulary?all=true&limit=100")
        self.assertEqual(free_words.status_code, 200)
        self.assertEqual(free_words.json["count"], 20)
        self.assertEqual({word["id"] for word in free_words.json["items"]}, set(range(610, 630)))

        restricted_category = self.client.get("/api/vocabulary?category=01-fruits&limit=100")
        self.assertEqual(restricted_category.json["count"], 0)
        restricted_ids = self.client.get("/api/vocabulary?ids=1,610,611,999")
        self.assertEqual([word["id"] for word in restricted_ids.json["items"]], [610, 611])

        with patch("sprakverkstan.routes.api.search_wikidata_lexemes") as lookup:
            online_search = self.client.get("/api/vocabulary?category=20-essential-everyday-expressions&q=unlisted")
        self.assertEqual(online_search.json["count"], 0)
        lookup.assert_not_called()

        grammar = self.client.get("/api/grammar")
        free_lessons = [
            lesson
            for group in grammar.json
            for lesson in group["lessons"]
        ]
        self.assertEqual(
            {lesson["title"] for lesson in free_lessons},
            {"En and ett gender", "Present tense", "V2 main-clause order"},
        )
        self.assertEqual(self.client.get("/api/situations").status_code, 401)

    def test_signed_in_user_gets_full_learning_library(self):
        self.register_user()
        manifest = self.client.get("/api/manifest")
        self.assertEqual(manifest.json["meta"]["total"], 760)
        self.assertGreater(len(manifest.json["chapters"]), 1)

        all_words = self.client.get("/api/vocabulary?all=true&limit=100")
        self.assertEqual(all_words.json["count"], 760)
        self.assertEqual(len(all_words.json["items"]), 100)

        grammar = self.client.get("/api/grammar")
        lesson_count = sum(len(group["lessons"]) for group in grammar.json)
        self.assertGreater(lesson_count, 3)
        self.assertEqual(self.client.get("/api/situations").status_code, 200)

    def test_missing_search_word_is_fetched_from_wikidata_and_saved(self):
        self.register_user()
        lexemes = [{
            "lexeme_uri": "https://www.wikidata.org/entity/L123456",
            "lemma": "sällsynt",
            "gloss": "rare",
        }]
        with patch("sprakverkstan.routes.api.search_wikidata_lexemes", return_value=lexemes) as lookup:
            response = self.client.get("/api/vocabulary?category=01-fruits&q=rare")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["count"], 1)
        item = response.json["items"][0]
        self.assertEqual(item["sv"], "sällsynt")
        self.assertEqual(item["source"]["license"], "CC0-1.0")
        lookup.assert_called_once_with("rare")

        with self.app.app_context():
            saved = db.session.get(ExternalVocabularyWord, item["id"])
            self.assertIsNotNone(saved)
            self.assertEqual(saved.data["source"]["uri"], lexemes[0]["lexeme_uri"])
            self.assertIn(" rare ", saved.search_text)

        with patch("sprakverkstan.routes.api.search_wikidata_lexemes") as lookup:
            repeated = self.client.get("/api/vocabulary?category=01-fruits&q=rare")
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(repeated.json["items"][0]["id"], item["id"])
        lookup.assert_not_called()

    def test_missing_search_word_reports_wikidata_failure(self):
        self.register_user()
        with patch(
            "sprakverkstan.routes.api.search_wikidata_lexemes",
            side_effect=WikidataLookupError("Wikidata is unavailable"),
        ):
            response = self.client.get("/api/vocabulary?category=01-fruits&q=rare")

        self.assertEqual(response.status_code, 503)
        self.assertIn("Online vocabulary lookup", response.json["error"])

    def test_wikidata_lookup_parses_lexeme_results_without_live_network(self):
        payload = {
            "results": {
                "bindings": [{
                    "lexeme": {"value": "https://www.wikidata.org/entity/L123456"},
                    "lemma": {"value": "sällsynt"},
                    "gloss": {"value": "rare"},
                }],
            },
        }
        response = io.BytesIO(json.dumps(payload).encode("utf-8"))
        with patch("sprakverkstan.vocabulary_lookup.urllib.request.urlopen", return_value=response) as urlopen:
            results = search_wikidata_lexemes("rare")

        self.assertEqual(results, [{
            "lexeme_uri": "https://www.wikidata.org/entity/L123456",
            "lemma": "sällsynt",
            "gloss": "rare",
        }])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 10)


if __name__ == "__main__":
    unittest.main()