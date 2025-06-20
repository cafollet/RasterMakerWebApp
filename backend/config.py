import os
import logging
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate


# Create Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ['http://localhost:5173', "http://localhost:3000", "https://rastermakerwebapp-frontend.onrender.com"]}})

# Configure comprehensive logging
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""
    
    grey = "\x1b[38;21m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    red = "\x1b[31m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    
    FORMATS = {
        logging.DEBUG: grey + "%(asctime)s - [DEBUG] - %(name)s - %(message)s" + reset,
        logging.INFO: green + "%(asctime)s - [INFO] - %(name)s - %(message)s" + reset,
        logging.WARNING: yellow + "%(asctime)s - [WARNING] - %(name)s - %(message)s" + reset,
        logging.ERROR: red + "%(asctime)s - [ERROR] - %(name)s - %(message)s" + reset,
        logging.CRITICAL: bold_red + "%(asctime)s - [CRITICAL] - %(name)s - %(message)s" + reset
    }
    
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)

# Configure root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# Remove existing handlers
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Console handler with colored output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(ColoredFormatter())
root_logger.addHandler(console_handler)

# File handler for persistent logs
file_handler = logging.FileHandler('app.log', mode='a')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    '%(asctime)s - [%(levelname)s] - %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(file_formatter)
root_logger.addHandler(file_handler)

# Create specific loggers for different modules
main_logger = logging.getLogger('main')
db_logger = logging.getLogger('database')
api_logger = logging.getLogger('api')
processing_logger = logging.getLogger('processing')

# Log application startup
main_logger.info("="*60)
main_logger.info("APPLICATION STARTING UP")
main_logger.info("="*60)

# Database configuration
if os.environ.get('DATABASE_URL') is None:
    db_uri = "sqlite:///mydatabase.db"
    db_logger.info("Using SQLite database: mydatabase.db")
else:
    db_uri = os.environ.get('DATABASE_URL')
    db_logger.info(f"Using PostgreSQL database from environment variable")

app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

db_logger.info("Database and migration initialized successfully")
