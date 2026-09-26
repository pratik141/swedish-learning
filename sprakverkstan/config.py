import os
from datetime import timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
INSTANCE_DIRECTORY = ROOT / "instance"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    database_url = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{INSTANCE_DIRECTORY / 'sprakverkstan.db'}",
    )
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    secure_cookie_default = "true" if os.environ.get("K_SERVICE") else "false"
    SESSION_COOKIE_SECURE = os.environ.get("COOKIE_SECURE", secure_cookie_default).lower() == "true"
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    MAX_CONTENT_LENGTH = 32 * 1024
    PORT = int(os.environ.get("PORT", "8080"))
    AUTO_CREATE_TABLES = os.environ.get("AUTO_CREATE_TABLES", "true").lower() == "true"