from config import db, db_logger
import logging

# Set up logger for this module
logger = logging.getLogger('database.models')


class RasterLayer(db.Model):
    """Model for storing raster layer data"""
    
    __tablename__ = 'raster_layers'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    col_weights = db.Column(db.Text, nullable=False)  # JSON string
    title = db.Column(db.String(255), nullable=False)
    geom_y = db.Column(db.String(100), nullable=False)
    geom_x = db.Column(db.String(100), nullable=False)
    in_csv_data = db.Column(db.LargeBinary, nullable=False)
    out_img_data = db.Column(db.LargeBinary, nullable=False)
    out_json_data = db.Column(db.Text, nullable=False)

    def __init__(self, filename, col_weights, title, geom_y, geom_x, in_csv_data, out_img_data, out_json_data):
        """Initialize a new RasterLayer"""
        self.filename = filename
        self.col_weights = str(col_weights).replace("'", "\"")
        self.title = title
        self.geom_y = geom_y
        self.geom_x = geom_x
        self.in_csv_data = in_csv_data
        self.out_img_data = out_img_data
        self.out_json_data = out_json_data
        
        logger.info(f"Created new RasterLayer instance: title='{title}', filename='{filename}'")

    def to_json(self):
        """Convert RasterLayer to JSON representation"""
        try:
            json_data = {
                "id": self.id,
                "filename": self.filename,
                "col_weights": self.col_weights,
                "title": self.title,
                "geom_y": self.geom_y,
                "geom_x": self.geom_x
            }
            logger.debug(f"Converted RasterLayer {self.id} to JSON")
            return json_data
        except Exception as e:
            logger.error(f"Failed to convert RasterLayer {self.id} to JSON: {str(e)}")
            raise

    def __repr__(self):
        """String representation of RasterLayer"""
        return f"<RasterLayer(id={self.id}, title='{self.title}', filename='{self.filename}')>"

    def __str__(self):
        """Human-readable string representation"""
        return f"RasterLayer: {self.title} (ID: {self.id})"


# Log model registration
logger.info("RasterLayer model registered successfully")
db_logger.info("Database models loaded")
