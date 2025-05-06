from flask import Blueprint, jsonify
from http import HTTPStatus
from dataset import patients_collection,users_collection
import statistics
statistique_bp = Blueprint('statistique', __name__)

@statistique_bp.route("/fill-rate", methods=["GET"])
def get_fill_rate():
    try:
        # Initialize counters
        total_fields = 0
        filled_fields = 0
        field_counts = {}  # Per-field counts {field: {total: int, filled: int}}
        total_patients = 0
        total_rows = 0

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            
            for row in donnees_cliniques:
                total_rows += 1
                # If row is a dict (direct row), process it
                if isinstance(row, dict) and not row.get("rows"):
                    fields = row.keys()
                    for field in fields:
                        # Initialize field counters if not present
                        if field not in field_counts:
                            field_counts[field] = {"total": 0, "filled": 0}
                        
                        field_counts[field]["total"] += 1
                        total_fields += 1
                        
                        # Check if field is filled (not null, not empty string)
                        value = row.get(field)
                        if value is not None and value != "":
                            field_counts[field]["filled"] += 1
                            filled_fields += 1
                
                # If row has a nested "rows" array (from previous backend versions)
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        fields = sub_row.keys()
                        for field in fields:
                            if field not in field_counts:
                                field_counts[field] = {"total": 0, "filled": 0}
                            
                            field_counts[field]["total"] += 1
                            total_fields += 1
                            
                            value = sub_row.get(field)
                            if value is not None and value != "":
                                field_counts[field]["filled"] += 1
                                filled_fields += 1

        # Calculate overall fill rate
        overall_fill_rate = (filled_fields / total_fields * 100) if total_fields > 0 else 0

        # Calculate per-field fill rates
        field_fill_rates = {
            field: {
                "fill_rate": (counts["filled"] / counts["total"] * 100) if counts["total"] > 0 else 0,
                "filled": counts["filled"],
                "total": counts["total"]
            }
            for field, counts in field_counts.items()
        }

        # Prepare response
        response = {
            "overall_fill_rate": round(overall_fill_rate, 2),
            "field_fill_rates": {
                field: {
                    "fill_rate": round(data["fill_rate"], 2),
                    "filled": data["filled"],
                    "total": data["total"]
                }
                for field, data in field_fill_rates.items()
            },
            "total_patients": total_patients,
            "total_rows": total_rows,
            "total_fields": total_fields,
            "filled_fields": filled_fields
        }
        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating fill rate: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/view-occurrences", methods=["GET"])
