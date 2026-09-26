from flask import Blueprint, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import User


auth_bp = Blueprint("auth", __name__)


def _credentials():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, (jsonify({"error": "A JSON request body is required."}), 400)

    email = payload.get("email")
    password = payload.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return None, (jsonify({"error": "Email and password are required."}), 400)

    email = email.strip().lower()
    if len(email) > 254 or "@" not in email:
        return None, (jsonify({"error": "Enter a valid email address."}), 400)
    if not password:
        return None, (jsonify({"error": "Email and password are required."}), 400)
    return (payload, email, password), None


@auth_bp.post("/register")
def register():
    credentials, error = _credentials()
    if error:
        return error

    payload, email, password = credentials
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        return jsonify({"error": "Name is required."}), 400
    if len(name.strip()) > 120:
        return jsonify({"error": "Name must be 120 characters or fewer."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters."}), 400

    user = User(name=name.strip(), email=email, progress_data={})
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "An account with this email already exists."}), 409

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    return jsonify({"message": "Account created.", "user": user.to_public_dict()}), 201


@auth_bp.post("/login")
def login():
    credentials, error = _credentials()
    if error:
        return error
    _, email, password = credentials

    user = db.session.execute(db.select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    return jsonify({"message": "Signed in.", "user": user.to_public_dict()})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})


@auth_bp.get("/me")
def me():
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if user is None:
        return jsonify({"error": "Authentication required."}), 401
    return jsonify({"user": user.to_public_dict()})