from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import Index

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    progress_data = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_public_dict(self):
        return {"id": self.id, "name": self.name, "email": self.email}


class VocabularyWord(db.Model):
    __tablename__ = "vocabulary_words"
    __table_args__ = (
        Index("ix_vocabulary_category_order", "category_slug", "id"),
        Index("ix_vocabulary_level_kind", "level", "kind"),
    )

    id = db.Column(db.Integer, primary_key=True)
    category_slug = db.Column(db.String(80), nullable=False)
    level = db.Column(db.String(8), nullable=False)
    kind = db.Column(db.String(24), nullable=False)
    is_quick_reference = db.Column(db.Boolean, nullable=False, default=False, index=True)
    data = db.Column(db.JSON, nullable=False)
    search_text = db.Column(db.Text, nullable=False, default="")


class SchemaMigration(db.Model):
    __tablename__ = "schema_migrations"

    revision = db.Column(db.String(64), primary_key=True)
    applied_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class LearningContent(db.Model):
    __tablename__ = "learning_content"

    key = db.Column(db.String(80), primary_key=True)
    data = db.Column(db.JSON, nullable=False)


class ExternalVocabularyWord(db.Model):
    __tablename__ = "external_vocabulary_words"

    id = db.Column(db.Integer, primary_key=True)
    source_key = db.Column(db.String(255), unique=True, nullable=False)
    source_uri = db.Column(db.String(500), nullable=False)
    data = db.Column(db.JSON, nullable=False)
    search_text = db.Column(db.Text, nullable=False, default="")