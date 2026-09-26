import tempfile
import unittest
from pathlib import Path

from sprakverkstan import create_app
from sprakverkstan.extensions import db
from sprakverkstan.migrations import upgrade_all
from sprakverkstan.models import ExternalVocabularyWord, LearningContent, VocabularyWord


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
        repeat_results = upgrade_all(self.app)
        self.assertTrue(all(result["already_applied"] for result in repeat_results))
        with self.app.app_context():
            self.assertEqual(db.session.query(VocabularyWord).count(), 760)
            self.assertEqual(db.session.query(LearningContent).count(), 3)

    def test_api_serves_only_requested_vocabulary(self):
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
        self.assertEqual(len(situations.json), 10)
        self.assertEqual(self.client.get("/data/manifest.json").status_code, 404)
        self.assertEqual(self.client.get("/data/grammar.json").status_code, 404)

    def test_external_open_licensed_words_are_separate_and_attributed(self):
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


if __name__ == "__main__":
    unittest.main()