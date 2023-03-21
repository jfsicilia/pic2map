"""GPS data model and validation."""
from itertools import count
import logging

import exiftool

from voluptuous import (
    All,
    Any,
    Invalid,
    Match,
    Range,
    Required,
    Schema,
    unicode
)

logger = logging.getLogger(__name__)

# Interesting tags with GPS information
TAGS = [
    'EXIF:GPSDateStamp',
    'EXIF:GPSLatitude',
    'EXIF:GPSLatitudeRef',
    'EXIF:GPSLongitude',
    'EXIF:GPSLongitudeRef',
    'EXIF:GPSTimeStamp',
]

PATHS_PARTITION_SIZE = 1000

POSITIVE_NUMBER = All(Any(int, float), Range(min=0))

SCHEMA = Schema({
    Required('EXIF:GPSLatitude'): POSITIVE_NUMBER,
    Required('EXIF:GPSLatitudeRef'): Any(u'N', u'S'),
    Required('EXIF:GPSLongitude'): POSITIVE_NUMBER,
    Required('EXIF:GPSLongitudeRef'): Any(u'E', u'W'),
    Required('SourceFile'): unicode,
})


def validate_gps_metadata(exif_metadata):
    """Validate GPS metadata using a schema.

    :param exif_metadata: Metadata to be validated
    :type exif_metadata: dict(str)
    :returns: Whether GPS metadata was found or not
    :rtype: bool

    """
    try:
        SCHEMA(exif_metadata)
    except Invalid as exception:
        logger.debug(
            'No GPS metadata found:\n%s\n%s', exif_metadata, exception)
        return False

    return True


def get_gps_metadata(paths):
    """
    :param paths: Picture filenames to get metadata from
    :type paths: list(str)
    :returns: The metadata records
    :rtype: list(dict(str))

    """
    partitions = list(partition(paths, PATHS_PARTITION_SIZE))
    if len(partitions) > 1:
        logger.info(
            'Getting GPS metadata for %d files in %d partitions',
            len(paths),
            len(partitions)
        )
    with exiftool.ExifToolHelper() as tool:
        for i, part in enumerate(partition(paths, PATHS_PARTITION_SIZE)):
            metadata_records = tool.get_tags(part, TAGS)
            for metadata_record in metadata_records:
                metadata_record['valid'] = validate_gps_metadata(metadata_record)

            if len(partitions) > 1:
                logger.info(
                    'Found %d GPS metadata records in partition %d',
                    len(m for m in metadata_records if m['valid']),
                    i + 1
                )
            yield metadata_records


def partition(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i+size]
