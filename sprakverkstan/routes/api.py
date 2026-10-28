import hashlib
import re
import unicodedata

from flask import Blueprint, current_app, jsonify, request, session
from sqlalchemy import func, select

from ..extensions import db
from ..models import ExternalVocabularyWord, LearningContent, User, VocabularyWord
from ..vocabulary_lookup import WikidataLookupError, search_wikidata_lexemes


api_bp = Blueprint("api", __name__)

FREE_WORD_IDS = tuple(range(610, 630))
FREE_GRAMMAR_LESSONS = {
    "En and ett gender",
    "Present tense",
    "V2 main-clause order",
}


def _normalize_search(value):
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(char for char in decomposed if not unicodedata.combining(char)).split())


def _current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None


def _store_wikidata_lexemes(search):
    lexemes = search_wikidata_lexemes(search)
    if not lexemes:
        return []

    existing_words = db.session.execute(select(VocabularyWord.data["sv"])).scalars().all()
    existing_words.extend(db.session.execute(select(ExternalVocabularyWord.data["sv"])).scalars().all())
    seen_lemmas = {word.casefold() for word in existing_words if word}
    next_id = max(
        db.session.scalar(select(func.max(VocabularyWord.id))) or 0,
        db.session.scalar(select(func.max(ExternalVocabularyWord.id))) or 1_000_000,
    ) + 1

    additions = []
    for lexeme in lexemes:
        lemma = lexeme["lemma"]
        gloss = lexeme["gloss"]
        lexeme_uri = lexeme["lexeme_uri"]
        if lemma.casefold() in seen_lemmas:
            continue

        source_key = f"{lexeme_uri}|{gloss.casefold()}"
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
                "license": "CC0-1.0",
            },
        }
        additions.append(ExternalVocabularyWord(
            id=next_id,
            source_key=hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:16],
            source_uri=lexeme_uri,
            data=item,
            search_text=f" {_normalize_search(' '.join((lemma, gloss)))} ",
        ))
        seen_lemmas.add(lemma.casefold())
        next_id += 1

    db.session.add_all(additions)
    db.session.commit()
    return [item.data for item in additions]


@api_bp.get("/manifest")
def manifest():
    content = db.session.get(LearningContent, "manifest")
    if content is None:
        return jsonify({"error": "Learning content has not been migrated."}), 503

    payload = dict(content.data)
    payload.pop("notes", None)
    if _current_user() is None:
        free_chapter = next(
            chapter for chapter in payload["chapters"]
            if chapter["slug"] == "20-essential-everyday-expressions"
        )
        payload["chapters"] = [{
            **free_chapter,
            "title": "Free beginner phrases",
            "label": "Free beginner phrases",
            "count": len(FREE_WORD_IDS),
        }]
        payload["meta"] = {**payload["meta"], "total": len(FREE_WORD_IDS), "quickTotal": len(FREE_WORD_IDS)}
        payload["quickIds"] = list(FREE_WORD_IDS)
        response = jsonify(payload)
        response.headers["Cache-Control"] = "private, no-store"
        return response

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
    response = jsonify(payload)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@api_bp.get("/grammar")
def grammar():
    content = db.session.get(LearningContent, "grammar")
    if content is None:
        return jsonify({"error": "Grammar content has not been migrated."}), 503
    grammar_data = content.data
    if _current_user() is None:
        grammar_data = [
            {
                **group,
                "lessons": [
                    lesson for lesson in group["lessons"]
                    if lesson["title"] in FREE_GRAMMAR_LESSONS
                ],
            }
            for group in grammar_data
            if any(lesson["title"] in FREE_GRAMMAR_LESSONS for lesson in group["lessons"])
        ]
    response = jsonify(grammar_data)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@api_bp.get("/situations")
def situations():
    if _current_user() is None:
        return jsonify({"error": "Sign in to unlock Situations."}), 401
    content = db.session.get(LearningContent, "situations")
    if content is None:
        return jsonify({"error": "Situation content has not been migrated."}), 503
    response = jsonify(content.data)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@api_bp.get("/vocabulary")
def vocabulary():
    user = _current_user()
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

    if user is None:
        base_filters.append(VocabularyWord.id.in_(FREE_WORD_IDS))
        external_filters.append(ExternalVocabularyWord.id < 0)

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

    fallback_external = False
    if user is not None and search and requested_ids is None and base_count == 0:
        if not include_external:
            external_count = db.session.scalar(
                select(func.count()).select_from(ExternalVocabularyWord).where(*external_filters)
            )
        if external_count:
            include_external = True
            fallback_external = True
        elif (not level or level == "B1") and (not kind or kind == "word"):
            try:
                items = _store_wikidata_lexemes(search[:100])
            except WikidataLookupError:
                current_app.logger.exception("Wikidata vocabulary lookup failed")
                return jsonify({"error": "Online vocabulary lookup is temporarily unavailable."}), 503
            items = [
                item for item in items
                if (not level or item["level"] == level) and (not kind or item["kind"] == kind)
            ]
            if items:
                page_items = items[offset:offset + limit]
                return jsonify({
                    "items": page_items,
                    "count": len(items),
                    "offset": offset,
                    "hasMore": offset + len(page_items) < len(items),
                })

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
    if fallback_external:
        items = db.session.execute(external_query.offset(offset).limit(limit)).scalars().all()
    elif include_external and (include_all or (category is None and requested_ids is None)):
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
    response.headers["Cache-Control"] = "private, no-store"
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