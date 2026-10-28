import unittest

from sprakverkstan.config import _normalize_database_url


class DatabaseUrlConfigTests(unittest.TestCase):
    def test_postgres_urls_select_installed_psycopg2_driver(self):
        self.assertEqual(
            _normalize_database_url("postgres://user:pass@example/db"),
            "postgresql+psycopg2://user:pass@example/db",
        )
        self.assertEqual(
            _normalize_database_url("postgresql://user:pass@example/db"),
            "postgresql+psycopg2://user:pass@example/db",
        )

    def test_explicit_driver_and_sqlite_urls_are_preserved(self):
        self.assertEqual(
            _normalize_database_url("postgresql+psycopg2://user:pass@example/db"),
            "postgresql+psycopg2://user:pass@example/db",
        )
        self.assertEqual(
            _normalize_database_url("sqlite:////app/instance/app.db"),
            "sqlite:////app/instance/app.db",
        )


if __name__ == "__main__":
    unittest.main()
