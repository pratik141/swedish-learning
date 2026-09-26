from pathlib import Path

from flask import Flask, abort, jsonify, send_from_directory
from sqlalchemy import text

from .config import Config
from .extensions import db


def create_app(test_config=None):
    root = Path(__file__).resolve().parent.parent
    instance_path = root / "instance"
    instance_path.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, instance_path=str(instance_path), instance_relative_config=True)
    app.config.from_object(Config)
    app.config["SITE_DIRECTORY"] = root / "docs"
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY to a long random value before starting the service.")

    db.init_app(app)

    from . import models
    from .routes.api import api_bp
    from .routes.auth import auth_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")

    @app.get("/api/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Database health check failed")
            return jsonify({"status": "error", "service": "sprakverkstan"}), 503
        return jsonify({"status": "ok", "service": "sprakverkstan"})

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def site(path):
        if path == "data" or path.startswith("data/"):
            abort(404)
        site_directory = app.config["SITE_DIRECTORY"]
        requested = site_directory / path
        if path and requested.is_file():
            return send_from_directory(site_directory, path)
        return send_from_directory(site_directory, "index.html")

    if app.config.get("AUTO_CREATE_TABLES"):
        with app.app_context():
            db.create_all()

    return app