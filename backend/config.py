import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ['http://localhost:5173', "http://localhost:3000", "https://rastermakerwebapp-frontend.onrender.com"]}})

# Define main logger
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
main_logger = logging.getLogger(__name__)

# Set path to sql database URI
if os.environ.get('DATABASE_URL') is None:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
