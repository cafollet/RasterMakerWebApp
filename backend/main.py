import json
import base64
import logging
from waitress import serve
from flask import request, jsonify
from config import app, db
from models import RasterLayer
from io import BytesIO, StringIO
from generate_raster_file import generate_raster_file
from getImage import write_pix_json, convert_to_alpha
from provide_columns import provide_columns
import git
import argparse

@app.route('/update_backend', methods=['POST'])
def webhook():
    if request.method == 'POST':
        repo = git.Repo(
            'https://github.com/cafollet/RasterMakerWebApp'
            )
        origin = repo.remotes.origin
        origin.pull()
        return 'Updated PythonAnywhere successfully', 200
    else:
        return 'Wrong event type', 400


@app.route("/layers", methods=["GET"])
def get_layers():
    layers = RasterLayer.query.all()
    json_layers = list(map(lambda x: x.to_json(), layers))
    return jsonify({"layers": json_layers})


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        file = request.files['file']
        return jsonify({"columns": provide_columns(BytesIO(file.read()))})

    except Exception as e:
        print("ERROR:", e, "END ERROR")
        return jsonify({"message": str(e)}), 400


@app.route("/get_columns/<int:layer_id>", methods=["GET"])
def get_columns(layer_id):
    layer = db.session.get(RasterLayer, layer_id)
    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    columns = provide_columns(BytesIO(layer.in_csv_data))
    return jsonify({"columns": columns})



@app.route("/get_raster/<int:layer_id>", methods=["GET"])
def get_raster(layer_id):
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


@app.route("/get_json/<int:layer_id>", methods=["GET"])
def get_json(layer_id):
    layer = db.session.get(RasterLayer, layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    json_index = StringIO(layer.out_json_data)
    json_index = json.loads(json_index.getvalue())

    return jsonify({"jsonFile": json_index})


@app.route("/create_layer", methods=["POST"])
def create_layer():
    file = request.files["file"]
    title = request.form.get("title")
    filename = file.filename

    col_weights = request.form.get("colWeights")
    col_weights = col_weights.replace("'", "\"")
    col_weights = json.loads(col_weights)

    geom = request.form.get("geom")
    for i, string in enumerate(geom):
        if string == ",":
            prime_index = i
    geom_x = geom[:prime_index]
    geom_y = geom[prime_index + 1:]

    logging.info(
        filename,
        col_weights,
        title,
        geom_y,
        geom_x)

    instream = BytesIO(file.read())

    outstream_1 = BytesIO()

    outstream_2 = StringIO()

    outstream_3 = BytesIO()

    try:
        generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
        logging.info("Raster File Generated")
        write_pix_json(outstream_1, outstream_2)
        logging.info("Json File Generated")
        convert_to_alpha(outstream_1, out_fp=outstream_3)
        logging.info("Successfully Converted Image to LA")
    except Exception as e:
        logging.info(e)




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
    layer = RasterLayer.query.get(layer_id)

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

    print(json.loads(layer.col_weights), col_weights)
    if (layer.filename != filename) or (json.loads(layer.col_weights) != col_weights) or (layer.geom_x != geom_x) or (layer.geom_y != geom_y):

        outstream_1 = BytesIO()

        outstream_2 = StringIO()

        outstream_3 = BytesIO()

        generate_raster_file(instream, outstream_1, col_weights, [geom_y, geom_x])
        logging.info("Raster File Generated")
        write_pix_json(outstream_1, outstream_2)
        logging.info("Json File Generated")
        convert_to_alpha(outstream_1, out_fp=outstream_3)
        logging.info("Successfully Converted Image to LA")

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
    layer = RasterLayer.query.get(layer_id)

    if not layer:
        return jsonify({"message": "Layer not found"}), 404

    db.session.delete(layer)
    db.session.commit()

    return jsonify({"message": "Layer deleted!"}), 200

if __name__ == "__main__":



    with app.app_context():
        db.drop_all()
        db.create_all()

    logger = logging.getLogger('waitress')
    logger.setLevel(logging.INFO)

    logging.basicConfig(filename='app.log', level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    serve(app, host="0.0.0.0", port=8080)
