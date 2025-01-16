#!/usr/bin/env python3
# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import hashlib
import json
import logging
import os
import sys

from codebasin import CodeBase, config, finder, util

# TODO: Refactor to avoid imports from __main__
from codebasin.__main__ import (
    Formatter,
    WarningAggregator,
    _help_string,
    version,
)
from codebasin.preprocessor import CodeNode

log = logging.getLogger("codebasin")


def _build_parser() -> argparse.ArgumentParser:
    """
    Build argument parser.
    """
    parser = argparse.ArgumentParser(
        description="CBI Coverage Tool " + version,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )
    parser.set_defaults(func=None)
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help="Display help message and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"CBI Coverage Tool {version}",
        help="Display version information and exit.",
    )

    subparsers = parser.add_subparsers(title="commands")

    compute_parser = subparsers.add_parser(
        "compute",
        help="Compute coverage.",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )
    compute_parser.set_defaults(func=_compute)
    compute_parser.add_argument(
        "-h",
        "--help",
        action="help",
        help=_help_string("Display help message and exit."),
    )
    compute_parser.add_argument(
        "-S",
        "--source-dir",
        metavar="<path>",
        dest="source_dir",
        help=_help_string("Path to source directory.", is_long=True),
        default=os.getcwd(),
    )
    compute_parser.add_argument(
        "-x",
        "--exclude",
        dest="excludes",
        metavar="<pattern>",
        action="append",
        default=[],
        help=_help_string(
            "Exclude files matching this pattern from the code base.",
            "May be specified multiple times.",
            is_long=True,
        ),
    )
    compute_parser.add_argument(
        "-o",
        "--output",
        dest="ofile",
        metavar="<output path>",
        default="coverage.json",
        help=_help_string(
            "Path to coverage JSON file.",
            "If not specified, defaults to 'coverage.json'.",
            is_long=True,
            is_last=True,
        ),
    )
    compute_parser.add_argument(
        "ifile",
        metavar="<input path>",
        help=_help_string(
            "Path to compilation database JSON file.",
            is_last=True,
        ),
    )

    return parser


def _compute(args: argparse.Namespace):
    dbpath = os.path.realpath(args.ifile)
    covpath = os.path.realpath(args.ofile)
    for path in [dbpath, covpath]:
        if not util.valid_path(path):
            raise ValueError(f"{path} is not a valid path.")
        util.ensure_ext(path, [".json"])

    source_dir = os.path.realpath(args.source_dir)

    # Run CBI configured as-if:
    # - configuration contains a single (dummy) platform
    # - codebase contains all files in the specified compilation database
    db = config.load_database(dbpath, source_dir)
    configuration = {"cli": db}
    codebase = CodeBase(source_dir, exclude_patterns=args.excludes)
    state = finder.find(source_dir, codebase, configuration)

    # Export coverage information in P3 Analysis Library format.
    covarray = []
    for filename in codebase:
        relative_path = os.path.relpath(filename, start=source_dir)

        with open(filename, "rb") as f:
            digest = hashlib.file_digest(f, "sha512")

        lines = []
        tree = state.get_tree(filename)
        association = state.get_map(filename)
        for node in [n for n in tree.walk() if isinstance(n, CodeNode)]:
            if association[node] == frozenset([]):
                continue
            lines.extend(node.lines)

        covarray.append(
            {
                "file": relative_path,
                "id": digest.hexdigest(),
                "lines": lines,
            },
        )

    util._validate_json(covarray, "coverage")
    with open(covpath, "w") as f:
        json.dump(covarray, f, indent=2)

    sys.exit(0)


def cli(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    command = args.func

    if command is None:
        parser.print_help()
        sys.exit(2)

    # Configure logging such that:
    # - All messages are written to a log file
    # - Only errors are written to the terminal
    # - Meta-warnings and statistics are generated by a WarningAggregator
    aggregator = WarningAggregator()
    log.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("cbi.log", mode="w")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(Formatter())
    file_handler.addFilter(aggregator)
    log.addHandler(file_handler)

    # Inform the user that a log file has been created.
    # 'print' instead of 'log' to ensure the message is visible in the output.
    log_path = os.path.abspath("cbi.log")
    print(f"Log file created at {log_path}")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(Formatter(colors=sys.stderr.isatty()))
    log.addHandler(stderr_handler)

    return command(args)


def main():
    try:
        cli(sys.argv[1:])
    except Exception as e:
        log.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    sys.argv[0] = "codebasin.coverage"
    main()
