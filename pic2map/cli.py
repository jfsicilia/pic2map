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
from pic2map.gps import filter_gps_metadata
from pic2map.server.app import app
from pic2map.server.app import ALBUMS_CONFIG_TAG, DEFAULT_HOST, DEFAULT_PORT


logger = logging.getLogger(__name__)


def main(argv=None):
    """
    Entry point for the pic2map.py script.

    Args:
        argv (list, optional): List of command-line arguments. Defaults to None, which uses sys.argv[1:].

    This function parses command-line arguments, configures logging, and invokes the appropriate function
    based on the parsed arguments. If no function is specified in the arguments, it prints the argument parser help.
    """
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    configure_logging(args.log_level)
    if hasattr(args, "func"):
        args.func(args)
    else:
        args.parser.print_help()


def add(args):
    """Add location information for pictures in an album.

    :param args.album: Album name
    :type args.album: str
    :param args.directories: One or more directories with album pictures
    :type args.directories: list(str)
    """
    paths = []
    for directory in args.directories:
        logger.info(
            "Adding image files for album %r from %r...", args.album, directory
        )
        tree_explorer = TreeExplorer(directory)
        paths.extend(tree_explorer.paths())

    gps_metadata_records = filter_gps_metadata(paths)

    logger.info(
        "%d pictures found with GPS metadata", len(gps_metadata_records)
    )

    location_rows = [
        transform_metadata_to_row(args.album, metadata)
        for metadata in gps_metadata_records
    ]
    if location_rows:
        with LocationDB() as database:
            database.insert(location_rows)


def remove(args):
    """Remove album/s from the database.

    :param args.albums: One or more albums to be removed
    :type args.albums: list(str)
    """

    with LocationDB() as database:
        for album in args.albums:
            logger.info("Removing image files from album %r...", album)
            nRows = database.delete(album)
            if nRows > 0:
                logger.info("Deleted album %s with %d rows", album, nRows)


def list(args):
    """Retrieve the list of albums and the number of pictures in the database."""
    logger.info("Getting albums' information from the database...")

    with LocationDB() as database:
        albums = database.list_albums(args.albums)
        for album in albums:
            count = database.count(album)
            logger.info("Album {!r} has {} pictures".format(album, count))


def server(args):
    """Run web server.

    :param _args: Command line arguments
    """
    app.config[ALBUMS_CONFIG_TAG] = args.albums
    app.run(debug=True, port=DEFAULT_PORT, host=DEFAULT_HOST)


def valid_directory(path):
    """Directory validation."""
    if not os.path.isdir(path):
        raise argparse.ArgumentTypeError(
            "{!r} is not a valid directory".format(path)
        )

    if not os.access(path, os.R_OK | os.X_OK):
        raise argparse.ArgumentTypeError(
            "not enough permissions to explore {!r}".format(path)
        )

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
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    log_handler.setFormatter(formatter)
    log_handler.setLevel(log_level)
    root_logger.addHandler(log_handler)


def parse_arguments(argv):
    """Parse command line arguments.

    :returns: Parsed arguments
    :rtype: argparse.Namespace

    """
    parser = argparse.ArgumentParser(
        description="Show the locations of pictures from an album on a map."
    )
    log_levels = ["debug", "info", "warning", "error", "critical"]
    parser.add_argument(
        "-l",
        "--log-level",
        dest="log_level",
        choices=log_levels,
        default="info",
        help=(
            "Log level. One of {0} or {1} "
            "(%(default)s by default)".format(
                ", ".join(log_levels[:-1]), log_levels[-1]
            )
        ),
    )
    parser.set_defaults(parser=parser)

    subparsers = parser.add_subparsers(help="Subcommands")

    # ADD subcommand
    add_parser = subparsers.add_parser("add", help=add.__doc__)
    add_parser.add_argument("album", type=str, help="Album name")
    add_parser.add_argument(
        "directories",
        type=valid_directory,
        nargs="+",
        help="One or more directories with album pictures",
    )
    add_parser.set_defaults(func=add)

    # REMOVE subcommand
    remove_parser = subparsers.add_parser("remove", help=remove.__doc__)
    remove_parser.add_argument(
        "albums", nargs="+", help="Albums to be removed."
    )
    remove_parser.set_defaults(func=remove)

    # LIST subcommand
    list_parser = subparsers.add_parser("list", help=list.__doc__)
    list_parser.add_argument(
        "albums",
        nargs="*",
        help="Albums to be listed (if omitted, all albums will be listed).",
    )
    list_parser.set_defaults(func=list)

    # SERVER subcommand
    serve_parser = subparsers.add_parser("server", help=server.__doc__)
    serve_parser.add_argument(
        "albums",
        nargs="*",
        help="Albums to be shown (if omitted, all albums will be displayed).",
    )
    serve_parser.set_defaults(func=server)

    args = parser.parse_args(argv)
    args.log_level = getattr(logging, args.log_level.upper())
    return args


if __name__ == "__main__":
    main()
