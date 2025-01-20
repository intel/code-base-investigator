#!/usr/bin/env python3
# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import logging
import os
import sys

from codebasin import CodeBase, config, finder, report, util

# TODO: Refactor to avoid imports from __main__
from codebasin.__main__ import Formatter, _help_string, version

log = logging.getLogger("codebasin")


def _build_parser() -> argparse.ArgumentParser:
    """
    Build argument parser.
    """
    parser = argparse.ArgumentParser(
        description="CBI Tree Tool " + version,
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=False,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        help=_help_string("Display help message and exit."),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"CBI Coverage Tool {version}",
        help=_help_string("Display version information and exit."),
    )
    parser.add_argument(
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
    parser.add_argument(
        "-p",
        "--platform",
        dest="platforms",
        metavar="<platform>",
        action="append",
        default=[],
        help=_help_string(
            "Include the specified platform in the analysis.",
            "May be specified multiple times.",
            "If not specified, all platforms will be included.",
            is_long=True,
            is_last=True,
        ),
    )

    parser.add_argument(
        "analysis_file",
        metavar="<analysis-file>",
        help=_help_string(
            "TOML file describing the analysis to be performed, "
            + "including the codebase and platform descriptions.",
            is_last=True,
        ),
    )

    return parser


def _tree(args: argparse.Namespace):
    # TODO: Refactor this to avoid duplication in __main__
    # Determine the root directory based on where codebasin is run.
    rootdir = os.path.abspath(os.getcwd())

    # Set up a default configuration object.
    configuration = {}

    # Load the analysis file if it exists.
    if args.analysis_file is not None:
        path = os.path.abspath(args.analysis_file)
        if os.path.exists(path):
            if not os.path.splitext(path)[1] == ".toml":
                raise RuntimeError(f"Analysis file {path} must end in .toml.")

        with open(path, "rb") as f:
            analysis_toml = util._load_toml(f, "analysis")

        if "codebase" in analysis_toml:
            if "exclude" in analysis_toml["codebase"]:
                args.excludes += analysis_toml["codebase"]["exclude"]

        for name in args.platforms:
            if name not in analysis_toml["platform"].keys():
                raise KeyError(
                    f"Platform {name} requested on the command line "
                    + "does not exist in the configuration file.",
                )

        cmd_platforms = args.platforms.copy()
        for name in analysis_toml["platform"].keys():
            if cmd_platforms and name not in cmd_platforms:
                continue
            if "commands" not in analysis_toml["platform"][name]:
                raise ValueError(f"Missing 'commands' for platform {name}")
            p = analysis_toml["platform"][name]["commands"]
            db = config.load_database(p, rootdir)
            args.platforms.append(name)
            configuration.update({name: db})

    # Construct a codebase object associated with the root directory.
    codebase = CodeBase(rootdir, exclude_patterns=args.excludes)

    # Parse the source tree, and determine source line associations.
    # The trees and associations are housed in state.
    state = finder.find(
        rootdir,
        codebase,
        configuration,
        show_progress=True,
    )

    # Print the file tree.
    report.files(codebase, state)
    sys.exit(0)


def cli(argv: list[str]) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # Configure logging such that:
    # - All messages are written to a log file
    # - Only errors are written to the terminal
    log.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler("cbi.log", mode="w")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(Formatter())
    log.addHandler(file_handler)

    # Inform the user that a log file has been created.
    # 'print' instead of 'log' to ensure the message is visible in the output.
    log_path = os.path.abspath("cbi.log")
    print(f"Log file created at {log_path}")

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.ERROR)
    stderr_handler.setFormatter(Formatter(colors=sys.stderr.isatty()))
    log.addHandler(stderr_handler)

    return _tree(args)


def main():
    try:
        cli(sys.argv[1:])
    except Exception as e:
        log.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    sys.argv[0] = "codebasin.tree"
    main()
