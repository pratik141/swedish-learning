import re
import unicodedata

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func, select

from ..extensions import db
from ..models import ExternalVocabularyWord, LearningContent, User, VocabularyWord


api_bp = Blueprint("api", __name__)


def _normalize_search(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def _current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


@api_bp.get("/manifest")
def manifest():
    content = db.session.get(LearningContent, "manifest")
    if content is None:
        return jsonify({"error": "Learning content has not been migrated."}), 503

    payload = dict(content.data)
    payload.pop("notes", None)
    external_count = db.session.scalar(select(db.func.count()).select_from(ExternalVocabularyWord))
    if external_count:
        chapters = list(payload["chapters"])
        chapters.append({
            "title": "🌐 Open vocabulary",
            "label": "🌐 Open vocabulary",
            "level": "B1",
            "slug": "open-vocabulary",
            "count": external_count,
        })
        payload["chapters"] = chapters
        payload["meta"] = {**payload["meta"], "total": payload["meta"]["total"] + external_count}
    return jsonify(payload)


@api_bp.get("/grammar")
def grammar():
    content = db.session.get(LearningContent, "grammar")
    if content is None:
        return jsonify({"error": "Grammar content has not been migrated."}), 503
    return jsonify(content.data)


@api_bp.get("/situations")
def situations():
    content = db.session.get(LearningContent, "situations")
    if content is None:
        return jsonify({"error": "Situation content has not been migrated."}), 503
    return jsonify(content.data)


@api_bp.get("/vocabulary")
def vocabulary():
    category = request.args.get("category")
    requested_ids = request.args.get("ids")
    word_set = request.args.get("set")
    include_all = request.args.get("all") == "true"
    level = request.args.get("level")
    kind = request.args.get("kind")
    search = request.args.get("q", "").strip()
    try:
        limit = min(max(int(request.args.get("limit", "50")), 1), 100)
        offset = max(int(request.args.get("offset", "0")), 0)
    except ValueError:
        return jsonify({"error": "Limit and offset must be integers."}), 400

    selectors = sum((category is not None, requested_ids is not None, word_set is not None, include_all))
    if selectors != 1:
        return jsonify({"error": "Specify one category, ids, set=quick, or all=true."}), 400

    base_filters = []
    external_filters = []
    include_external = include_all
    if category is not None:
        if not re.fullmatch(r"[a-z0-9-]{1,80}", category):
            return jsonify({"error": "Invalid category slug."}), 400
        if category == "open-vocabulary":
            include_external = True
            base_filters.append(VocabularyWord.id < 0)
        else:
            base_filters.append(VocabularyWord.category_slug == category)
    elif requested_ids is not None:
        try:
            ids = list(dict.fromkeys(int(value) for value in requested_ids.split(",") if value))
        except ValueError:
            return jsonify({"error": "Word IDs must be comma-separated integers."}), 400
        if len(ids) > 1000 or any(word_id < 1 for word_id in ids):
            return jsonify({"error": "Request between 1 and 1000 valid word IDs."}), 400
        if not ids:
            return jsonify({"items": [], "count": 0})
        base_filters.append(VocabularyWord.id.in_(ids))
        external_filters.append(ExternalVocabularyWord.id.in_(ids))
        include_external = True
    elif word_set == "quick":
        base_filters.append(VocabularyWord.is_quick_reference.is_(True))
    elif word_set is not None:
        return jsonify({"error": "Unknown vocabulary set."}), 400

    for model, filters in ((VocabularyWord, base_filters), (ExternalVocabularyWord, external_filters)):
        if level:
            filters.append(model.level == level) if hasattr(model, "level") else filters.append(model.data["level"].as_string() == level)
        if kind:
            filters.append(model.kind == kind) if hasattr(model, "kind") else filters.append(model.data["kind"].as_string() == kind)
        if search:
            normalized_terms = _normalize_search(search[:100]).split()
            for term in normalized_terms:
                escaped_term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                filters.append(model.search_text.ilike(f"% {escaped_term}%", escape="\\"))

    base_count = db.session.scalar(select(func.count()).select_from(VocabularyWord).where(*base_filters))
    external_count = 0
    if include_external:
        external_count = db.session.scalar(select(func.count()).select_from(ExternalVocabularyWord).where(*external_filters))
    total = base_count + external_count

    if requested_ids is not None:
        base_query = select(VocabularyWord.data).where(*base_filters).order_by(VocabularyWord.id)
        external_query = select(ExternalVocabularyWord.data).where(*external_filters).order_by(ExternalVocabularyWord.id)
        items = db.session.execute(base_query).scalars().all()
        items.extend(db.session.execute(external_query).scalars().all())
        items.sort(key=lambda item: item["id"])
        return jsonify({"items": items, "count": total, "offset": 0, "hasMore": False})

    base_query = select(VocabularyWord.data).where(*base_filters).order_by(VocabularyWord.id)
    external_query = select(ExternalVocabularyWord.data).where(*external_filters).order_by(ExternalVocabularyWord.id)
    if include_external and (include_all or (category is None and requested_ids is None)):
        if offset < base_count:
            base_items = db.session.execute(base_query.offset(offset).limit(limit)).scalars().all()
            remaining = limit - len(base_items)
            external_items = db.session.execute(external_query.limit(remaining)).scalars().all() if remaining else []
        else:
            base_items = []
            external_items = db.session.execute(external_query.offset(offset - base_count).limit(limit)).scalars().all()
        items = base_items + external_items
    elif category == "open-vocabulary":
        items = db.session.execute(external_query.offset(offset).limit(limit)).scalars().all()
    else:
        items = db.session.execute(base_query.offset(offset).limit(limit)).scalars().all()

    response = jsonify({
        "items": items,
        "count": total,
        "offset": offset,
        "hasMore": offset + len(items) < total,
    })
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


@api_bp.get("/progress")
def get_progress():
    user = _current_user()
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    return jsonify(user.progress_data or {})


@api_bp.put("/progress")
def save_progress():
    user = _current_user()
    if user is None:
        return jsonify({"error": "Authentication required."}), 401

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "Progress must be a JSON object."}), 400

    user.progress_data = payload
    db.session.commit()
    return jsonify({"message": "Progress saved."})