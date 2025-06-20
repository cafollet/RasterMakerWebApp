import json
import base64
import logging
import signal
import sys
import gc
import traceback
from waitress import serve
from flask import request, jsonify
from config import app, db, main_logger, api_logger, db_logger
from models import RasterLayer
from io import BytesIO, StringIO
from generate_raster_file import generate_raster_file
from getImage import write_pix_json, convert_to_alpha
from provide_columns import provide_columns


# Configure request logging
@app.before_request
def log_request_info():
    """Log information about incoming requests"""
    api_logger.debug(f"Request: {request.method} {request.path}")
    if request.method in ['POST', 'PUT', 'PATCH']:
        api_logger.debug(f"Request headers: {dict(request.headers)}")
        if request.is_json:
            api_logger.debug(f"Request JSON: {request.get_json()}")

@app.after_request
def log_response_info(response):
    """Log information about outgoing responses"""
    api_logger.debug(f"Response status: {response.status_code}")
    return response

def handle_sigterm(signum, frame):
    """Handle termination signals gracefully"""
    main_logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
    main_logger.info("Closing database connections...")
    db.session.close()
    main_logger.info("Shutdown complete. Exiting...")
    sys.exit(0)


@app.route("/layers", methods=["GET"])
def get_layers():
    """Retrieve all raster layers"""
    api_logger.info("GET /layers - Retrieving all layers")
    try:
        layers = RasterLayer.query.all()
        json_layers = list(map(lambda x: x.to_json(), layers))
        api_logger.info(f"Successfully retrieved {len(layers)} layers")
        return jsonify({"layers": json_layers})
    except Exception as e:
        api_logger.error(f"Failed to retrieve layers: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": "Internal server error while retrieving layers"}), 500


@app.route("/upload", methods=["POST"])
def upload_file():
    """Handle file upload and return available columns"""
    api_logger.info("POST /upload - Processing file upload")
    try:
        if 'file' not in request.files:
            api_logger.warning("No file in request")
            return jsonify({"message": "No file provided"}), 400
            
        file = request.files['file']
        api_logger.info(f"Processing uploaded file: {file.filename}")
        
        columns = provide_columns(file.stream)
        api_logger.info(f"Successfully extracted {len(columns)} columns: {columns}")
        
        return jsonify({"columns": columns})
    except Exception as e:
        api_logger.error(f"File upload failed: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": f"Error processing file: {str(e)}"}), 400


@app.route("/get_columns/<int:layer_id>", methods=["GET"])
def get_columns(layer_id):
    """Get columns for a specific layer"""
    api_logger.info(f"GET /get_columns/{layer_id} - Retrieving columns for layer {layer_id}")
    try:
        layer = db.session.get(RasterLayer, layer_id)
        if not layer:
            api_logger.warning(f"Layer {layer_id} not found")
            return jsonify({"message": "Layer not found"}), 404

        columns = provide_columns(BytesIO(layer.in_csv_data))
        api_logger.info(f"Successfully retrieved {len(columns)} columns for layer {layer_id}")
        return jsonify({"columns": columns})
    except Exception as e:
        api_logger.error(f"Failed to get columns for layer {layer_id}: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": "Error retrieving columns"}), 500


@app.route("/get_raster/<int:layer_id>", methods=["GET"])
def get_raster(layer_id):
    """Get raster data for a specific layer"""
    api_logger.info(f"GET /get_raster/{layer_id} - Retrieving raster for layer {layer_id}")
    try:
        layer = db.session.get(RasterLayer, layer_id)
        if not layer:
            api_logger.warning(f"Layer {layer_id} not found")
            return jsonify({"message": "Layer not found"}), 404

        api_logger.debug(f"Converting raster data to base64 for layer {layer_id}")
        image = BytesIO(layer.out_img_data)
        json_index = layer.out_json_data
        image_base64 = base64.b64encode(image.getvalue()).decode('ascii')

        # Construct the JSON response
        image_response_data = {
            "image": image_base64,
            "contentType": 'image/tiff'  # GEOTIFF MIME TYPE
        }
        
        api_logger.info(f"Successfully retrieved raster for layer {layer_id}")
        return jsonify({"layerImage": image_response_data, "layerJson": json.load(StringIO(json_index))})
    except Exception as e:
        api_logger.error(f"Failed to get raster for layer {layer_id}: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": "Error retrieving raster data"}), 500


@app.route("/get_json/<int:layer_id>/<string:coord>", methods=["GET"])
def get_json(layer_id, coord):
    """Get JSON metadata for a specific layer and coordinate"""
    api_logger.info(f"GET /get_json/{layer_id}/{coord} - Retrieving JSON for layer {layer_id}, coord {coord}")
    try:
        layer = db.session.get(RasterLayer, layer_id)
        if not layer:
            api_logger.warning(f"Layer {layer_id} not found")
            return jsonify({"message": "Layer not found"}), 404

        json_index = StringIO(layer.out_json_data)
        if coord == "None":
            find_these_items = ["tbound", "bbound", "lbound", "rbound", "sizex", "sizey"]
            api_logger.debug(f"Retrieving bounds and size for layer {layer_id}")
        else:
            find_these_items = [coord]
            api_logger.debug(f"Retrieving specific coordinate {coord} for layer {layer_id}")

        json_index = json.loads(json_index.getvalue())
        new_json = {}
        for item in find_these_items:
            new_json[item] = json_index[item]

        del json_index, find_these_items
        api_logger.info(f"Successfully retrieved JSON data for layer {layer_id}")
        return jsonify({"jsonFile": new_json})
    except Exception as e:
        api_logger.error(f"Failed to get JSON for layer {layer_id}: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": "Error retrieving JSON data"}), 500


