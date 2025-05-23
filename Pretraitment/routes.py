
from flask import Blueprint, request, jsonify, send_file
from http import HTTPStatus
from dataset import patients_collection, db
from gridfs import GridFS
import json
from bson import ObjectId
import io
from pymongo.errors import PyMongoError
from datetime import datetime
import numpy as np
from scipy import stats
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from imblearn.over_sampling import SMOTE
import pandas as pd
from sklearn.preprocessing import LabelEncoder
pretraitement_bp = Blueprint('pretraitement', __name__)
gridfs = GridFS(db)  # Initialize GridFS

# Endpoint pour suppression des colonnes/lignes inutiles ou corrompues
# @pretraitement_bp.route("/preprocess/clean/<DoctorId>", methods=["POST"])
# def preprocess_clean(DoctorId):
#     try:
#         data = request.get_json()
#         if not data or 'DoctorId' not in data:
#             return jsonify({"message": "DoctorId requis dans le corps de la requête JSON"}), HTTPStatus.BAD_REQUEST

#         doctor_id = DoctorId
#         if not isinstance(doctor_id, str) or not doctor_id.strip():
#             return jsonify({"message": "DoctorId doit être une chaîne non vide"}), HTTPStatus.BAD_REQUEST

#         # Récupérer uniquement les patients associés au DoctorId
#         patients = patients_collection.find({"DoctorId": doctor_id})
#         patients_updated = 0

#         for patient in patients:
#             patient_id = patient.get("patient_id")
#             donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])

#             # Filtrer les lignes avec trop de valeurs manquantes (seuil : > 25% des champs)
#             cleaned_data = []
#             for row in donnees_cliniques:
#                 if isinstance(row, dict):
#                     missing_count = sum(1 for v in row.values() if v is None or v == "")
#                     if missing_count / len(row) <= 0.25:  # Seuil de 25%
#                         cleaned_data.append(row)

#             # Supprimer les colonnes non informatives (exemple : IDs, doublons)
#             if cleaned_data:
#                 all_fields = set().union(*[set(row.keys()) for row in cleaned_data])
#                 informative_fields = [f for f in all_fields if f.lower() not in ("patientid", "foldernumber", "id")]
#                 cleaned_data = [{k: v for k, v in row.items() if k in informative_fields} for row in cleaned_data]

#             # Mettre à jour uniquement le patient correspondant
#             result = patients_collection.update_one(
#                 {"patient_id": patient_id, "DoctorId": doctor_id},
#                 {"$set": {"Donnees_cliniques_clean": cleaned_data}}
#             )
#             if result.modified_count > 0:
#                 patients_updated += 1

#         if patients_updated == 0:
#             return jsonify({"message": "Aucun patient trouvé ou modifié pour ce DoctorId"}), HTTPStatus.OK

