#!/usr/bin/env python3
# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
This script is the main executable of Code Base Investigator.

usage: codebasin.py [-h] [-c FILE] [-v] [-q] [-r DIR] [-R REPORT [REPORT ...]]

optional arguments:
  -h, --help            show this help message and exit
  -c FILE, --config FILE
                        configuration file (default: <DIR>/config.yaml)
  -v, --verbose         verbosity level
  -q, --quiet           quiet level
  -r DIR, --rootdir DIR
                        Set working root directory (default .)
  -R REPORT [REPORT ...], --report REPORT [REPORT ...]
                        desired output reports (default: all)
"""

import argparse
import os
import sys
import logging

from codebasin import config, finder, report, util
from codebasin.walkers.platform_mapper import PlatformMapper

version = 1.05


def report_enabled(name):
    """
    Return true if the report with the specified name is enabled.
    """
    if "all" in args.reports:
        return True
    return name in args.reports


def guess_project_name(config_path):
    """
    Guess a useful name from the given path so that we can pick
    meaningful filenames for output.
    """
    fullpath = os.path.realpath(config_path)
    (thedir, thename) = os.path.split(fullpath)
    if config_path == 'config.yaml':
        (base, end) = os.path.split(thedir)
        res = end.strip()
    else:
        (base, end) = os.path.splitext(thename)
        res = base.strip()
    if not res:
        logging.getLogger("codebasin").warning("Can't guess meaningful output name from input")
        res = "unknown"
    return res


if __name__ == '__main__':

    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Code Base Investigator v" + str(version))
    parser.add_argument('-r', '--rootdir', dest="rootdir", metavar='DIR',
                        default=os.getcwd(), type=str,
                        help="Set working root directory (default .)")
    parser.add_argument('-c', '--config', dest='config_file', metavar='FILE', action='store',
                        help='configuration file (default: <DIR>/config.yaml)')
    parser.add_argument('-v', '--verbose', dest='verbose',
                        action='count', default=0, help='increase verbosity level')
    parser.add_argument('-q', '--quiet', dest='quiet',
                        action='count', default=0, help='decrease verbosity level')
    parser.add_argument('-R', '--report', dest='reports', metavar='REPORT', default=['all'],
                        choices=['all', 'summary', 'clustering'], nargs='+',
                        help='desired output reports (default: all)')
    parser.add_argument('--batchmode', dest='batchmode', action='store_true', default=False,
                        help="Set batch mode (additional output for bulk operation.)")
    args = parser.parse_args()

    stdout_log = logging.StreamHandler(sys.stdout)
    stdout_log.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
    logging.getLogger("codebasin").addHandler(stdout_log)
    logging.getLogger("codebasin").setLevel(
        max(1, logging.WARNING - 10 * (args.verbose - args.quiet)))
    rootdir = os.path.realpath(args.rootdir)

    if args.config_file is None:
        config_file = os.path.join(rootdir, "config.yaml")
    else:
        config_file = args.config_file
    # Load the configuration file into a dict
    if not util.ensure_yaml(config_file):
        logging.getLogger("codebasin").error(
            "Configuration file does not have YAML file extension.")
        sys.exit(1)
    codebase, configuration = config.load(config_file, rootdir)

    # Parse the source tree, and determine source line associations.
    # The trees and associations are housed in state.
    state = finder.find(rootdir, codebase, configuration)

    # Count lines for platforms
    platform_mapper = PlatformMapper(codebase)
    setmap = platform_mapper.walk(state)

    output_prefix = os.path.realpath(guess_project_name(config_file))

    if args.batchmode and (report_enabled("summary") or report_enabled("clustering")):
        print(f"Config file: {config_file}")
        print(f"Root: {rootdir}")

    # Print summary report
    if report_enabled("summary"):
        summary = report.summary(setmap)
        if summary is not None:
            print(summary)

    # Print clustering report
    if report_enabled("clustering"):
        clustering_output_name = output_prefix + "-dendrogram.png"
        clustering = report.clustering(clustering_output_name, setmap)
        if clustering is not None:
            print(clustering)

    sys.exit(0)
