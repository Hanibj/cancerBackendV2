
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
import string
import random
from flask_mail import Mail, Message
auth_bp = Blueprint('auth', __name__)


def generate_password(length=12):
    """
    Génère un mot de passe aléatoire sécurisé.
    
    Paramètres :
    - length (int) : Longueur du mot de passe (par défaut 12).
    
    Retourne :
    - str : Mot de passe généré.
    """
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(random.choice(characters) for _ in range(length))
    return password

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


def validate_signup_data(data, user_type):
    required_fields = ["nom", "prenom", "email", "password","telephone"]
    if user_type.lower() == "doctor":
        required_fields.append("matricule")
    else:  # visitor
        required_fields.extend(["age", "specialite"])
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False, f"{field.capitalize()} is required"
    
    if not re.match(EMAIL_REGEX, data["email"]):
        return False, "Invalid email format"
    
    if len(data["password"]) < 8:
        return False, "Password must be at least 8 characters long"
    
    if user_type.lower() == "visitor":
        try:
            age = int(data["age"])
            if age <= 0:
                return False, "Age must be a positive integer"
        except (ValueError, TypeError):
            return False, "Age must be a valid integer"
        
      
    
    return True, ""

@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), HTTPStatus.BAD_REQUEST
        
        user_type = data.get("user_type", "visitor").lower()  # Normalize to lowercase

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
            "telephone":data['telephone'],
            "password": hashed_password,
            "user_type": user_type,
            "created_at": datetime.datetime.utcnow()
        }
        
        if user_type == "doctor":
            user_data["matricule"] = data["matricule"]
        else:  # visitor
            user_data["age"] = int(data["age"])
            user_data["specialite"] = data["specialite"]
        
        # Insert user into MongoDB
        users_collection.insert_one(user_data)
        return jsonify({"message": "User registered successfully"}), HTTPStatus.CREATED
    
    except PyMongoError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error during signup: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
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

@auth_bp.route('/forget-password', methods=['POST'])
def forget_password():
    try:
        # Get email from request body
        data = request.get_json()
        email = data.get('email')
        print(f"Received email: {email}")
        if not email:
            return jsonify({'message': 'Email is required'}), 400

        # Find user by email
        user =users_collection.find_one({'email': email})
        if not user:
            return jsonify({'message': 'User not found'}), 404
        print(f"Found user: {user}")

        # Generate a new password
        new_password = generate_password(12)
        print(f"Generated password: {new_password}")

        # Hash the new password and update the user's document
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        users_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'password': hashed_password}}
        )
        print("User password updated in database")

        # Access Flask-Mail instance from the current app
        mail = Mail(current_app)

        # Create and send the email with the new password
        msg = Message(
            subject='Password Reset Request',
            recipients=[email],
            html=f"""
            <p>Bonjour,</p>
            <p>Votre mot de passe a été réinitialisé. Voici votre nouveau mot de passe temporaire :</p>
            <p><strong>{new_password}</strong></p>
            <p>Veuillez vous connecter avec ce mot de passe et le modifier immédiatement dans votre profil.</p>
            <p>Si vous n'avez pas demandé cette réinitialisation, contactez notre support.</p>
            <p>Cordialement,<br>Votre Application</p>
            """
        )
        print(f"Email message prepared: {msg}")
        mail.send(msg)
        print("Email sent successfully")

        return jsonify({'message': 'Password reset email sent successfully'}), 200

    except Exception as e:
        print(f"Error in forget_password: {str(e)}")
        return jsonify({'message': 'Error sending email', 'error': str(e)}), 500