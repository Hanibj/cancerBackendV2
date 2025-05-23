
from flask import Blueprint, jsonify
from http import HTTPStatus
from dataset import patients_collection, users_collection
import statistics
import logging
from datetime import datetime, timedelta
from pymongo.errors import PyMongoError
from dateutil.relativedelta import relativedelta
statistique_bp = Blueprint('statistique', __name__)
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

@statistique_bp.route("/fill-rate/<matricule>", methods=["GET"])
def get_fill_rate(matricule):
    print("matricule", matricule)
    try:
        total_fields = 0
        filled_fields = 0
        field_counts = {}
        total_patients = 0
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                total_rows += 1
                if isinstance(row, dict) and not row.get("rows"):
                    fields = row.keys()
                    for field in fields:
                        if field not in field_counts:
                            field_counts[field] = {"total": 0, "filled": 0}
                        field_counts[field]["total"] += 1
                        total_fields += 1
                        value = row.get(field)
                        if value is not None and value != "":
                            field_counts[field]["filled"] += 1
                            filled_fields += 1
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
        overall_fill_rate = (filled_fields / total_fields * 100) if total_fields > 0 else 0
        field_fill_rates = {
            field: {
                "fill_rate": (counts["filled"] / counts["total"] * 100) if counts["total"] > 0 else 0,
                "filled": counts["filled"],
                "total": counts["total"]
            }
            for field, counts in field_counts.items()
        }
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

