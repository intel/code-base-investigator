#!/usr/bin/env python3
# Copyright (C) 2019-2023 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Calculates the lines of code used by a single platform, as described by a
compilation database, and outputs coverage in the P3 Analysis Library format.
"""

import argparse
import json
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from codebasin.walkers.exporter import Exporter  # nopep8
import codebasin.config as config  # nopep8
import codebasin.finder as finder  # nopep8
import codebasin.util as util  # nopep8

if __name__ == '__main__':

    # Read command-line arguments
    desc = 'Code Base Investigator Coverage Tool'
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument('ifile', metavar='INPUT',
                        help="path to compilation database JSON file")
    parser.add_argument('ofile', metavar='OUTPUT',
                        help="path to coverage JSON file")
    args = parser.parse_args()

    dbpath = os.path.realpath(args.ifile)
    covpath = os.path.realpath(args.ofile)
    for path in [dbpath, covpath]:
        if not util.valid_path(path):
            raise ValueError("%s is not a valid path." % path)
        if not util.ensure_ext(path, ['.json']):
            raise ValueError("%s is not a JSON file." % path)

    # Ensure regular CBI output goes to stderr
    stderr_log = logging.StreamHandler(sys.stderr)
    stderr_log.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
    logging.getLogger('codebasin').addHandler(stderr_log)
    logging.getLogger('codebasin').setLevel(logging.WARNING)

    # Run CBI configured as-if:
    # - configuration contains a single (dummy) platform
    # - codebase contains all files in the specified compilation database
    db = config.load_database(dbpath, os.getcwd())
    configuration = {'cli': db}
    files = [e['file'] for e in db]
    codebase = {'files': files, 'platforms': ['cli'], 'exclude_files': []}

    state = finder.find(os.getcwd(), codebase, configuration)

    exporter = Exporter(codebase)
    exports = exporter.walk(state)
    for p in codebase['platforms']:
        covarray = []
        for filename in exports[p]:
            covobject = {"file": filename, "regions": []}
            for region in exports[p][filename]:
                covobject["regions"].append(region)
            covarray.append(covobject)
        json_string = json.dumps(covarray)
        util.validate_coverage_json(json_string)
        with open(covpath, 'w') as fp:
            fp.write(json_string)
