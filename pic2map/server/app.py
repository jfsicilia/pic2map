"""Web application server."""

import json

from flask import (
    Flask,
    render_template,
    request,
    send_file,
)

from pic2map.db import LocationDB
from pic2map.util import average

# Note: python and javascript don't seem to agree on what %c, %x
# and %X are, so it's better to be explicit in the time formatting
DATE_EXCHANGE_FORMAT = '%Y/%m/%d %H:%M:%S'

app = Flask(__name__)


@app.route('/')
def index():
    """Application main page."""
    with LocationDB() as location_db:
        db_rows = list(location_db.select_all(True))
        centroid = json.dumps([
            average([row.latitude for row in db_rows]),
            average([row.longitude for row in db_rows]),
        ])
        rows = json.dumps([row_to_serializable(db_row) for db_row in db_rows])

    return render_template('index.html', centroid=centroid, rows=rows)


@app.route('/get_image')
def get_image():
    """Serves the image data for the given filename, if it is present in the db."""
    if filename := request.args.get('filename'):
        with LocationDB() as location_db:
            if location_db.file_exists(filename):
                return send_file(filename, mimetype='image/jpg')
    return None


def row_to_serializable(row):
    """Transform row to make it json serializable.

    This is needed to pass the location informaton to the javascript code.

    :param row: Database row with location information
    :type row: sqlalchemy.engine.row.Row
    :returns: Location information in JSON format
    :rtype: dict(str)

    """
    row = row._asdict()
    if row['datetime']:
        row['datetime'] = row['datetime'].strftime(DATE_EXCHANGE_FORMAT)
    return row


if __name__ == '__main__':
    app.run(debug=True)
