import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_migrate import Migrate


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://rastermakerwebapp-frontend.onrender.com"]}})


# Temporary URI
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL')
#"postgresql://rasterlayer_user:1HJakO6qVJe2bl2vMA3GNCOyLRkrdWi5@dpg-d0a6iv0gjchc73bofabg-a/rasterlayer"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)
