
from flask import Flask
from flask_pymongo import PyMongo
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask_mail import Mail
from auth.routes import auth_bp
from patient.routes import patients_bp
from statistique.routes import statistique_bp
from doctor.routes import Doctor_bp
from Pretraitment.routes import pretraitement_bp
# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
#app.config["MONGO_URI"] = os.getenv("MONGO_URI", "mongodb+srv://hanibenjemaa39:hani1234@cancerv2.keq4got.mongodb.net/cancer_db?retryWrites=true&w=majority&appName=cancerV2")
app.config["MONGO_URI"] = os.getenv("MONGO_URI","mongodb+srv://hanibenjemaa39:hani1234@cancerv3.cnjbfhn.mongodb.net/?retryWrites=true&w=majority&appName=cancerV3")
# app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "your-secure-jwt-secret-key")
# app.config["MAIL_SERVER"] = "smtp.gmail.com"
# app.config["MAIL_PORT"] = 465
# app.config["MAIL_USE_SSL"] = True
# app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "habj0023@gmail.com")
# app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "gkvp qqqh voju vixj")
# app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "habj0023@gmail.com")

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'habj0023@gmail.com')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'gkvp qqqh voju vixj')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'habj0023@gmail.com')
app.config['MAIL_MAX_EMAILS'] = None
app.config['MAIL_ASCII_ATTACHMENTS'] = False
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "your-secure-jwt-secret-key")
# SECRET_KEY = os.getenv('JWT_SECRET_KEY')
# Initialize extensions
mail = Mail(app)
mongo = PyMongo(app)
CORS(app)

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(patients_bp, url_prefix='/patients')
app.register_blueprint(statistique_bp, url_prefix='/Statistique')
app.register_blueprint(Doctor_bp, url_prefix='/doctors')
app.register_blueprint(pretraitement_bp, url_prefix='/pretraitment')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)