"""Command Line Interface."""

import argparse
import logging
import os
import sys

from pic2map.db import (
    LocationDB,
    transform_metadata_to_row,
)
from pic2map.fs import TreeExplorer
from pic2map.gps import get_gps_metadata
from pic2map.server.app import app


logger = logging.getLogger(__name__)


def main(argv=None):
    """Entry point for the pic2map.py script."""
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    configure_logging(args.log_level)
    args.func(args)


def add(args):
    """Add location information for pictures under directory."""
    dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.directory))
    logger.info('Adding image files from %r...', dir)
    tree_explorer = TreeExplorer(dir)
    paths = tree_explorer.paths()
    paths_set = set(paths)

    with LocationDB() as database:
        existing_paths = set(row.filename for row in database.select_all())
        filtered_paths = paths_set - existing_paths
        if len(filtered_paths) < len(paths):
            logger.info(
                'Processing %d files, skipping %d files (already in database)',
                len(filtered_paths),
                len(paths) - len(filtered_paths)
            )

        for gps_metadata_records in get_gps_metadata(list(filtered_paths)):
            location_rows = [
                transform_metadata_to_row(metadata)
                for metadata in gps_metadata_records
            ]
            if location_rows:
                database.insert(location_rows)
                logger.info('%d files added to database', len(location_rows))


def remove(args):
    """Remove location information for pictures under directory."""
    dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.directory))
    logger.info('Removing image files from %r...', dir)

    with LocationDB() as database:
        database.delete(dir)


def reset(args):
    """Reset the database."""
    logger.info('Resetting the database...')

    with LocationDB() as database:
        database.truncate()


def count(_args):
    """Get number picture files in the database."""
    logger.info('Getting image files in the database...')

    with LocationDB() as database:
        file_count = database.count()

    print(file_count)


def serve(_args):
    """Run web server."""
    app.run(debug=True)


def valid_directory(path):
    """Directory validation."""
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(
            '{!r} is not a valid directory'.format(path))

    if not os.access(path, os.R_OK | os.X_OK):
        raise argparse.ArgumentTypeError(
            'not enough permissions to explore {!r}'.format(path))

    return path


def configure_logging(log_level):
    """Configure logging based on command line argument.

    :param log_level: Log level passed form the command line
    :type log_level: int

    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Log to sys.stderr using log level
    # passed through command line
    log_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    log_handler.setFormatter(formatter)
    log_handler.setLevel(log_level)
    root_logger.addHandler(log_handler)


def parse_arguments(argv):
    """Parse command line arguments.

    :returns: Parsed arguments
    :rtype: argparse.Namespace

    """
    parser = argparse.ArgumentParser(
        description='Display pictures location in a map')
    log_levels = ['debug', 'info', 'warning', 'error', 'critical']
    parser.add_argument(
        '-l', '--log-level',
        dest='log_level',
        choices=log_levels,
        default='info',
        help=('Log level. One of {0} or {1} '
              '(%(default)s by default)'
              .format(', '.join(log_levels[:-1]), log_levels[-1])))

    subparsers = parser.add_subparsers(help='Subcommands')

    add_parser = subparsers.add_parser('add', help=add.__doc__)
    add_parser.add_argument(
        'directory', type=valid_directory, help='Base directory')
    add_parser.set_defaults(func=add)

    remove_parser = subparsers.add_parser('remove', help=remove.__doc__)
    remove_parser.add_argument(
        'directory', type=valid_directory, help='Base directory')
    remove_parser.set_defaults(func=remove)

    remove_parser = subparsers.add_parser('reset', help=reset.__doc__)
    remove_parser.set_defaults(func=reset)

    count_parser = subparsers.add_parser('count', help=count.__doc__)
    count_parser.set_defaults(func=count)

    serve_parser = subparsers.add_parser('serve', help=serve.__doc__)
    serve_parser.set_defaults(func=serve)

    args = parser.parse_args(argv)
    args.log_level = getattr(logging, args.log_level.upper())
    return args

if __name__ == '__main__':
    main()
