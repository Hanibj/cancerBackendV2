
from flask import Blueprint, request, jsonify, send_file
from http import HTTPStatus
from dataset import patients_collection, db
from gridfs import GridFS
import json
from bson import ObjectId
import io

patients_bp = Blueprint('patients', __name__)
gridfs = GridFS(db)  # Initialize GridFS

def get_next_folder_Number():
    """Génère un folder_Number unique (entier) commençant à 0."""
    last_patiente = patients_collection.find_one(sort=[("FolderNumber", -1)])
    if last_patiente and "FolderNumber" in last_patiente:
        last_folder_Number = last_patiente["FolderNumber"]
        next_folder_Number = last_folder_Number + 1
    else:
        next_folder_Number = 0
    return next_folder_Number

@patients_bp.route("/upload", methods=["POST"])
def upload_file():
    try:
        # Log the incoming request data
        print("Request files:", request.files)
        print("Request form data:", request.form)

        if 'file' not in request.files:
            return jsonify({"message": "Aucun fichier fourni"}), HTTPStatus.BAD_REQUEST
        file = request.files['file']
        patient_id = request.form.get('patient_id')
        file_format = request.form.get('format')

        if not file.filename:
            return jsonify({"message": "Aucun fichier sélectionné"}), HTTPStatus.BAD_REQUEST
        if not patient_id or not file_format:
            return jsonify({"message": "patient_id et format requis"}), HTTPStatus.BAD_REQUEST

        # Validate file content type
        content_type = file.content_type or "application/octet-stream"
        print(f"Uploading file: {file.filename}, content_type: {content_type}")

        # Store file in GridFS with fallback for content_type
        gridfs_id = gridfs.put(
            file,
            filename=file.filename,
            metadata={
                "patient_id": patient_id,
                "format": file_format,
                "content_type": content_type
            }
        )

        return jsonify({"message": "Fichier uploadé avec succès", "gridfs_id": str(gridfs_id)}), HTTPStatus.OK
    except Exception as e:
        print(f"Exception during upload: {str(e)}")  # Detailed exception logging
        return jsonify({"message": f"Erreur lors de l'upload : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/file/<gridfs_id>", methods=["GET"])
def get_file(gridfs_id):
    try:
        file = gridfs.get(ObjectId(gridfs_id))
        return send_file(
            io.BytesIO(file.read()),
            mimetype=file.metadata.get("content_type", "application/octet-stream"),
            as_attachment=True,
            download_name=file.filename
        )
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération du fichier : {str(e)}"}), HTTPStatus.NOT_FOUND

@patients_bp.route("/images/<patient_id>", methods=["GET"])
def get_patient_images(patient_id):
    try:
        patient = patients_collection.find_one({"patient_id": patient_id})
        if not patient:
            return jsonify({"message": "Patient non trouvé"}), HTTPStatus.NOT_FOUND

        images = patient.get("Images_originales", [])
        print(f"Images récupérées pour {patient_id}: {images}")  # Log pour débogage
        return jsonify({"images": images}), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des images : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/add", methods=["POST"])
def add_patient():
    try:
        data = request.get_json()
        if not data or 'patients' not in data:
            return jsonify({"message": "Tableau JSON de patients requis"}), HTTPStatus.BAD_REQUEST

        patients = data['patients']
        print("Données reçues dans /add:", json.dumps(patients, indent=2))  # Log pour débogage

        for patient in patients:
            if not patient.get('patient_id'):
                return jsonify({"message": "Données de patient invalides : patient_id requis"}), HTTPStatus.BAD_REQUEST

            patient_data = {
                "patient_id": patient["patient_id"],
                "DoctorId": patient.get("DoctorId", ""),
                "FolderNumber": get_next_folder_Number(),
                "Images_originales": patient.get("Images_originales", []),
                "Images_pretraitees": patient.get("Images_pretraitees", []),
                "Verite_terrains": patient.get("Verite_terrains", []),
                "Images_augmentees": patient.get("Images_augmentees", []),
                "Donnees_cliniques_brutes": patient.get("Donnees_cliniques_brutes", []),
                "Donnees_cliniques_pretraitees": patient.get("Donnees_cliniques_pretraitees", []),
                "Videos_originales": patient.get("Videos_originales", []),
                "Signaux_originaux": patient.get("Signaux_originaux", []),
                "created_at": patient.get("created_at", "2025-05-03T12:00:00Z")
            }

            print(f"Traitement du patient {patient_data['patient_id']}: Images_originales = {patient_data['Images_originales']}")  # Log pour débogage

            existing_patient = patients_collection.find_one({"patient_id": patient_data["patient_id"]})
            if existing_patient:
                # Merge images
                existing_images = existing_patient.get("Images_originales", [])
                new_images = patient_data["Images_originales"]
                image_set = {tuple(sorted(d.items())) for d in existing_images}
                image_set.update(tuple(sorted(d.items())) for d in new_images)
                patient_data["Images_originales"] = [dict(t) for t in image_set]

                # Merge clinical data
                existing_clinical = existing_patient.get("Donnees_cliniques_brutes", [])
                new_clinical = patient_data["Donnees_cliniques_brutes"]
                clinical_set = {tuple(sorted(d.items())) for d in existing_clinical}
                clinical_set.update(tuple(sorted(d.items())) for d in new_clinical)
                patient_data["Donnees_cliniques_brutes"] = [dict(t) for t in clinical_set]

                # Merge videos
                existing_videos = existing_patient.get("Videos_originales", [])
                new_videos = patient_data["Videos_originales"]
                video_set = {tuple(sorted(d.items())) for d in existing_videos}
                video_set.update(tuple(sorted(d.items())) for d in new_videos)
                patient_data["Videos_originales"] = [dict(t) for t in video_set]

                # Merge signals
                existing_signals = existing_patient.get("Signaux_originaux", [])
                new_signals = patient_data["Signaux_originaux"]
                signal_set = {tuple(sorted(d.items())) for d in existing_signals}
                signal_set.update(tuple(sorted(d.items())) for d in new_signals)
                patient_data["Signaux_originaux"] = [dict(t) for t in signal_set]

                patients_collection.update_one(
                    {"patient_id": patient_data["patient_id"]},
                    {"$set": patient_data}
                )
                print(f"Patient {patient_data['patient_id']} mis à jour: Images_originales = {patient_data['Images_originales']}")  # Log pour débogage
            else:
                patients_collection.insert_one(patient_data)
                print(f"Patient {patient_data['patient_id']} inséré: Images_originales = {patient_data['Images_originales']}")  # Log pour débogage

        return jsonify({"message": "Données des patients ajoutées avec succès"}), HTTPStatus.CREATED

    except json.JSONDecodeError:
        return jsonify({"message": "Format JSON invalide"}), HTTPStatus.BAD_REQUEST
    except Exception as e:
        print(f"Erreur dans /add: {str(e)}")  # Log pour débogage
        return jsonify({"message": f"Erreur lors de l'ajout du patient : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/all", methods=["GET"])
def get_all_patients():
    try:
        normalized = request.args.get("normalized", "false").lower() == "true"
        data_field = "Donnees_cliniques_brutes" 

        all_data = []
        all_fields = set(["FolderNumber"])
        patients = patients_collection.find()

        for patient in patients:
            FolderNumber = patient.get("FolderNumber")
            donnees = patient.get(data_field, [])

            for row in donnees:
                if isinstance(row, dict) and not row.get("rows"):
                    record = {"FolderNumber": FolderNumber}
                    for field, value in row.items():
                        record[field] = value
                        all_fields.add(field)
                    all_data.append(record)
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        record = {"FolderNumber": FolderNumber}
                        for field, value in sub_row.items():
                            record[field] = value
                            all_fields.add(field)
                        all_data.append(record)

        headers = sorted(list(all_fields))
        response = {
            "data": all_data,
            "headers": headers
        }
   
        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des données des patients : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/normalize", methods=["POST"])
def normalize_patients():
    try:
        field_values = {}
        patients = patients_collection.find()

        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    for field, value in row.items():
                        if value is not None and value != "":
                            try:
                                num_value = float(value)
                                if field not in field_values:
                                    field_values[field] = {"min": float("inf"), "max": float("-inf")}
                                field_values[field]["min"] = min(field_values[field]["min"], num_value)
                                field_values[field]["max"] = max(field_values[field]["max"], num_value)
                            except (ValueError, TypeError):
                                pass
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        for field, value in sub_row.items():
                            if value is not None and value != "":
                                try:
                                    num_value = float(value)
                                    if field not in field_values:
                                        field_values[field] = {"min": float("inf"), "max": float("-inf")}
                                    field_values[field]["min"] = min(field_values[field]["min"], num_value)
                                    field_values[field]["max"] = max(field_values[field]["max"], num_value)
                                except (ValueError, TypeError):
                                    pass

        patients = patients_collection.find()
        for patient in patients:
            patient_id = patient.get("patient_id")
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            normalized_data = []

            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    normalized_row = row.copy()
                    for field, value in row.items():
                        if field in field_values and value is not None and value != "":
                            try:
                                num_value = float(value)
                                field_min = field_values[field]["min"]
                                field_max = field_values[field]["max"]
                                if field_max != field_min:
                                    normalized_row[field] = round((num_value - field_min) / (field_max - field_min), 4)
                                else:
                                    normalized_row[field] = 0.0
                            except (ValueError, TypeError):
                                pass
                    normalized_data.append(normalized_row)
                elif isinstance(row, dict) and row.get("rows"):
                    normalized_sub_rows = []
                    for sub_row in row["rows"]:
                        normalized_sub_row = sub_row.copy()
                        for field, value in sub_row.items():
                            if field in field_values and value is not None and value != "":
                                try:
                                    num_value = float(value)
                                    field_min = field_values[field]["min"]
                                    field_max = field_values[field]["max"]
                                    if field_max != field_min:
                                        normalized_sub_row[field] = round((num_value - field_min) / (field_max - field_min), 4)
                                    else:
                                        normalized_sub_row[field] = 0.0
                                except (ValueError, TypeError):
                                    pass
                        normalized_sub_rows.append(normalized_sub_row)
                    normalized_data.append({"file": row.get("file", {}), "rows": normalized_sub_rows})

            patients_collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"Donnees_cliniques_pretraitees": normalized_data}}
            )

        return jsonify({"message": "Dataset normalisé avec succès"}), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Erreur lors de la normalisation du dataset : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/allnormalize", methods=["GET"])
