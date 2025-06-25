import json
import base64
import logging
import signal
import sys
import gc
from waitress import serve
from flask import request, jsonify
from config import app, db, main_logger
from models import RasterLayer
from io import BytesIO, StringIO
from generate_raster_file import generate_raster_file
from getImage import write_pix_json, convert_to_alpha
from provide_columns import provide_columns

def handle_sigterm(signum, frame):
    """Handles a sigterm, if thrown by the interpreter"""
    main_logger.info(f"Received signal {signum}. Exiting gracefully...")
    sys.exit(0)


@app.route("/layers", methods=["GET"])
def get_layers():
    """
    Retrieves all stored raster layers.

    Returns:
            JSON: A list of all layer objects in the database.
    """
    layers = RasterLayer.query.all()
    json_layers = list(map(lambda x: x.to_json(), layers))
    return jsonify({"layers": json_layers})


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Retrieves a csv file, and provides all numerical columns for that file
    Returns:
            JSON: A list of all numerical columns found.
    """
    try:
        file = request.files['file']
        columns = provide_columns(file.stream)
        return jsonify({"columns": columns})

    except Exception as e:
        main_logger.error(e)
        return jsonify({"message": str(e)}), 400


@app.route("/get_columns/<int:layer_id>", methods=["GET"])
def get_columns(layer_id: int):
    """
    Retrieve all of the columns in data set that have numerical values
    Query Parameters:
            layer_id (int): unique id for the database layer to retrieve columns from
    Returns:
            JSON: A list of all numerical columns found.
    """
    layer = db.session.get(RasterLayer, layer_id)
    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    columns = provide_columns(BytesIO(layer.in_csv_data))
    return jsonify({"columns": columns})



@app.route("/get_raster/<int:layer_id>", methods=["GET"])
def get_raster(layer_id):
    """
    Retrieve the raster image from a layer
    Query Parameters:
            layer_id (int): unique id for the database layer to retrieve the raster from
    Returns:
            JSON: A dictionary containing the Image data in base64, and the json data
            describing the dimensions and pixel values
    """
    layer = db.session.get(RasterLayer, layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    image = BytesIO(layer.out_img_data)

    json_index = layer.out_json_data

    image_base64 = base64.b64encode(image.getvalue()).decode('ascii')

    # Construct the JSON response
    image_response_data = {
        "image": image_base64,
        "contentType": 'image/tiff'  # GEOTIFF MIME TYPE
    }
    return jsonify({"layerImage": image_response_data, "layerJson": json.load(StringIO(json_index))})


@app.route("/get_json/<int:layer_id>/<string:coord>", methods=["GET"])
def get_json(layer_id, coord):
    """
    Retrieve a pixel value in data set, as well as the dimensions of the layer image
    Query Parameters:
            layer_id (int): unique id for the database layer
            coord (str): the coodinate of the pixel to query
    Returns:
            JSON: An object describing the top, bottom, left, and right bounds of the layer,
            as well as the size, and specific pixel value.
    """
    layer = db.session.get(RasterLayer, layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    json_index = StringIO(layer.out_json_data)
    if coord == "None":
        find_these_items = ["tbound", "bbound", "lbound", "rbound", "sizex", "sizey"]
    else:
        find_these_items = [coord]

    json_index = json.loads(json_index.getvalue())

    new_json = {}
    for item in find_these_items:
        new_json[item] = json_index[item]

    del json_index, find_these_items
    return jsonify({"jsonFile": new_json})


@app.route("/create_layer", methods=["POST"])
def create_layer():
    """
    Create a layer and store in database

    Returns:
            JSON: A success message
    """
    main_logger.info("Creating Layer")
    file = request.files["file"]
    title = request.form.get("title")
    filename = file.filename
    main_logger.info("Successfully grabbed file")

    col_weights = request.form.get("colWeights")
    col_weights = col_weights.replace("'", "\"")
    col_weights = json.loads(col_weights)
    main_logger.info("Successfully grabbed Column Weights")

    geom = request.form.get("geom")
    for i, string in enumerate(geom):
        if string == ",":
            prime_index = i
    geom_x = geom[:prime_index]
    geom_y = geom[prime_index + 1:]

    main_logger.info("Successfully grabbed geometry columns")
    main_logger.info((filename, col_weights, title, geom_y, geom_x))

    instream = BytesIO(file.read())

    outstream_1 = BytesIO()

    outstream_2 = StringIO()

    outstream_3 = BytesIO()

    main_logger.info("Successfully Initialized Buffer streams")

    try:
        generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
        # Get values and release memory
        outstream_1_value = outstream_1.getvalue()

        write_pix_json(BytesIO(outstream_1_value), outstream_2)

        convert_to_alpha(BytesIO(outstream_1_value), out_fp=outstream_3)
        outstream_1 = None  # Help garbage collector

    except Exception as e:
        main_logger.info(e)




    if not title or not filename or not col_weights or not geom:
        return (
            jsonify({"message": "You must include a title, file and col_weights"}),
            400,
        )

    new_layer = RasterLayer(
        filename,
        col_weights,
        title,
        geom_y,
        geom_x,
        instream.getvalue(),
        outstream_3.getvalue(),
        outstream_2.getvalue())

    instream.close()  # Release memory
    print("TEST", new_layer, "END TEST")

    try:
        db.session.add(new_layer)
        db.session.commit()
    except Exception as e:
        print("ERROR:", e, "END ERROR")
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "Layer Created!"}), 201



@app.route("/update_layer/<int:layer_id>", methods=["PATCH"])
def update_layer(layer_id):
    """
    Updates a layer currently in the database
    Query Parameters:
            layer_id (int): unique id for the database layer
    Returns:
            JSON: A success message
    """
    layer = db.session.get(RasterLayer, layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    file = request.files.get("file")
    data = request.form
    title = data.get("title")
    if file:
        filename = file.filename
    else:
        filename = layer.filename

    col_weights = data.get("colWeights")
    col_weights = col_weights.replace('"', "\"")
    col_weights = col_weights.replace("'", "\"")
    col_weights = json.loads(col_weights)
    geom = data.get("geom")

    for i, string in enumerate(geom):
        if string == ",":
            prime_index = i
    geom_x = geom[:prime_index]
    geom_y = geom[prime_index + 1:]

    if (layer.filename != filename):
        instream = BytesIO(file.read())
    else:
        instream = BytesIO(layer.in_csv_data)

    if ((layer.filename != filename) or (json.loads(layer.col_weights) != col_weights)
            or (layer.geom_x != geom_x) or (layer.geom_y != geom_y)):

        outstream_1 = BytesIO()

        outstream_2 = StringIO()

        outstream_3 = BytesIO()

        generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
        main_logger.info("Raster File Generated")
        write_pix_json(outstream_1, outstream_2)
        main_logger.info("Json File Generated")
        convert_to_alpha(outstream_1, out_fp=outstream_3)
        main_logger.info("Successfully Converted Image to LA")

        layer.filename = filename
        layer.col_weights = str(col_weights).replace("'", "\"")
        layer.geom_x = geom_x
        layer.geom_y = geom_y
        layer.in_csv_data = instream.getvalue()
        layer.out_img_data = outstream_3.getvalue()
        layer.out_json_data = outstream_2.getvalue()

    layer.title = title

    db.session.commit()

    return jsonify({"message": "Layer updated!"}), 200


@app.route("/delete_layer/<int:layer_id>", methods=["DELETE"])
def delete_layer(layer_id):
    """
        Deletes a layer from the database
        Query Parameters:
                layer_id (int): unique id for the database layer to delete
        Returns:
                JSON: A success message
        """
    layer = RasterLayer.query.get(layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    db.session.delete(layer)
    db.session.commit()

    return jsonify({"message": "Layer deleted!"}), 200

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)

    with app.app_context():
        db.drop_all()
        db.create_all()

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.INFO)

    serve(app, host="0.0.0.0", port=8080)
