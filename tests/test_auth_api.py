import tempfile
import unittest
from pathlib import Path

from sprakverkstan import create_app
from sprakverkstan.extensions import db


class AuthApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_directory.name) / "test.db"
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-only-secret",
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{database_path}",
            "AUTO_CREATE_TABLES": True,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_directory.cleanup()

    def test_register_login_and_progress_round_trip(self):
        response = self.client.post("/api/register", json={
            "name": "Test Learner",
            "email": "TEST@example.com",
            "password": "secure-pass-123",
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["user"]["email"], "test@example.com")
        self.assertEqual(self.client.get("/api/me").status_code, 200)

        saved = self.client.put("/api/progress", json={"learned": ["word-1"]})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get("/api/progress").json, {"learned": ["word-1"]})

        self.client.post("/api/logout")
        self.assertEqual(self.client.get("/api/progress").status_code, 401)
        self.assertEqual(self.client.post("/api/login", json={
            "email": "test@example.com",
            "password": "secure-pass-123",
        }).status_code, 200)
        self.assertEqual(self.client.get("/api/progress").json, {"learned": ["word-1"]})

    def test_rejects_weak_password_and_duplicate_email(self):
        account = {"name": "Test Learner", "email": "test@example.com", "password": "secure-pass-123"}
        self.assertEqual(self.client.post("/api/register", json={**account, "password": "short"}).status_code, 400)
        self.assertEqual(self.client.post("/api/register", json=account).status_code, 201)
        self.assertEqual(self.client.post("/api/register", json=account).status_code, 409)

    def test_progress_requires_object_payload(self):
        self.client.post("/api/register", json={
            "name": "Test Learner",
            "email": "test@example.com",
            "password": "secure-pass-123",
        })
        self.assertEqual(self.client.put("/api/progress", json=["invalid"]).status_code, 400)


if __name__ == "__main__":
    unittest.main()