def get_all_patients_normalize():
    try:
        # Initialize data and headers
        all_data = []
        all_fields = []  # Use list to preserve field order

        # Query all patients, preserving natural order
        patients = patients_collection.find()

        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_pretraitees", [])

            for row in donnees_cliniques:
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    # Create a new empty record
                    record = {}
                    # Add all fields from the row
                    for field, value in row.items():
                        record[field] = value
                        if field not in all_fields:
                            all_fields.append(field)  # Add field in order of appearance
                    all_data.append(record)
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        # Create a new empty record
                        record = {}
                        # Add all fields from the sub-row
                        for field, value in sub_row.items():
                            record[field] = value
                            if field not in all_fields:
                                all_fields.append(field)  # Add field in order of appearance
                        all_data.append(record)

        # Prepare response
        response = {
            "data": all_data,
            "headers": all_fields,
            "total_rows": len(all_data)
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error retrieving patient data: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
@patients_bp.route("/all/images", methods=["GET"])
def get_all_patients_images():
    try:
        patients = patients_collection.find()
        patient_images = []

        for patient in patients:
            patient_id = patient.get("patient_id")
            images = patient.get("Images_originales", [])
            patient_images.append({
                "patient_id": patient_id,
                "images": images
            })

        print(f"Images récupérées pour tous les patients: {patient_images}")  # Log pour débogage
        return jsonify({"patients": patient_images}), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des images de tous les patients : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@patients_bp.route("/all-patiente-by-matricule/<DoctorId>", methods=["GET"])
def get_all_patients_by_matricule(DoctorId):
    try:
        normalized = request.args.get("normalized", "false").lower() == "true"
        data_field = "Donnees_cliniques_brutes" 
        
        all_data = []
        all_fields = set(["FolderNumber"])
        patients = patients_collection.find({"DoctorId":DoctorId})
        
        for patient in patients:
            FolderNumber = patient.get("FolderNumber")
            donnees = patient.get(data_field, [])
            print("donnees",donnees)
            for row in donnees:
                if isinstance(row, dict) and not row.get("rows"):
                    record = {"FolderNumber": FolderNumber}
                    for field, value in row.items():
                        record[field] = value
                        all_fields.add(field)
                    all_data.append(record)
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        record = {"FolderNumber": FolderNumber}
                        for field, value in sub_row.items():
                            record[field] = value
                            all_fields.add(field)
                        all_data.append(record)

        headers = sorted(list(all_fields))
        response = {
            "data": all_data,
            "headers": headers
        }
       
        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des données des patients : {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR