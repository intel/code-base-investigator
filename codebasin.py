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
import warnings

from codebasin import config, finder, report, util
from codebasin.walkers.platform_mapper import PlatformMapper

version = "1.1.1"


def guess_project_name(config_path):
    """
    Guess a useful name from the given path so that we can pick
    meaningful filenames for output.
    """
    fullpath = os.path.realpath(config_path)
    (thedir, thename) = os.path.split(fullpath)
    if config_path == "config.yaml":
        (base, end) = os.path.split(thedir)
        res = end.strip()
    else:
        (base, end) = os.path.splitext(thename)
        res = base.strip()
    if not res:
        logging.getLogger("codebasin").warning(
            "Can't guess meaningful output name from input",
        )
        res = "unknown"
    return res


def main():
    # Read command-line arguments
    parser = argparse.ArgumentParser(
        description="Code Base Investigator v" + str(version),
    )
    parser.add_argument(
        "-r",
        "--rootdir",
        dest="rootdir",
        metavar="DIR",
        default=None,
        help="Set working root directory (default .)",
    )
    parser.add_argument(
        "-S",
        "--source-dir",
        metavar="<path>",
        dest="source_dir",
        default=None,
        help="Set path to source directory. "
        + "The default is the current directory.",
    )
    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        metavar="FILE",
        action="store",
        help="configuration file (default: <DIR>/config.yaml)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="increase verbosity level",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        dest="quiet",
        action="count",
        default=0,
        help="decrease verbosity level",
    )
    parser.add_argument(
        "-R",
        "--report",
        dest="reports",
        metavar="REPORT",
        default=["all"],
        choices=["all", "summary", "clustering"],
        nargs="+",
        help="desired output reports (default: all)",
    )
    parser.add_argument(
        "-d",
        "--dump",
        dest="dump",
        metavar="<file.json>",
        action="store",
        help="dump out annotated platform/parsing tree to <file.json>",
    )
    parser.add_argument(
        "--batchmode",
        dest="batchmode",
        action="store_true",
        default=False,
        help="Set batch mode (additional output for bulk operation.)",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        dest="excludes",
        metavar="<pattern>",
        action="append",
        default=[],
        help="Exclude files matching this pattern from the code base. "
        + "May be specified multiple times.",
    )
    parser.add_argument(
        "-p",
        "--platform",
        dest="platforms",
        metavar="<platform>",
        action="append",
        default=[],
        help="Add the specified platform to the analysis. "
        + "May be a name or a path to a compilation database. "
        + "May be specified multiple times. "
        + "If not specified, all known platforms will be included.",
    )

    args = parser.parse_args()

    stdout_log = logging.StreamHandler(sys.stdout)
    stdout_log.setFormatter(logging.Formatter("[%(levelname)-8s] %(message)s"))
    logging.getLogger("codebasin").addHandler(stdout_log)
    logging.getLogger("codebasin").setLevel(
        max(1, logging.WARNING - 10 * (args.verbose - args.quiet)),
    )

    # Warnings for deprecated functionality with no planned replacement.
    if args.batchmode:
        warnings.warn("--batchmode will be removed in a future release.")
    if args.dump:
        warnings.warn("--dump will be removed in a future release.")

    # Determine the root directory based on the -S and -r flags.
    rootpath = None
    if args.source_dir and args.rootdir:
        raise RuntimeError(
            "Cannot specify both --source-dir (-S) and --rootdir (-r).",
        )
    if not args.source_dir and not args.rootdir:
        rootpath = os.getcwd()
    elif args.source_dir:
        rootpath = args.source_dir
    elif args.rootdir:
        warnings.warn(
            "--rootdir (-r) is deprecated. Use --source-dir (-S) instead.",
        )
        rootpath = args.rootdir
    rootdir = os.path.realpath(rootpath)

    # Process the -p flag first to infer wider context.
    filtered_platforms = []
    additional_platforms = []
    for p in args.platforms:
        # If it's a path, it has to be a compilation database.
        if os.path.exists(p):
            if not os.path.splitext(p)[1] == ".json":
                raise RuntimeError(f"Platform file {p} must end in .json.")
            additional_platforms.append(p)
            continue

        # Otherwise, treat it as a name in the configuration file.
        # Explain the logic above in cases that look suspiciously like paths.
        if "/" in p or os.path.splitext(p)[1] == ".json":
            logging.getLogger("codebasin").warning(
                f"{p} doesn't exist, so will be treated as a name.",
            )
        filtered_platforms.append(p)

    # If no additional platforms are specified, a config file is required.
    config_file = args.config_file
    if len(additional_platforms) == 0 and config_file is None:
        config_file = os.path.join(rootdir, "config.yaml")
        if not os.path.exists(config_file):
            raise RuntimeError(f"Could not find config file {config_file}")

    # Set up a default codebase and configuration object.
    codebase = {
        "files": [],
        "platforms": [],
        "exclude_files": set(),
        "exclude_patterns": args.excludes,
        "rootdir": rootdir,
    }
    configuration = {}

    # Load the configuration file if it exists, obeying any platform filter.
    if config_file is not None:
        if not util.ensure_yaml(config_file):
            logging.getLogger("codebasin").error(
                "Configuration file does not have YAML file extension.",
            )
            sys.exit(1)
        codebase, configuration = config.load(
            config_file,
            rootdir,
            exclude_patterns=args.excludes,
            filtered_platforms=filtered_platforms,
        )

    # Extend configuration with any additional platforms.
    for p in additional_platforms:
        name = os.path.splitext(os.path.basename(p))[0]
        if name in codebase["platforms"]:
            raise RuntimeError(f"Platform name {p} conflicts with {name}.")
        db = config.load_database(p, rootdir)
        configuration.update({name: db})

    # Parse the source tree, and determine source line associations.
    # The trees and associations are housed in state.
    legacy_warnings = True if config_file else False
    state = finder.find(
        rootdir,
        codebase,
        configuration,
        legacy_warnings=legacy_warnings,
    )

    # Count lines for platforms
    platform_mapper = PlatformMapper(codebase)
    setmap = platform_mapper.walk(state)

    if args.dump:
        if util.ensure_json(args.dump):
            report.annotated_dump(args.dump, state)
        else:
            logging.getLogger("codebasin").warning(
                "Output path for annotation dump does not end with .json: "
                f"'{args.dump}'. Skipping dump.",
            )

    def report_enabled(name):
        if "all" in args.reports:
            return True
        return name in args.reports

    if args.batchmode and (
        report_enabled("summary") or report_enabled("clustering")
    ):
        print(f"Config file: {config_file}")
        print(f"Root: {rootdir}")

    # Print summary report
    if report_enabled("summary"):
        summary = report.summary(setmap)
        if summary is not None:
            print(summary)

    # Print clustering report
    if report_enabled("clustering"):
        if config_file is None:
            platform_names = [p[0] for p in args.platforms]
            output_prefix = "-".join(platform_names)
        else:
            output_prefix = os.path.realpath(guess_project_name(config_file))
        clustering_output_name = output_prefix + "-dendrogram.png"
        clustering = report.clustering(clustering_output_name, setmap)
        if clustering is not None:
            print(clustering)

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.getLogger("codebasin").error(str(e))
        sys.exit(1)