#         return jsonify({"message": f"Dataset cleaned successfully for {patients_updated} patients"}), HTTPStatus.OK
#     except Exception as e:
#         return jsonify({"message": f"Error during cleaning: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
@pretraitement_bp.route("/preprocess/clean/<DoctorId>", methods=["POST"])
def preprocess_clean(DoctorId):
    try:
        doctor_id = DoctorId
        if not isinstance(doctor_id, str) or not doctor_id.strip():
            return jsonify({"message": "DoctorId doit être une chaîne non vide"}), HTTPStatus.BAD_REQUEST

        # Récupérer les patients associés au DoctorId
        patients = patients_collection.find({"DoctorId": doctor_id})
        patients_updated = 0

        for patient in patients:
            patient_id = patient.get("patient_id")
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            
            if not donnees_cliniques or not all(isinstance(row, dict) for row in donnees_cliniques):
                continue  # Ignorer si les données sont vides ou mal formées

            # Filtrer les lignes avec trop de valeurs manquantes
            cleaned_data = []
            for row in donnees_cliniques:
                missing_count = sum(1 for v in row.values() if v is None or v == "")
                if missing_count / len(row) <= 0.25:  # Seuil de 25%
                    cleaned_data.append(row)

            # Supprimer les colonnes non informatives
            if cleaned_data:
                try:
                    all_fields = set().union(*[set(row.keys()) for row in cleaned_data])
                    informative_fields = [f for f in all_fields if f.lower() not in ("patientid", "foldernumber", "id")]
                    cleaned_data = [{k: v for k, v in row.items() if k in informative_fields} for row in cleaned_data]
                except (TypeError, AttributeError) as e:
                    print(f"Erreur de structure pour patient {patient_id}: {str(e)}")
                    continue

            # Mettre à jour le patient
            result = patients_collection.update_one(
                {"patient_id": patient_id, "DoctorId": doctor_id},
                {"$set": {"Donnees_cliniques_clean": cleaned_data}}
            )
            if result.modified_count > 0:
                patients_updated += 1

        if patients_updated == 0:
            return jsonify({"message": "Aucun patient trouvé ou modifié pour ce DoctorId"}), HTTPStatus.OK

        return jsonify({"message": f"Dataset cleaned successfully for {patients_updated} patients"}), HTTPStatus.OK
    except PyMongoError as e:
        return jsonify({"message": f"Erreur MongoDB : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Erreur lors du nettoyage : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

# Endpoint pour imputation des valeurs manquantes
@pretraitement_bp.route("/preprocess/impute/<DoctorId>", methods=["POST"])
def preprocess_impute(DoctorId):
    try:
     
    
        doctor_id = DoctorId
        if not isinstance(doctor_id, str) or not doctor_id.strip():
            return jsonify({"message": "DoctorId doit être une chaîne non vide"}), HTTPStatus.BAD_REQUEST

        # Récupérer uniquement les patients associés au DoctorId
        patients = patients_collection.find({"DoctorId": doctor_id})
        patients_updated = 0

        for patient in patients:
            patient_id = patient.get("patient_id")
            donnees_cliniques = patient.get("Donnees_cliniques_clean", [])
            imputed_data = []

            if not donnees_cliniques:
                continue

            # Calculer la médiane pour chaque champ numérique
            field_medians = {}
            for row in donnees_cliniques:
                for field, value in row.items():
                    if value is not None and value != "" and isinstance(value, (int, float)):
                        field_medians[field] = field_medians.get(field, [])
                        field_medians[field].append(float(value))

            for field in field_medians:
                field_medians[field] = np.median(field_medians[field]) if field_medians[field] else 0

            # Imputer les valeurs manquantes avec la médiane
            for row in donnees_cliniques:
                imputed_row = row.copy()
                for field in row:
                    if row[field] is None or row[field] == "":
                        imputed_row[field] = field_medians.get(field, 0)
                imputed_data.append(imputed_row)

            # Mettre à jour uniquement le patient correspondant
            result = patients_collection.update_one(
                {"patient_id": patient_id, "DoctorId": doctor_id},
                {"$set": {"Donnees_cliniques_impute": imputed_data}}
            )
            if result.modified_count > 0:
                patients_updated += 1

        if patients_updated == 0:
            return jsonify({"message": "Aucun patient trouvé ou modifié pour ce DoctorId"}), HTTPStatus.OK

        return jsonify({"message": f"Dataset imputed successfully for {patients_updated} patients"}), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error during imputation: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

# Endpoint pour balancement des classes
@pretraitement_bp.route("/preprocess/balance/<DoctorId>", methods=["POST"])
def preprocess_balance(DoctorId):
    try:
        print(DoctorId)
        doctor_id = DoctorId
        if not isinstance(doctor_id, str) or not doctor_id.strip():
            return jsonify({"message": "DoctorId doit être une chaîne non vide"}), HTTPStatus.BAD_REQUEST

        # Récupérer uniquement les patients associés au DoctorId
        patients = patients_collection.find({"DoctorId": doctor_id})
        patients_updated = 0
        print("patients",patients)
        for patient in patients:
            patient_id = patient.get("patient_id")
            donnees_cliniques = patient.get("Donnees_cliniques_impute", [])
            if not donnees_cliniques:
                continue
            
            # Compter les classes
            class_counts = {}
            for row in donnees_cliniques:
                if isinstance(row, dict) and "Class" in row:
                    class_value = row["Class"]
                    class_counts[class_value] = class_counts.get(class_value, 0) + 1

            if not class_counts:
                continue

            min_count = min(class_counts.values())
            balanced_data = []

            # Undersampling ou oversampling (simplifié)
            for class_value in class_counts:
                class_rows = [row for row in donnees_cliniques if row.get("Class") == class_value]
                if len(class_rows) > min_count:
                    balanced_data.extend(class_rows[:min_count])  # Undersampling
                else:
                    balanced_data.extend(class_rows * (min_count // len(class_rows)) + class_rows[:min_count % len(class_rows)])  # Oversampling
            print("balanced_data",balanced_data)
            # Mettre à jour uniquement le patient correspondant
            result = patients_collection.update_one(
                {"patient_id": patient_id, "DoctorId": doctor_id},
                {"$set": {"Donnees_cliniques_balance": balanced_data}}
            )
            print("result",result)
            if result.modified_count > 0:
                patients_updated += 1

        if patients_updated == 0:
            return jsonify({"message": "Aucun patient trouvé ou modifié pour ce DoctorId"}), HTTPStatus.OK

        return jsonify({"message": f"Dataset balanced successfully for {patients_updated} patients"}), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error during balancing: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@pretraitement_bp.route("/preprocess/normalize/<DoctorId>", methods=["POST"])
def preprocess_normalize(DoctorId):
    try:
        doctor_id = DoctorId
        if not isinstance(doctor_id, str) or not doctor_id.strip():
            return jsonify({"message": "DoctorId doit être une chaîne non vide"}), HTTPStatus.BAD_REQUEST

        # Récupérer les données
        all_data = []
        patients = patients_collection.find({"DoctorId": doctor_id})
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_balance", [])
            all_data.extend([row for row in donnees_cliniques if isinstance(row, dict)])

        if not all_data:
            return jsonify({"message": "Aucun patient trouvé pour ce DoctorId ou aucune donnée à normaliser"}), HTTPStatus.OK

        # Calculer les statistiques (min et max uniquement)
        field_stats = {}
        for row in all_data:
            for field, value in row.items():
                if field.lower() == "index":  # Ignorer le champ index
                    continue
                if value is not None and value != "":
                    try:
                        if isinstance(value, str) and value.strip():
                            try:
                                num_value = float(value)
                            except ValueError:
                                continue
                        elif isinstance(value, (int, float)):
                            num_value = float(value)
                        else:
                            continue
                        field_stats[field] = field_stats.get(field, {"min": float("inf"), "max": float("-inf")})
                        field_stats[field]["min"] = min(field_stats[field]["min"], num_value)
                        field_stats[field]["max"] = max(field_stats[field]["max"], num_value)
                    except (ValueError, TypeError):
                        continue

        # Normaliser les données (Min-Max uniquement)
        patients = patients_collection.find({"DoctorId": doctor_id})
        patients_updated = 0
        for patient in patients:
            patient_id = patient.get("patient_id")
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            normalized_data = []

            for row in donnees_cliniques:
                normalized_row = row.copy()
                for field in row:
                    if field.lower() == "index":  # Ignorer le champ index
                        continue
                    if field in field_stats and row[field] is not None and row[field] != "":
                        try:
                            if isinstance(row[field], str) and row[field].strip():
                                try:
                                    value = float(row[field])
                                except ValueError:
                                    continue
                            elif isinstance(row[field], (int, float)):
                                value = float(row[field])
                            else:
                                continue
                            min_max_value = (value - field_stats[field]["min"]) / (field_stats[field]["max"] - field_stats[field]["min"]) if field_stats[field]["max"] != field_stats[field]["min"] else 0
                            normalized_row[field] = round(min_max_value, 4)
                        except (ValueError, TypeError):
                            pass
                normalized_data.append(normalized_row)

            result = patients_collection.update_one(
                {"patient_id": patient_id, "DoctorId": doctor_id},
                {"$set": {"Donnees_cliniques_pretraitees": normalized_data}}
            )
            if result.modified_count > 0:
                patients_updated += 1

        if patients_updated == 0:
            return jsonify({"message": "Aucun patient trouvé ou modifié pour ce DoctorId"}), HTTPStatus.OK

        return jsonify({"message": f"Dataset normalized successfully for {patients_updated} patients"}), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error during normalization: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR