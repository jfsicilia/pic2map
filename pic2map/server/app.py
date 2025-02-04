"""Web application server."""

import json
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    abort,
    send_file,
)

from pic2map.db import LocationDB
from pic2map.util import average

# Note: python and javascript don't seem to agree on what %c, %x
# and %X are, so it's better to be explicit in the time formatting
DATE_EXCHANGE_FORMAT = "%Y/%m/%d %H:%M:%S"

# Configuration keys for the application
ALBUMS_CONFIG_TAG = "ALBUMS"

# Template index file
TEMPLATE_INDEX = "index.html"

# URL parameters
PARAM_ALBUMS = "albums"
PARAM_ID = "id"

# Default port and host for the web server
DEFAULT_PORT = 5000
DEFAULT_HOST = "0.0.0.0"

app = Flask(__name__)


@app.route("/")
def index():
    """Application main page."""

    param = request.args.get(PARAM_ALBUMS)
    if param:
        albums = param.split(",")
    else:
        albums = app.config[ALBUMS_CONFIG_TAG]

    with LocationDB() as location_db:
        db_rows = list(location_db.select_all(albums))
        if len(db_rows) == 0:
            centroid = json.dumps([0, 0])
            rows = json.dumps([])
        else:
            centroid = json.dumps(
                [
                    average([row.latitude for row in db_rows]),
                    average([row.longitude for row in db_rows]),
                ]
            )
            rows = json.dumps(
                [row_to_serializable(db_row) for db_row in db_rows]
            )

    return render_template(TEMPLATE_INDEX, centroid=centroid, rows=rows)


@app.route("/image")
def serve_image():
    # Get requested image id
    id = request.args.get(PARAM_ID)
    if not id:
        abort(400, "Missing id url parameter.")

    with LocationDB() as location_db:
        row = location_db.get_by_id(id)
        print(row)
        if not row:
            abort(404, f"Image id {id} not found")

        # Filepath is relative to the directory where the interpreter was launched.
        filepath = Path.cwd() / row.filepath
        print(filepath)
        if not filepath.exists():
            abort(404, f"Image file {filepath} not found")
        return send_file(filepath, mimetype="image/jpeg")


def row_to_serializable(row):
    """Transform row to make it json serializable.

    This is needed to pass the location informaton to the javascript code.

    :param row: Database row with location information
    :type row: sqlalchemy.engine.row.Row
    :returns: Location information in JSON format
    :rtype: dict(str)

    """
    row = row._asdict()
    if row["datetime"]:
        row["datetime"] = row["datetime"].strftime(DATE_EXCHANGE_FORMAT)
    return row


if __name__ == "__main__":
    app.run(debug=True, port=DEFAULT_PORT, host=DEFAULT_HOST)