def get_view_occurrences():
    try:
        # Initialize counters
        view_counts = {}
        total_patients = 0
        total_rows = 0

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])

            for row in donnees_cliniques:
                total_rows += 1
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    view = row.get("View", "unknown")
                    if view == "":
                        view = "unknown"
                    view_counts[view] = view_counts.get(view, 0) + 1
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        view = sub_row.get("View", "unknown")
                        if view == "":
                            view = "unknown"
                        view_counts[view] = view_counts.get(view, 0) + 1

        # Prepare response
        response = {
            "view_occurrences": view_counts,
            "total_patients": total_patients,
            "total_rows": total_rows
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating view occurrences: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@statistique_bp.route("/study-distribution", methods=["GET"])
def get_study_distribution():
    try:
        # Initialize counters
        study_distribution = {}  # Maps number of studies to patient count
        total_patients = 0
        total_studies = 0
        study_uids = set()  # Track unique StudyUIDs across all patients

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            patient_study_uids = set()  # Unique StudyUIDs for this patient

            for row in donnees_cliniques:
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    study_uid = row.get("StudyUID")
                    if study_uid and study_uid != "":
                        patient_study_uids.add(study_uid)
                        study_uids.add(study_uid)
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        study_uid = sub_row.get("StudyUID")
                        if study_uid and study_uid != "":
                            patient_study_uids.add(study_uid)
                            study_uids.add(study_uid)

            # Count studies for this patient
            study_count = len(patient_study_uids)
            if study_count > 0:  # Only count patients with at least one valid study
                study_distribution[str(study_count)] = study_distribution.get(str(study_count), 0) + 1

        # Calculate total studies
        total_studies = len(study_uids)

        # Prepare response
        response = {
            "study_distribution": study_distribution,
            "total_patients": total_patients,
            "total_studies": total_studies
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating study distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    
@statistique_bp.route("/column-statistics", methods=["GET"])
def get_column_statistics():
    try:
        column_values = {}
        total_patients = 0
        total_rows = 0
        patients = patients_collection.find()
        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                total_rows += 1
                if isinstance(row, dict) and not row.get("rows"):
                    for field, value in row.items():
                        if value is not None and value != "":
                            try:
                                num_value = float(value)
                                if field not in column_values:
                                    column_values[field] = []
                                column_values[field].append(num_value)
                            except (ValueError, TypeError):
                                pass
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        for field, value in sub_row.items():
                            if value is not None and value != "":
                                try:
                                    num_value = float(value)
                                    if field not in column_values:
                                        column_values[field] = []
                                    column_values[field].append(num_value)
                                except (ValueError, TypeError):
                                    pass
        column_statistics = {}
        for field, values in column_values.items():
            if len(values) > 0:
                try:
                    mean = statistics.mean(values)
                    std_dev = statistics.stdev(values) if len(values) > 1 else 0
                    max_val = max(values)
                    min_val = min(values)
                    column_statistics[field] = {
                        "mean": round(mean, 2),
                        "std_dev": round(std_dev, 2),
                        "max": round(max_val, 2),
                        "min": round(min_val, 2)
                    }
                except Exception as e:
                    print(f"Error calculating stats for {field}: {str(e)}")
        response = {
            "column_statistics": column_statistics,
            "total_patients": total_patients,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating column statistics: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/class-distribution", methods=["GET"])
def get_class_distribution():
    try:
        # Initialize class counts and total rows
        class_counts = {}
        total_rows = 0

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])

            for row in donnees_cliniques:
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    class_value = row.get("Class", "unknown")  # Default to "unknown" for missing/empty
                    if class_value == "":
                        class_value = "unknown"
                    class_counts[class_value] = class_counts.get(class_value, 0) + 1
                    total_rows += 1
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        class_value = sub_row.get("Class", "unknown")  # Default to "unknown" for missing/empty
                        if class_value == "":
                            class_value = "unknown"
                        class_counts[class_value] = class_counts.get(class_value, 0) + 1
                        total_rows += 1

        # Prepare response
        response = {
            "class_counts": class_counts,
            "total_rows": total_rows
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/class-percentege", methods=["GET"])
def get_class_percentege():
    try:
        # Initialize counts and total rows
        class_counts = {}
        total_rows = 0

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])

            for row in donnees_cliniques:
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    # Process Class
                    class_value = row.get("Class", "unknown")
                    if class_value == "":
                        class_value = "unknown"
                    class_counts[class_value] = class_counts.get(class_value, 0) + 1
                    total_rows += 1
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        # Process Class
                        class_value = sub_row.get("Class", "unknown")
                        if class_value == "":
                            class_value = "unknown"
                        class_counts[class_value] = class_counts.get(class_value, 0) + 1
                        total_rows += 1

        # Calculate percentages
        class_distribution = {
            key: {
                "count": count,
                "percentage": round((count / total_rows * 100) if total_rows > 0 else 0, 2)
            }
            for key, count in class_counts.items()
        }

        # Prepare response
        response = {
            "class_distribution": class_distribution,
            "total_rows": total_rows
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/view-percentage", methods=["GET"])
def get_view_percentage():

    try:
        # Initialize counts and total rows
        view_counts = {}
        total_rows = 0

        # Query all patients
        patients = patients_collection.find()

        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])

            for row in donnees_cliniques:
                # Handle direct row structure
                if isinstance(row, dict) and not row.get("rows"):
                    # Process View
                    view_value = row.get("View", "unknown")
                    if view_value == "":
                        view_value = "unknown"
                    view_counts[view_value] = view_counts.get(view_value, 0) + 1
                    total_rows += 1
                
                # Handle nested rows structure
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        # Process View
                        view_value = sub_row.get("View", "unknown")
                        if view_value == "":
                            view_value = "unknown"
                        view_counts[view_value] = view_counts.get(view_value, 0) + 1
                        total_rows += 1

        # Calculate percentages
        view_distribution = {
            key: {
                "count": count,
                "percentage": round((count / total_rows * 100) if total_rows > 0 else 0, 2)
            }
            for key, count in view_counts.items()
        }

        # Prepare response
        response = {
            "view_distribution": view_distribution,
            "total_rows": total_rows
        }

        return jsonify(response), HTTPStatus.OK

    except Exception as e:
        return jsonify({"message": f"Error calculating view distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/doctor-count', methods=['GET'])
def get_doctor_count():
    try:
        # Count the number of documents in users_collection with user_type 'doctor'
        count = users_collection.count_documents({'user_type': {'$regex': '^doctor$', '$options': 'i'}})
        return jsonify({
            "message": "Doctor count retrieved successfully",
            "doctor_count": count
        }), HTTPStatus.OK
    except Exception as e:
        # Log the error internally (logging not shown for brevity)
        return jsonify({
            "message": "Error retrieving doctor count"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/patient-count', methods=['GET'])
def get_patient_count():
    try:
        # Compter le nombre total de documents dans patients_collection
        count = patients_collection.count_documents({})
        return jsonify({
            "message": "Patient count retrieved",
            "patient_count": count
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({
            "message": "Error retrieving patient count",
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@statistique_bp.route('/study-count', methods=['GET'])
def get_study_count():
    try:
        # Use aggregation to count unique StudyUID values
        pipeline = [
            # Unwind Donnees_cliniques_brutes array
            {"$unwind": "$Donnees_cliniques_brutes"},
            # Unwind nested rows array, if present
            {"$unwind": {
                "path": "$Donnees_cliniques_brutes.rows",
                "preserveNullAndEmptyArrays": True
            }},
            # Project StudyUID from both direct and nested structures
            {"$project": {
                "StudyUID": {
                    "$cond": [
                        {"$ifNull": ["$Donnees_cliniques_brutes.rows", False]},
                        "$Donnees_cliniques_brutes.rows.StudyUID",
                        "$Donnees_cliniques_brutes.StudyUID"
                    ]
                }
            }},
            # Filter out documents with missing or empty StudyUID
            {"$match": {
                "StudyUID": {"$exists": True, "$ne": ""}
            }},
            # Group to get unique StudyUIDs
            {"$group": {
                "_id": "$StudyUID"
            }},
            # Count the unique StudyUIDs
            {"$group": {
                "_id": 'null',
                "study_count": {"$sum": 1}
            }},
            # Project the final count
            {"$project": {
                "_id": 0,
                "study_count": 1
            }}
        ]

        # Execute aggregation
        result = list(patients_collection.aggregate(pipeline))
        study_count = result[0]["study_count"] if result else 0

        return jsonify({
            "message": "Study count retrieved successfully",
            "study_count": study_count
        }), HTTPStatus.OK

    except Exception as e:
        # Log the error internally (logging not shown for brevity)
        return jsonify({
            "message": "Error retrieving study count"
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    