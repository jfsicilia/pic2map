"""Location database."""

import logging
import os

import arrow

from sqlalchemy import (
    Column,
    MetaData,
    Table,
    create_engine,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy.types import (
    DateTime,
    Float,
    Integer,
    String,
)
from sqlalchemy.dialects.sqlite import insert as db_insert

# from xdg import BaseDirectory

logger = logging.getLogger(__name__)


class Database(object):

    """Generic database object.

    This class is subclassed to provide additional functionality specific to
    artifacts and/or documents.

    :param db_filename: Path to the sqlite database file
    :type db_filename: str

    """

    def __init__(self, db_filename):
        """Connect to database and create session object."""
        self.db_filename = db_filename
        self.engine = create_engine(
            'sqlite:///{}'.format(db_filename),
            connect_args={'check_same_thread': False},
            isolation_level="AUTOCOMMIT"
        )
        self.connection = None
        self.metadata = MetaData()

    def connect(self):
        """Create connection."""
        logger.debug('Connecting to SQLite database: %r', self.db_filename)
        self.connection = self.engine.connect()

    def disconnect(self):
        """Close connection."""
        assert not self.connection.closed
        logger.debug(
            'Disconnecting from SQLite database: %r', self.db_filename)
        self.connection.close()

    def __enter__(self):
        """Connect on entering context."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Disconnect on exiting context."""
        self.disconnect()

    def __getitem__(self, table_name):
        """Get table object in database.

        :param table_name: Name of the table
        :type table_name: str
        :return: Table object that can be used in queries
        :rtype: sqlalchemy.schema.Table

        """
        if not isinstance(table_name, str):
            raise TypeError('Unexpected table name: {}'.format(table_name))
        table = self.metadata.tables.get(table_name)
        if table is None:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
        return table


class LocationDB(Database):

    """Location database.

    Store location information from picture files into a sqlite database.

    """

    def __init__(self):
        """Create database if needed."""
        # base_directory = BaseDirectory.save_data_path('pic2map')
        # db_filename = os.path.join(base_directory, 'location.db')
        db_filename = os.path.join('.', 'location.db')
        Database.__init__(self, db_filename)

        if os.path.isfile(db_filename):
            self.location_table = self['location']
        else:
            logger.debug('Creating location database %r...', db_filename)

            self.location_table = Table(
                'location',
                self.metadata,
                Column('id', Integer, primary_key=True, autoincrement=True),
                Column('album', String),
                Column('filepath', String),
                Column('latitude', Float),
                Column('longitude', Float),
                Column('datetime', DateTime),
                UniqueConstraint('album', 'filepath', name='uix_album_filepath')
            )
            self.location_table.create(bind=self.engine)

    def insert(self, rows):
        """Insert rows in location table.

        :param rows: Rows to be inserted in the database
        :type rows: list(dict(str))

        """
        insert_query = db_insert(self.location_table).on_conflict_do_nothing()
        result = self.connection.execute(insert_query, rows)
        logger.debug('%d rows inserted', result.rowcount)

    def select_all(self, albums=None):
        """Get all rows from the location table.

        :param albums: List of albums to filter
        :type albums: list(str)
        :returns: Location information rows
        :rtype: sqlalchemy.engine.result.ResultProxy

        """
        select_query = select(self.location_table)
        if albums:
            select_query = select_query.where(self.location_table.c.album.in_(albums))
        result = self.connection.execute(select_query)
        return result

    def get_by_id(self, id):
        query = self.location_table.select().where(self.location_table.c.id == id)
        result = self.connection.execute(query)
        return result
    

    def exists(self, filepath):
        """Check if a row with the given filepath exists in the location table.

        :param filepath: The filepath to check for
        :type filepath: str
        :returns: True if a row with the given filepath exists, False otherwise
        :rtype: bool
        """
        query = self.location_table.select().where(self.location_table.c.filepath == filepath)
        result = self.connection.execute(query)
        return result.fetchone() is not None

    def delete(self, album):
        """Delete rows within a given album.

        :param album: Album to be deleted.
        :type album: str
        :return: Number of rows deleted
        :rtype: int

        """
        table = self.location_table
        delete_query = (
            table.delete()
            .where(table.c.album == album)
        )
        result = self.connection.execute(delete_query)
        logger.debug('%d rows deleted', result.rowcount)
        return result.rowcount

    def list_albums(self, albums):
        """Get the list of albums in the database.

        :return: List of albums.
        :rtype: list

        """
        query = select(self.location_table.c.album).distinct()
        if albums:
            query = query.where(self.location_table.c.album.in_(albums)).distinct()
        result = self.connection.execute(query)
        return [row.album for row in result]

    def count(self, album):
        """Get number of pictures in an album.

        :return: Number of pictures
        :rtype: int

        """
        stmt = select(func.count()).select_from(self.location_table).filter(self.location_table.c.album == album)
        result = self.connection.execute(stmt)
        return result.scalar()


def transform_metadata_to_row(album, metadata):
    """Transform GPS metadata in database rows.

    :param metadata: GPS metadata as returned by exiftool
    :type metadata: dict(str)
    :returns: Database row
    :rtype: dict(str)

    """
    new_metadata = {
        'album' : album,
        'filepath': metadata['SourceFile'],
        'latitude': metadata['EXIF:GPSLatitude'],
        'longitude': metadata['EXIF:GPSLongitude'],
    }

    if metadata['EXIF:GPSLatitudeRef'] == u'S':
        new_metadata['latitude'] *= -1
    if metadata['EXIF:GPSLongitudeRef'] == u'W':
        new_metadata['longitude'] *= -1

    if ('EXIF:GPSDateStamp' in metadata and
            'EXIF:GPSTimeStamp' in metadata):
        datetime_str = u'{} {}'.format(
            metadata['EXIF:GPSDateStamp'],
            metadata['EXIF:GPSTimeStamp'],
        )

        new_metadata['datetime'] = arrow.get(
            datetime_str,
            ['YYYY:MM:DD HH:mm:ss.SSS', 'YYYY:MM:DD HH:mm:ss'],
        ).datetime
    else:
        new_metadata['datetime'] = None

    return new_metadata