@statistique_bp.route("/view-occurrences/<matricule>", methods=["GET"])
def get_view_occurrences(matricule):
    try:
        view_counts = {}
        total_patients = 0
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                total_rows += 1
                if isinstance(row, dict) and not row.get("rows"):
                    view = row.get("View", "unknown")
                    if view == "":
                        view = "unknown"
                    view_counts[view] = view_counts.get(view, 0) + 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        view = sub_row.get("View", "unknown")
                        if view == "":
                            view = "unknown"
                        view_counts[view] = view_counts.get(view, 0) + 1
        response = {
            "view_occurrences": view_counts,
            "total_patients": total_patients,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating view occurrences: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/study-distribution/<matricule>", methods=["GET"])
def get_study_distribution(matricule):
    try:
        study_distribution = {}
        total_patients = 0
        total_studies = 0
        study_uids = set()
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            patient_study_uids = set()
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    study_uid = row.get("StudyUID")
                    if study_uid and study_uid != "":
                        patient_study_uids.add(study_uid)
                        study_uids.add(study_uid)
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        study_uid = sub_row.get("StudyUID")
                        if study_uid and study_uid != "":
                            patient_study_uids.add(study_uid)
                            study_uids.add(study_uid)
            study_count = len(patient_study_uids)
            if study_count > 0:
                study_distribution[str(study_count)] = study_distribution.get(str(study_count), 0) + 1
        total_studies = len(study_uids)
        response = {
            "study_distribution": study_distribution,
            "total_patients": total_patients,
            "total_studies": total_studies
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating study distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/column-statistics/<matricule>", methods=["GET"])
def get_column_statistics(matricule):
    try:
        column_values = {}
        total_patients = 0
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
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

@statistique_bp.route("/class-distribution/<matricule>", methods=["GET"])
def get_class_distribution(matricule):
    try:
        class_counts = {}
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    class_value = row.get("Class", "unknown")
                    if class_value == "":
                        class_value = "unknown"
                    class_counts[class_value] = class_counts.get(class_value, 0) + 1
                    total_rows += 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        class_value = sub_row.get("Class", "unknown")
                        if class_value == "":
                            class_value = "unknown"
                        class_counts[class_value] = class_counts.get(class_value, 0) + 1
                        total_rows += 1
        response = {
            "class_counts": class_counts,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/class-percentege/<matricule>", methods=["GET"])
def get_class_percentege(matricule):
    try:
        class_counts = {}
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    class_value = row.get("Class", "unknown")
                    if class_value == "":
                        class_value = "unknown"
                    class_counts[class_value] = class_counts.get(class_value, 0) + 1
                    total_rows += 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        class_value = sub_row.get("Class", "unknown")
                        if class_value == "":
                            class_value = "unknown"
                        class_counts[class_value] = class_counts.get(class_value, 0) + 1
                        total_rows += 1
        class_distribution = {
            key: {
                "count": count,
                "percentage": round((count / total_rows * 100) if total_rows > 0 else 0, 2)
            }
            for key, count in class_counts.items()
        }
        response = {
            "class_distribution": class_distribution,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/view-percentage/<matricule>", methods=["GET"])
def get_view_percentage(matricule):
    try:
        view_counts = {}
        total_rows = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    view_value = row.get("View", "unknown")
                    if view_value == "":
                        view_value = "unknown"
                    view_counts[view_value] = view_counts.get(view_value, 0) + 1
                    total_rows += 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        view_value = sub_row.get("View", "unknown")
                        if view_value == "":
                            view_value = "unknown"
                        view_counts[view_value] = view_counts.get(view_value, 0) + 1
                        total_rows += 1
        view_distribution = {
            key: {
                "count": count,
                "percentage": round((count / total_rows * 100) if total_rows > 0 else 0, 2)
            }
            for key, count in view_counts.items()
        }
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
        count = users_collection.count_documents({'user_type': {'$regex': '^doctor$', '$options': 'i'}})
        return jsonify({
            "message": "Doctor count retrieved successfully",
            "doctor_count": count
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({
            "message": "Error retrieving doctor count"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/patient-count', methods=['GET'])
def get_patient_count():
    try:
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
@statistique_bp.route('/patient-count/<matricule>', methods=['GET'])
def get_patient_count_by_doctor(matricule):
    try:
        count = patients_collection.count_documents({"DoctorId":matricule})
        return jsonify({
            "message": "Patient count retrieved",
            "patient_count": count
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({
            "message": "Error retrieving patient count",
            "error": str(e)
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/study-count/<matricule>', methods=['GET'])
def get_study_count(matricule):
    try:
        pipeline = [
            {"$match": {"DoctorId": matricule}},
            {"$unwind": "$Donnees_cliniques_brutes"},
            {"$unwind": {
                "path": "$Donnees_cliniques_brutes.rows",
                "preserveNullAndEmptyArrays": True
            }},
            {"$project": {
                "StudyUID": {
                    "$cond": [
                        {"$ifNull": ["$Donnees_cliniques_brutes.rows", False]},
                        "$Donnees_cliniques_brutes.rows.StudyUID",
                        "$Donnees_cliniques_brutes.StudyUID"
                    ]
                }
            }},
            {"$match": {
                "StudyUID": {"$exists": True, "$ne": ""}
            }},
            {"$group": {
                "_id": "$StudyUID"
            }},
            {"$group": {
                "_id": 'null',
                "study_count": {"$sum": 1}
            }},
            {"$project": {
                "_id": 0,
                "study_count": 1
            }}
        ]
        result = list(patients_collection.aggregate(pipeline))
        study_count = result[0]["study_count"] if result else 0
        return jsonify({
            "message": "Study count retrieved successfully",
            "study_count": study_count
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({
            "message": "Error retrieving study count"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/images-per-doctor/<matricule>', methods=['GET'])
def get_images_per_doctor(matricule):
    try:
        total_patients = 0
        total_images = 0
        patients = patients_collection.find({"DoctorId": matricule})
        for patient in patients:
            total_patients += 1
            images = patient.get("Images_originales", [])
            image_count = len(images) if isinstance(images, list) else 0
            total_images += image_count
        response = {
            "doctor_id": matricule,
            "image_count": total_images,
            "total_patients": total_patients
        }
        return jsonify(response), HTTPStatus.OK
    except PyMongoError as e:
        return jsonify({"message": f"Database error calculating images per doctor: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error calculating images per doctor: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/user-count/', methods=['GET'])
def get_user_count():
    try:
        count = users_collection.count_documents(
            {'user_type': {'$ne': 'Admin'}},
            collation={'locale': 'en', 'strength': 2}
        )
        return jsonify({
            "message": "Non-Admin user count retrieved successfully",
            "user_count": count
        }), HTTPStatus.OK
    except Exception as e:
        return jsonify({
            "message": "Error retrieving user count"
        }), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/user-type-percentages', methods=['GET'])
def get_user_type_percentages():
    try:
        total_non_admin = users_collection.count_documents(
            {'user_type': {'$ne': 'Admin'}},
            collation={'locale': 'en', 'strength': 2}
        )
        if total_non_admin == 0:
            return jsonify({
                "message": "No non-Admin users found",
                "visitor_percentages": {},
                "doctor_percentage": 0
            }), HTTPStatus.OK
        doctor_count = users_collection.count_documents(
            {'user_type': 'doctor'},
            collation={'locale': 'en', 'strength': 2}
        )
        visitor_count = users_collection.count_documents(
            {'user_type': 'visitor'},
            collation={'locale': 'en', 'strength': 2}
        )
        doctor_percentage = (doctor_count / total_non_admin * 100) if total_non_admin > 0 else 0
        visitor_percentages_Data = (visitor_count / total_non_admin * 100) if total_non_admin > 0 else 0
        visitor_pipeline = [
            {'$match': {'user_type': 'visitor'}},
            {'$group': {'_id': '$specialite', 'count': {'$sum': 1}}},
            {'$project': {'specialite': '$_id', 'count': 1, '_id': 0}}
        ]
        visitor_data = list(users_collection.aggregate(
            visitor_pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))
        total_visitors = sum(item['count'] for item in visitor_data)
        visitor_percentages = {}
        if total_visitors > 0:
            for item in visitor_data:
                specialite = item['specialite']
                percentage = (item['count'] / total_visitors * 100)
                visitor_percentages[specialite] = round(percentage, 2)
        return jsonify({
            "message": "User type percentages retrieved successfully",
            "visitor_percentages": visitor_percentages,
            "visitor_percentages_Data": visitor_percentages_Data,
            "doctor_percentage": round(doctor_percentage, 2)
        }), HTTPStatus.OK
    except PyMongoError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error retrieving percentages: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route('/signup-statistics', methods=['GET'])
def get_signup_statistics():
    try:
        total_non_admin = users_collection.count_documents(
            {'user_type': {'$ne': 'Admin'}},
            collation={'locale': 'en', 'strength': 2}
        )
        if total_non_admin == 0:
            return jsonify({
                "message": "No non-Admin users found",
                "total_users": 0,
                "user_type_percentages": {"visitor": 0, "doctor": 0},
                "visitor_specialty_percentages": {},
                "signup_trends": {
                    "by_day": {},
                    "by_month": {},
                    "by_year": {}
                }
            }), HTTPStatus.OK
        user_type_counts = users_collection.aggregate([
            {'$match': {'user_type': {'$in': ['visitor', 'doctor']}}},
            {'$group': {'_id': '$user_type', 'count': {'$sum': 1}}},
            {'$project': {'user_type': '$_id', 'count': 1, '_id': 0}}
        ], collation={'locale': 'en', 'strength': 2})
        user_type_percentages = {"visitor": 0, "doctor": 0}
        for item in user_type_counts:
            user_type = item['user_type'].lower()
            user_type_percentages[user_type] = round((item['count'] / total_non_admin * 100), 2)
        visitor_specialty_pipeline = [
            {'$match': {'user_type': 'visitor'}},
            {'$group': {'_id': '$specialite', 'count': {'$sum': 1}}},
            {'$project': {'specialite': '$_id', 'count': 1, '_id': 0}}
        ]
        visitor_specialty_data = list(users_collection.aggregate(
            visitor_specialty_pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))
        total_visitors = sum(item['count'] for item in visitor_specialty_data)
        visitor_specialty_percentages = {}
        if total_visitors > 0:
            for item in visitor_specialty_data:
                specialty = item['specialite'] or 'Unknown'
                percentage = (item['count'] / total_visitors * 100)
                visitor_specialty_percentages[specialty] = round(percentage, 2)
        signup_trends_by_day_pipeline = [
            {'$match': {'user_type': {'$ne': 'Admin'}}},
            {'$group': {
                '_id': {
                    '$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$project': {'day': '$_id', 'count': 1, '_id': 0}}
        ]
        signup_trends_by_day_data = list(users_collection.aggregate(
            signup_trends_by_day_pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))
        signup_trends_by_day = {item['day']: item['count'] for item in signup_trends_by_day_data}
        signup_trends_by_month_pipeline = [
            {'$match': {'user_type': {'$ne': 'Admin'}}},
            {'$group': {
                '_id': {
                    '$dateToString': {'format': '%Y-%m', 'date': '$created_at'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$project': {'month': '$_id', 'count': 1, '_id': 0}}
        ]
        signup_trends_by_month_data = list(users_collection.aggregate(
            signup_trends_by_month_pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))
        signup_trends_by_month = {item['month']: item['count'] for item in signup_trends_by_month_data}
        signup_trends_by_year_pipeline = [
            {'$match': {'user_type': {'$ne': 'Admin'}}},
            {'$group': {
                '_id': {
                    '$dateToString': {'format': '%Y', 'date': '$created_at'}
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id': 1}},
            {'$project': {'year': '$_id', 'count': 1, '_id': 0}}
        ]
        signup_trends_by_year_data = list(users_collection.aggregate(
            signup_trends_by_year_pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))
        signup_trends_by_year = {item['year']: item['count'] for item in signup_trends_by_year_data}
        Doctor_Count=users_collection.count_documents({"user_type":"doctor"})
        Visitor_Count=users_collection.count_documents({"user_type":"visitor"})
        return jsonify({
            "message": "Signup statistics retrieved successfully",
            "total_users": total_non_admin,
            "user_type_percentages": user_type_percentages,
            "visitor_specialty_percentages": visitor_specialty_percentages,
            
            "signup_trends": {
                "by_day": signup_trends_by_day,
                "by_month": signup_trends_by_month,
                "by_year": signup_trends_by_year
            },
            "Doctor_Count":Doctor_Count,
            "Visitor_Count":Visitor_Count


        }), HTTPStatus.OK
    except PyMongoError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error retrieving signup statistics: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@statistique_bp.route('/signup-growth/<period>', methods=['GET'])

def get_signup_growth(period):
    """
    Calculate the signup growth rate for 'visitor' and 'doctor' user types by period.
    :param period: 'daily', 'monthly', or 'yearly'
    :return: JSON response with growth rates and signup counts
    """
    try:
        # Validate period parameter
        valid_periods = ['daily', 'monthly', 'yearly']
        if period not in valid_periods:
            return jsonify({
                "message": f"Invalid period. Must be one of {valid_periods}"
            }), HTTPStatus.BAD_REQUEST

        # Define date format based on period
        date_formats = {
            'daily': '%Y-%m-%d',
            'monthly': '%Y-%m',
            'yearly': '%Y'
        }
        date_format = date_formats[period]

        # Aggregation pipeline to group signups by user_type and period
        pipeline = [
            {
                '$match': {
                    'user_type': {'$in': ['visitor', 'doctor']},
                    'created_at': {'$exists': True}
                }
            },
            {
                '$group': {
                    '_id': {
                        'user_type': '$user_type',
                        'period': {
                            '$dateToString': {
                                'format': date_format,
                                'date': '$created_at'
                            }
                        }
                    },
                    'count': {'$sum': 1}
                }
            },
            {
                '$sort': {
                    '_id.period': 1,
                    '_id.user_type': 1
                }
            },
            {
                '$project': {
                    'user_type': '$_id.user_type',
                    'period': '$_id.period',
                    'count': 1,
                    '_id': 0
                }
            }
        ]

        # Execute aggregation with case-insensitive collation
        signup_data = list(users_collection.aggregate(
            pipeline,
            collation={'locale': 'en', 'strength': 2}
        ))

        if not signup_data:
            return jsonify({
                "message": "No signup data found for visitor or doctor user types",
                "growth_rates": {"visitor": [], "doctor": []},
                "total_signups": {"visitor": 0, "doctor": 0}
            }), HTTPStatus.OK

        # Organize data by user type and period
        visitor_data = {}
        doctor_data = {}
        for item in signup_data:
            user_type = item['user_type'].lower()
            if user_type == 'visitor':
                visitor_data[item['period']] = item['count']
            elif user_type == 'doctor':
                doctor_data[item['period']] = item['count']

        # Generate all periods between min and max to handle gaps
        def generate_periods(start_period, end_period, period_type):
            try:
                start_date = datetime.strptime(start_period, date_formats[period_type])
                end_date = datetime.strptime(end_period, date_formats[period_type])
            except ValueError as e:
                logger.error(f"Error parsing periods: {str(e)}")
                return []
            periods = []
            current_date = start_date
            while current_date <= end_date:
                periods.append(current_date.strftime(date_formats[period_type]))
                if period_type == 'daily':
                    current_date += timedelta(days=1)
                elif period_type == 'monthly':
                    current_date += relativedelta(months=1)
                else:  # yearly
                    current_date += relativedelta(years=1)
            return periods

        # Calculate growth rates
        def calculate_growth_rates(data, period_type):
            periods = sorted(data.keys())
            if not periods:
                return []
            all_periods = generate_periods(min(periods), max(periods), period_type)
            growth_rates = []
            for i in range(1, len(all_periods)):
                current_period = all_periods[i]
                previous_period = all_periods[i - 1]
                current_count = data.get(current_period, 0)
                previous_count = data.get(previous_period, 0)
                if previous_count == 0:
                    growth_rate = 0  # Consider float('inf') if growth from 0 is significant
                else:
                    growth_rate = ((current_count - previous_count) / previous_count * 100)
                growth_rates.append({
                    "period": current_period,
                    "growth_rate": round(growth_rate, 2),
                    "current_count": current_count,
                    "previous_count": previous_count
                })
            return growth_rates

        visitor_growth = calculate_growth_rates(visitor_data, period)
        doctor_growth = calculate_growth_rates(doctor_data, period)

        # Calculate total signups
        total_visitor_signups = sum(visitor_data.values())
        total_doctor_signups = sum(doctor_data.values())

        # Prepare response
        response = {
            "message": f"Signup growth rates for {period} period retrieved successfully",
            "growth_rates": {
                "visitor": visitor_growth,
                "doctor": doctor_growth
            },
            "total_signups": {
                "visitor": total_visitor_signups,
                "doctor": total_doctor_signups
            },
            "period": period
        }

        return jsonify(response), HTTPStatus.OK

    except PyMongoError as e:
        logger.error(f"Database error in signup-growth: {str(e)}")
        return jsonify({
            "message": f"Database error: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        logger.error(f"Error in signup-growth: {str(e)}")
        return jsonify({
            "message": f"Error calculating signup growth: {str(e)}"
        }), HTTPStatus.INTERNAL_SERVER_ERROR


@statistique_bp.route('/imagesCount', methods=['GET'])
def get_images_Count():
    try:
        total_patients = 0
        total_images = 0
        patients = patients_collection.find()
        for patient in patients:
            total_patients += 1
            images = patient.get("Images_originales", [])
            image_count = len(images) if isinstance(images, list) else 0
            total_images += image_count
        response = {
           
            "image_count": total_images,
            "total_patients": total_patients
        }
        return jsonify(response), HTTPStatus.OK
    except PyMongoError as e:
        return jsonify({"message": f"Database error calculating images per doctor: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
    except Exception as e:
        return jsonify({"message": f"Error calculating images per doctor: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/view-occurrences", methods=["GET"])
def get_all_view_occurrences():
    try:
        view_counts = {}
        total_patients = 0
        total_rows = 0
        patients = patients_collection.find()
        
        # Normalization mapping for View values (case-insensitive)
        view_normalization = {
            "rcc": "rcc",
            "lcc": "lcc",
            "rmlo": "rmlo",
            "lmlo": "lmlo"
        }

        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                total_rows += 1
                if isinstance(row, dict) and not row.get("rows"):
                    view = row.get("View", "unknown")
                    if view == "":
                        view = "unknown"
                    # Normalize View value
                    view_lower = view.lower()
                    normalized_view = "unknown"
                    for key in view_normalization:
                        if view_lower.startswith(key):
                            normalized_view = view_normalization[key]
                            break
                    view_counts[normalized_view] = view_counts.get(normalized_view, 0) + 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        view = sub_row.get("View", "unknown")
                        if view == "":
                            view = "unknown"
                        # Normalize View value
                        view_lower = view.lower()
                        normalized_view = "unknown"
                        for key in view_normalization:
                            if view_lower.startswith(key):
                                normalized_view = view_normalization[key]
                                break
                        view_counts[normalized_view] = view_counts.get(normalized_view, 0) + 1

        response = {
            "view_occurrences": view_counts,
            "total_patients": total_patients,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating view occurrences: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
@statistique_bp.route("/study-distribution", methods=["GET"])
def get_all_study_distribution():
    try:
        study_distribution = {}
        total_patients = 0
        total_studies = 0
        study_uids = set()
        patients = patients_collection.find()
        for patient in patients:
            total_patients += 1
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            patient_study_uids = set()
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    study_uid = row.get("StudyUID")
                    if study_uid and study_uid != "":
                        patient_study_uids.add(study_uid)
                        study_uids.add(study_uid)
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        study_uid = sub_row.get("StudyUID")
                        if study_uid and study_uid != "":
                            patient_study_uids.add(study_uid)
                            study_uids.add(study_uid)
            study_count = len(patient_study_uids)
            if study_count > 0:
                study_distribution[str(study_count)] = study_distribution.get(str(study_count), 0) + 1
        total_studies = len(study_uids)
        response = {
            "study_distribution": study_distribution,
            "total_patients": total_patients,
            "total_studies": total_studies
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating study distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

def normalize_class_value(row):
    """Normalize class based on Class column or Cancer, Benign, Normal, Actionnable columns."""
    # Check if Class column exists and is non-empty
    class_value = row.get("Class")
    if class_value and class_value != "":
        class_lower = class_value.lower()
        if class_lower.startswith("cancer"):
            return "cancer"
        if class_lower.startswith("benign"):
            return "benign"
        return "unknown"
    
    # If Class is missing or empty, check alternative columns
    if row.get("Cancer"):
        return "cancer"
    if row.get("Benign"):
        return "benign"
    if row.get("Normal"):
        return "normal"
    if row.get("Actionnable"):
        return "actionnable"
    return "unknown"

@statistique_bp.route("/all_class-distribution", methods=["GET"])
def get_all_class_distribution():
    try:
        class_counts = {}
        total_rows = 0
        patients = patients_collection.find()
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    normalized_class = normalize_class_value(row)
                    class_counts[normalized_class] = class_counts.get(normalized_class, 0) + 1
                    total_rows += 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        normalized_class = normalize_class_value(sub_row)
                        class_counts[normalized_class] = class_counts.get(normalized_class, 0) + 1
                        total_rows += 1
        response = {
            "class_counts": class_counts,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR

@statistique_bp.route("/all-class-percentege", methods=["GET"])
def get_all_class_percentege():
    try:
        class_counts = {}
        total_rows = 0
        patients = patients_collection.find()
        for patient in patients:
            donnees_cliniques = patient.get("Donnees_cliniques_brutes", [])
            for row in donnees_cliniques:
                if isinstance(row, dict) and not row.get("rows"):
                    normalized_class = normalize_class_value(row)
                    class_counts[normalized_class] = class_counts.get(normalized_class, 0) + 1
                    total_rows += 1
                elif isinstance(row, dict) and row.get("rows"):
                    for sub_row in row["rows"]:
                        normalized_class = normalize_class_value(sub_row)
                        class_counts[normalized_class] = class_counts.get(normalized_class, 0) + 1
                        total_rows += 1
        class_distribution = {
            key: {
                "count": count,
                "percentage": round((count / total_rows * 100) if total_rows > 0 else 0, 2)
            }
            for key, count in class_counts.items()
        }
        response = {
            "class_distribution": class_distribution,
            "total_rows": total_rows
        }
        return jsonify(response), HTTPStatus.OK
    except Exception as e:
        return jsonify({"message": f"Error calculating class distribution: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR