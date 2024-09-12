#!/usr/bin/env python3
# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
This script is the main executable of Code Base Investigator.
"""

import argparse
import logging
import os
import sys

from codebasin import CodeBase, config, finder, report, util
from codebasin.walkers.platform_mapper import PlatformMapper

version = "1.2.0"


def _help_string(*lines: str, is_long=False, is_last=False):
    """
    Parameters
    ----------
    *lines: str
        Each line in the help string.

    is_long: bool
        A flag indicating whether the option is long enough to generate an
        initial newline by default.

    is_last: bool
        A flag indicating whether the option is the last in the list.

    Returns
    -------
        An argparse help string formatted as a paragraph.
    """
    result = ""

    # A long option like --exclude will force a newline.
    if not is_long:
        result = "\n"

    # argparse.HelpFormatter indents by 24 characters.
    # We cannot override this directly, but can delete them with backspaces.
    lines = ["\b" * 20 + x for x in lines]

    # The additional space is required for argparse to respect newlines.
    result += "\n".join(lines)

    if not is_last:
        result += "\n "

    return result


def main():
    # Read command-line arguments
    parser = argparse.ArgumentParser(
        description="Code Base Investigator " + str(version),
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
        version=f"Code Base Investigator {version}",
        help=_help_string("Display version information and exit."),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help=_help_string("Increase verbosity level."),
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="count",
        default=0,
        help=_help_string("Decrease verbosity level."),
    )
    parser.add_argument(
        "-R",
        "--report",
        dest="reports",
        metavar="<report>",
        action="append",
        default=[],
        choices=["all", "summary", "clustering"],
        help=_help_string(
            "Generate a report of the specified type.",
            "May be specified multiple times.",
            "If not specified, all reports will be generated.",
            is_long=True,
        ),
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

    args = parser.parse_args()

    stdout_log = logging.StreamHandler(sys.stdout)
    stdout_log.setFormatter(logging.Formatter("[%(levelname)-8s] %(message)s"))
    logging.getLogger("codebasin").addHandler(stdout_log)
    logging.getLogger("codebasin").setLevel(
        max(1, logging.WARNING - 10 * (args.verbose - args.quiet)),
    )

    # If no specific report was specified, generate all reports.
    # Handled here to prevent "all" always being in the list.
    if len(args.reports) == 0:
        args.reports = ["all"]

    # Determine the root directory based on where codebasin is run.
    rootdir = os.path.realpath(os.getcwd())

    # Set up a default configuration object.
    configuration = {}

    # Load the analysis file if it exists.
    if args.analysis_file is not None:
        path = os.path.realpath(args.analysis_file)
        if os.path.exists(path):
            if not os.path.splitext(path)[1] == ".toml":
                raise RuntimeError(f"Analysis file {path} must end in .toml.")

        with util.safe_open_read_nofollow(path, "rb") as f:
            try:
                analysis_toml = util._load_toml(f, "analysis")
            except BaseException:
                raise ValueError("Analysis file failed validation")

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
        legacy_warnings=False,
    )

    # Count lines for platforms
    platform_mapper = PlatformMapper(codebase)
    setmap = platform_mapper.walk(state)

    def report_enabled(name):
        if "all" in args.reports:
            return True
        return name in args.reports

    # Print summary report
    if report_enabled("summary"):
        summary = report.summary(setmap)
        if summary is not None:
            print(summary)

    # Print clustering report
    if report_enabled("clustering"):
        basename = os.path.basename(args.analysis_file)
        filename = os.path.splitext(basename)[0]
        output_prefix = "-".join([filename] + args.platforms)

        clustering_output_name = output_prefix + "-dendrogram.png"
        clustering = report.clustering(clustering_output_name, setmap)
        if clustering is not None:
            print(clustering)

    sys.exit(0)


if __name__ == "__main__":
    try:
        sys.argv[0] = "codebasin"
        main()
    except Exception as e:
        logging.getLogger("codebasin").error(str(e))
        sys.exit(1)