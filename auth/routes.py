
from flask import Blueprint, request, jsonify, current_app
from flask_pymongo import PyMongo
from bson import ObjectId
import bcrypt
import jwt
import datetime
from functools import wraps
import re
from http import HTTPStatus
from dataset import users_collection

auth_bp = Blueprint('auth', __name__)

# Email validation regex
EMAIL_REGEX = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

# Token required decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({"message": "Token is missing"}), HTTPStatus.UNAUTHORIZED
        try:
            token = token.split(" ")[1]  # Expecting "Bearer <token>"
            jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token"}), HTTPStatus.UNAUTHORIZED
        return f(*args, **kwargs)
    return decorated

# Validate input fields
def validate_signup_data(data, user_type):
    required_fields = ["nom", "prenom", "email", "password"]
    if user_type == "doctor":
        required_fields.append("matricule")
    else:
        required_fields.append("age")
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"{field.capitalize()} is required"
    
    if not re.match(EMAIL_REGEX, data["email"]):
        return False, "Invalid email format"
    
    if len(data["password"]) < 8:
        return False, "Password must be at least 8 characters long"
    
    if user_type == "visitor":
        age = str(data["age"])
        if not age.isdigit() or int(age) <= 0:
            return False, "Age must be a positive integer"
    
    return True, ""

# Signup endpoint
@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    user_type = data.get("user_type", "visitor")  # Default to visitor if not specified

    # Validate input
    is_valid, error_message = validate_signup_data(data, user_type)
    if not is_valid:
        return jsonify({"message": error_message}), HTTPStatus.BAD_REQUEST

    # Check if email already exists
    if users_collection.find_one({"email": data["email"]}):
        return jsonify({"message": "Email already exists"}), HTTPStatus.BAD_REQUEST

    # Hash password
    hashed_password = bcrypt.hashpw(data["password"].encode('utf-8'), bcrypt.gensalt())

    # Prepare user data
    user_data = {
        "nom": data["nom"],
        "prenom": data["prenom"],
        "email": data["email"],
        "password": hashed_password,
        "user_type": user_type,
        "created_at": datetime.datetime.utcnow()
    }
    
    if user_type == "doctor":
        user_data["matricule"] = data["matricule"]
    else:
        user_data["age"] = int(data["age"])

    # Insert user into MongoDB
    users_collection.insert_one(user_data)
    return jsonify({"message": "User registered successfully"}), HTTPStatus.CREATED


@auth_bp.route("/signin", methods=["POST"])
def signin():
    data = request.get_json()
    
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"message": "Email et mot de passe requis"}), HTTPStatus.BAD_REQUEST

    # Find user by email
    user = users_collection.find_one({"email": data["email"]})
    if not user:
        return jsonify({"message": "Email ou mot de passe invalide"}), HTTPStatus.UNAUTHORIZED

    # Verify password
    if bcrypt.checkpw(data["password"].encode('utf-8'), user["password"]):
        # Generate JWT token
        token = jwt.encode({
            "user_id": str(user["_id"]),
            "email": user["email"],
            "user_type": user["user_type"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, current_app.config["SECRET_KEY"], algorithm="HS256")
        
        # Prepare response
        response = {
            "message": "Connexion réussie",
            "token": token,
            "user_type": user["user_type"]
        }
        
        # Include matricule for doctors
        if user["user_type"] == "doctor" and "matricule" in user:
            response["matricule"] = user["matricule"]

        return jsonify(response), HTTPStatus.OK
    
    return jsonify({"message": "Email ou mot de passe invalide"}), HTTPStatus.UNAUTHORIZED