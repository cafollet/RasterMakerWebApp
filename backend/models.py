from config import db
import json

class RasterLayer(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(50), unique = True)
    filename = db.Column(db.String(100))
    col_weights = db.Column(db.String(100))
    geom_x = db.Column(db.String(100))
    geom_y = db.Column(db.String(100))
    in_csv_data = db.Column(db.LargeBinary)
    out_img_data = db.Column(db.LargeBinary)  # Layer Image file data
    out_json_data = db.Column(db.Text)  # Layer Image json index
    def __init__(self, filename, col_weights, title, geom_y, geom_x, in_csv_data, out_img_data, out_json_data):
        self.title = title
        self.filename = filename
        self.col_weights = json.dumps(col_weights)
        self.geom_y = geom_y
        self.geom_x = geom_x
        self.in_csv_data = in_csv_data
        self.out_img_data = out_img_data
        self.out_json_data = out_json_data
    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "colWeights": self.col_weights,
            "geomX": self.geom_x,
            "geomY": self.geom_y
        }