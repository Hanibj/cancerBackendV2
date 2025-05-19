from flask import Blueprint, request, jsonify, current_app,json
from flask_pymongo import PyMongo
from bson import ObjectId
import bcrypt
import jwt
import datetime
from functools import wraps
import re
from http import HTTPStatus
from dataset import users_collection
import logging
from pymongo.errors import PyMongoError
import string
import random
import bcrypt
from flask_mail import Mail, Message
Doctor_bp = Blueprint('doctor', __name__)

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


def get_next_doctor_matricule():
    """Génère un matricule unique pour un docteur au format MAT-xxxxxx."""
    last_doctor = users_collection.find_one(
        {"user_type": "doctor"},
        sort=[("matricule", -1)]
    )
    if last_doctor and "matricule" in last_doctor:
        matricule = last_doctor["matricule"]
        # Check the format of matricule
        if "MAT-" in matricule:
            # New format: MAT-xxxxxx
            last_id = int(matricule.split("MAT-")[1])
        elif "DPT-D" in matricule:
            # Old format: DPT-Dxxxxx
            last_id = int(matricule.split("DPT-D")[1])
        elif "DR-" in matricule:
            # Old format: DR-xxxxx
            last_id = int(matricule.split("DR-")[1])
        else:
            # Fallback if format is unrecognized
            last_id = 0
        next_id = last_id + 1
    else:
        next_id = 1  # Start at 1 if no doctors exist

    return f"MAT-{next_id:06d}"  # Ex: MAT-000001