@app.route("/create_layer", methods=["POST"])
def create_layer():
    """Create a new raster layer"""
    api_logger.info("POST /create_layer - Creating new layer")
    
    try:
        # Validate request
        if 'file' not in request.files:
            api_logger.warning("No file in create layer request")
            return jsonify({"message": "No file provided"}), 400
            
        file = request.files["file"]
        title = request.form.get("title")
        filename = file.filename
        
        api_logger.info(f"Creating layer with file: {filename}, title: {title}")

        # Parse column weights
        col_weights = request.form.get("colWeights")
        if not col_weights:
            api_logger.warning("No column weights provided")
            return jsonify({"message": "Column weights are required"}), 400
            
        col_weights = col_weights.replace("'", "\"")
        col_weights = json.loads(col_weights)
        api_logger.debug(f"Column weights: {col_weights}")

        # Parse geometry columns
        geom = request.form.get("geom")
        if not geom or "," not in geom:
            api_logger.warning("Invalid geometry format")
            return jsonify({"message": "Invalid geometry format. Expected 'x,y'"}), 400
            
        prime_index = geom.index(",")
        geom_x = geom[:prime_index]
        geom_y = geom[prime_index + 1:]
        api_logger.debug(f"Geometry columns - X: {geom_x}, Y: {geom_y}")

        # Validate all required fields
        if not title or not filename or not col_weights or not geom:
            api_logger.warning("Missing required fields in create layer request")
            return jsonify({"message": "You must include a title, file and col_weights"}), 400

        # Initialize buffers
        api_logger.debug("Initializing buffer streams")
        instream = BytesIO(file.read())
        outstream_1 = BytesIO()
        outstream_2 = StringIO()
        outstream_3 = BytesIO()

        # Generate raster
        try:
            api_logger.info("Starting raster generation process")
            generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
            outstream_1_value = outstream_1.getvalue()
            api_logger.info("Raster file generated successfully")

            api_logger.info("Generating pixel JSON")
            write_pix_json(BytesIO(outstream_1_value), outstream_2)
            api_logger.info("Pixel JSON generated successfully")

            api_logger.info("Converting to alpha channel")
            convert_to_alpha(BytesIO(outstream_1_value), out_fp=outstream_3)
            api_logger.info("Alpha conversion completed")
            
            outstream_1 = None  # Help garbage collector
            gc.collect()
            
        except Exception as e:
            api_logger.error(f"Raster generation failed: {str(e)}")
            api_logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"message": f"Failed to generate raster: {str(e)}"}), 500

        # Create database entry
        new_layer = RasterLayer(
            filename,
            col_weights,
            title,
            geom_y,
            geom_x,
            instream.getvalue(),
            outstream_3.getvalue(),
            outstream_2.getvalue()
        )

        # Close streams
        instream.close()
        outstream_2.close()
        outstream_3.close()
        
        api_logger.debug(f"Created RasterLayer object: {new_layer}")

        # Save to database
        try:
            db_logger.info(f"Saving new layer to database: {title}")
            db.session.add(new_layer)
            db.session.commit()
            db_logger.info(f"Layer {title} saved successfully with ID: {new_layer.id}")
        except Exception as e:
            db_logger.error(f"Database error while saving layer: {str(e)}")
            db_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return jsonify({"message": f"Database error: {str(e)}"}), 400

        api_logger.info(f"Layer created successfully with ID: {new_layer.id}")
        return jsonify({"message": "Layer Created!", "layer_id": new_layer.id}), 201
        
    except json.JSONDecodeError as e:
        api_logger.error(f"JSON parsing error: {str(e)}")
        return jsonify({"message": "Invalid JSON format in column weights"}), 400
    except Exception as e:
        api_logger.error(f"Unexpected error in create_layer: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500


@app.route("/update_layer/<int:layer_id>", methods=["PATCH"])
def update_layer(layer_id):
    """Update an existing raster layer"""
    api_logger.info(f"PATCH /update_layer/{layer_id} - Updating layer {layer_id}")
    
    try:
        layer = db.session.get(RasterLayer, layer_id)
        if not layer:
            api_logger.warning(f"Layer {layer_id} not found for update")
            return jsonify({"message": "Layer not found"}), 404

        file = request.files.get("file")
        data = request.form
        title = data.get("title")
        
        if file:
            filename = file.filename
            api_logger.info(f"Updating layer {layer_id} with new file: {filename}")
        else:
            filename = layer.filename
            api_logger.info(f"Updating layer {layer_id} without file change")

        # Parse column weights
        col_weights = data.get("colWeights")
        if not col_weights:
            api_logger.warning("No column weights provided for update")
            return jsonify({"message": "Column weights are required"}), 400
            
        col_weights = col_weights.replace('"', "\"").replace("'", "\"")
        col_weights = json.loads(col_weights)
        
        # Parse geometry
        geom = data.get("geom")
        if not geom or "," not in geom:
            api_logger.warning("Invalid geometry format in update")
            return jsonify({"message": "Invalid geometry format"}), 400
            
        prime_index = geom.index(",")
        geom_x = geom[:prime_index]
        geom_y = geom[prime_index + 1:]

        # Check if regeneration is needed
        needs_regeneration = (
            (layer.filename != filename) or 
            (json.loads(layer.col_weights) != col_weights) or 
            (layer.geom_x != geom_x) or 
            (layer.geom_y != geom_y)
        )

        if needs_regeneration:
            api_logger.info(f"Regeneration needed for layer {layer_id}")
            
            if layer.filename != filename:
                instream = BytesIO(file.read())
            else:
                instream = BytesIO(layer.in_csv_data)

            outstream_1 = BytesIO()
            outstream_2 = StringIO()
            outstream_3 = BytesIO()

            try:
                api_logger.info("Starting raster regeneration")
                generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
                api_logger.info("Raster file regenerated")
                
                write_pix_json(outstream_1, outstream_2)
                api_logger.info("JSON file regenerated")
                
                convert_to_alpha(outstream_1, out_fp=outstream_3)
                api_logger.info("Alpha conversion completed")

                # Update layer data
                layer.filename = filename
                layer.col_weights = str(col_weights).replace("'", "\"")
                layer.geom_x = geom_x
                layer.geom_y = geom_y
                layer.in_csv_data = instream.getvalue()
                layer.out_img_data = outstream_3.getvalue()
                layer.out_json_data = outstream_2.getvalue()
                
            except Exception as e:
                api_logger.error(f"Regeneration failed for layer {layer_id}: {str(e)}")
                api_logger.error(f"Traceback: {traceback.format_exc()}")
                return jsonify({"message": f"Failed to regenerate raster: {str(e)}"}), 500

        layer.title = title

        # Save changes
        try:
            db_logger.info(f"Saving updates for layer {layer_id}")
            db.session.commit()
            db_logger.info(f"Layer {layer_id} updated successfully")
        except Exception as e:
            db_logger.error(f"Database error updating layer {layer_id}: {str(e)}")
            db_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return jsonify({"message": f"Database error: {str(e)}"}), 500

        api_logger.info(f"Layer {layer_id} updated successfully")
        return jsonify({"message": "Layer updated!"}), 200
        
    except Exception as e:
        api_logger.error(f"Unexpected error updating layer {layer_id}: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500


@app.route("/delete_layer/<int:layer_id>", methods=["DELETE"])
def delete_layer(layer_id):
    """Delete a raster layer"""
    api_logger.info(f"DELETE /delete_layer/{layer_id} - Deleting layer {layer_id}")
    
    try:
        layer = RasterLayer.query.get(layer_id)
        if not layer:
            api_logger.warning(f"Layer {layer_id} not found for deletion")
            return jsonify({"message": "Layer not found"}), 404

        try:
            db_logger.info(f"Deleting layer {layer_id} from database")
            db.session.delete(layer)
            db.session.commit()
            db_logger.info(f"Layer {layer_id} deleted successfully")
        except Exception as e:
            db_logger.error(f"Database error deleting layer {layer_id}: {str(e)}")
            db_logger.error(f"Traceback: {traceback.format_exc()}")
            db.session.rollback()
            return jsonify({"message": f"Database error: {str(e)}"}), 500

        api_logger.info(f"Layer {layer_id} deleted successfully")
        return jsonify({"message": "Layer deleted!"}), 200
        
    except Exception as e:
        api_logger.error(f"Unexpected error deleting layer {layer_id}: {str(e)}")
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({"message": f"Unexpected error: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    api_logger.warning(f"404 error: {request.url}")
    return jsonify({"message": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    api_logger.error(f"500 error: {str(error)}")
    api_logger.error(f"Traceback: {traceback.format_exc()}")
    return jsonify({"message": "Internal server error"}), 500


if __name__ == "__main__":
    # Set up signal handlers
    signal.signal(signal.SIGTERM, handle_sigterm)
    signal.signal(signal.SIGINT, handle_sigterm)

    try:
        with app.app_context():
            main_logger.info("Initializing database tables")
            db.drop_all()
            db.create_all()
            main_logger.info("Database tables created successfully")

        # Configure Waitress logging
        waitress_logger = logging.getLogger('waitress')
        waitress_logger.setLevel(logging.INFO)
        
        main_logger.info("Starting Waitress server on http://0.0.0.0:8080")
        serve(app, host="0.0.0.0", port=8080)
        
    except Exception as e:
        main_logger.critical(f"Failed to start application: {str(e)}")
        main_logger.critical(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
