#!/usr/bin/env python3
# Copyright (C) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Preprocess a source file using the codebasin preprocessor.
"""

import argparse
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# pylint: disable=wrong-import-position
from codebasin.file_parser import FileParser  # nopep8


if __name__ == '__main__':

    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Code Base Investigator Preprocessor")
    parser.add_argument('-I', dest='includes', metavar='PATH', action='append', default=[],
                        help="add to the include path")
    parser.add_argument('-D', dest='defines', metavar='DEFINE', action='append', default=[],
                        help="define a macro")
    parser.add_argument('filename', metavar='FILE', action='store')
    args = parser.parse_args()

    stderr_log = logging.StreamHandler(sys.stderr)
    stderr_log.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
    logging.getLogger("codebasin").addHandler(stderr_log)
    logging.getLogger("codebasin").setLevel(logging.WARNING)

    # Open file for parsing
    fileparser = FileParser(os.path.realpath(args.filename))
    source_tree = fileparser.parse_file()
    print(source_tree)