@Doctor_bp.route('/', methods=['GET'])
def get_doctors():
    try:


        # Find doctors with case-insensitive user_type 'doctor'
        doctors_cursor = users_collection.find(
            {'user_type': 'doctor'},
            {
                '_id': 1,
                'username': 1,
                'specialite': 1,
                'created_at': 1
            },
            collation={'locale': 'en', 'strength': 2}
        )

        # Convert cursor to list and serialize ObjectId
        doctors = []
        for doc in doctors_cursor:
            doc['_id'] = str(doc['_id'])
            doctors.append(doc)

        # Get total count for pagination metadata
        doctors = users_collection.find(
            {'user_type': 'doctor'},
            collation={'locale': 'en', 'strength': 2}
        )


        return jsonify({
            "message": "Doctors retrieved successfully",
            "doctors": doctors,
      
        }), HTTPStatus.OK

    except PyMongoError as e:
        logging.error(f"Database error retrieving doctors: {str(e)}")
        return jsonify({
            "message": f"Database error: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    except ValueError as e:
        logging.error(f"Invalid pagination parameters: {str(e)}")
        return jsonify({
            "message": "Invalid page or per_page parameters"
        }), HTTPStatus.BAD_REQUEST
    except Exception as e:
        logging.error(f"Unexpected error retrieving doctors: {str(e)}")
        return jsonify({
            "message": "Error retrieving doctors"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@Doctor_bp.route("/add-doctor",methods=['POST'])
def add_doctors():
    try:
        email=request.get_json(["email"])
        nom=request.get_json(["nom"])
        prenom=request.get_json(["prenom"])
        print("email",email)
        print("email",nom)
        print("email",prenom)
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided"}), HTTPStatus.BAD_REQUEST
        if users_collection.find_one({"email": data["email"]}):
            return jsonify({"message": "Email already exists"}), HTTPStatus.BAD_REQUEST
        password = generate_password()
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        if data["matricule"]=="":
            matricule=get_next_doctor_matricule()
        else:
            matricule=data["matricule"]
        # Prepare user data
        user_data = {
            "nom": data["nom"],
            "prenom": data["prenom"],
            "email": data["email"],
            "telephone":data['telephone'],
            "password": hashed_password,
            "user_type": "doctor",
            "matricule" :matricule,
            "created_at": datetime.datetime.utcnow()
        }
        

        # Insert user into MongoDB
        result=users_collection.insert_one(user_data)
       
        mail=Mail()
    # Envoyer un e-mail au docteur avec le mot de passe
        try:
            msg = Message(
            subject="Votre compte a été créé",
            sender="votre_email@example.com",  # Remplacer par votre adresse e-mail
            recipients=[data["email"]]
             )
            msg.body = f"""
            Bonjour Dr. {data["prenom"]} {data["nom"]},

            Votre compte a été créé avec succès. Voici vos identifiants de connexion :

            Email : {data["email"]}
            Mot de passe : {password}

            Veuillez changer votre mot de passe après votre première connexion pour des raisons de sécurité.

            Cordialement,
            Votre équipe
            """
            mail.send(msg)
        except Exception as e:
        # En cas d'erreur d'envoi d'e-mail, loguer l'erreur mais ne pas bloquer l'ajout
            print(f"Erreur lors de l'envoi de l'e-mail : {e}")
        return jsonify({"message": "User registered successfully"}), HTTPStatus.CREATED
    
    except PyMongoError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error during signup: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@Doctor_bp.route("/updateDoctor/<matricule>",methods=["PUT"])
def update_doctors(matricule):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données JSON requises"}), HTTPStatus.BAD_REQUEST

        # Find patient by patient_id and FolderNumber
        existing_doctor = users_collection.find_one({
            "matricule": matricule,
            
        })
        if not existing_doctor:
            return jsonify({"message": "Patient non trouvé avec patient_id et FolderNumber spécifiés"}), HTTPStatus.NOT_FOUND

        # Prepare updated patient data
        doctor_data = {
            "matricule":existing_doctor.get("matricule") ,
            "nom": data.get("nom", existing_doctor.get("nom", "")),
            "prenom":data.get("prenom", existing_doctor.get("prenom", "")),
            "email":data.get("email", existing_doctor.get("email", "")),
            "user_type":data.get("user_type", existing_doctor.get("user_type", "")),
            "password":data.get("password", existing_doctor.get("password", "")),
            "telephone":data.get("telephone",existing_doctor.get("telephone", ""))
        }

        # Update patient in MongoDB
        result = users_collection.update_one(
            {"matricule":matricule},
            {"$set": doctor_data}
        )

        if result.modified_count == 0:
            return jsonify({"message": "Aucune modification effectuée"}), HTTPStatus.OK

        # Return updated patient
        updated_doctor = users_collection.find_one({"matricule": matricule})
        return jsonify({
            "message": "Patient mis à jour avec succès",
            "doctor": {
                "_id": str(updated_doctor["_id"]),
                "matricule":updated_doctor["matricule"],
                "nom":updated_doctor["nom"],
                "prenom":updated_doctor["prenom"],
                "email":updated_doctor["email"],
                "user_type":updated_doctor["user_type"],
                "password":updated_doctor["password"],
                "telephone":updated_doctor["telephone"],

            }
        }), HTTPStatus.OK

    except json.JSONDecodeError:
        return jsonify({"message": "Format JSON invalide"}), HTTPStatus.BAD_REQUEST
    except PyMongoError as e:
        return jsonify({"message": f"Erreur de base de données : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR



@Doctor_bp.route("/delete-doctors/<matricule>", methods=["DELETE"])
def delete_doctors(matricule):
    try:
        # Validate matricule format (optional, adjust regex as needed)
        if not matricule or not isinstance(matricule, str):
            return jsonify({"message": "Invalid matricule provided"}), HTTPStatus.BAD_REQUEST

        # Check if doctor exists
        existing_doctor = users_collection.find_one({"matricule": matricule})
        if not existing_doctor:
            return jsonify({"message": f"Doctor not found with matricule: {matricule}"}), HTTPStatus.NOT_FOUND

        # Perform deletion
        result = users_collection.delete_one({"matricule": matricule})
        if result.deleted_count == 0:
            return jsonify({"message": "Doctor not deleted, possibly already removed"}), HTTPStatus.NOT_FOUND

        return jsonify({"message": "Doctor deleted successfully"}), HTTPStatus.OK

    except PyMongoError as e:
        return jsonify({"message": f"Database error during doctor deletion: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Unexpected error during doctor deletion: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR 