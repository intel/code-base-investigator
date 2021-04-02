#!/usr/bin/env python3
# Copyright (C) 2019-2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Preprocess a source file using the CBI preprocessor.
"""

import argparse
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# pylint: disable=wrong-import-position
from codebasin.walkers.source_printer import SourcePrinter, PreprocessedSourcePrinter  # nopep8
import codebasin.finder as finder  # nopep8

if __name__ == '__main__':

    # Read command-line arguments
    parser = argparse.ArgumentParser(description="Code Base Investigator Preprocessor")
    parser.add_argument('-I', dest='include_paths', metavar='PATH', action='append', default=[],
                        help="add to the include path")
    parser.add_argument(
        '-include',
        dest='include_files',
        metavar='PATH',
        action='append',
        default=[],
        help="add to the include files")
    parser.add_argument('-D', dest='defines', metavar='DEFINE', action='append', default=[],
                        help="define a macro")
    parser.add_argument('filename', metavar='FILE', action='store')
    args = parser.parse_args()

    # Ensure regular CBI output goes to stderr
    # Allows preprocessed output to print to stdout by default
    stderr_log = logging.StreamHandler(sys.stderr)
    stderr_log.setFormatter(logging.Formatter('[%(levelname)-8s] %(message)s'))
    logging.getLogger("codebasin").addHandler(stderr_log)
    logging.getLogger("codebasin").setLevel(logging.WARNING)

    # Parse file and construct source tree
    #fileparser = FileParser(file_path)
    #source_tree = fileparser.parse_file()

    # Run CBI configured as-if:
    # - codebase contains a single file (the file being preprocessed)
    # - configuration contains a single platform (corresponding to flags)
    file_path = os.path.realpath(args.filename)
    codebase = {"files": [file_path], "platforms": ["cli"]}
    configuration = {"cli": [{"file": file_path,
                              "defines": args.defines,
                              "include_paths": args.include_paths,
                              "include_files": args.include_files}]}
    state = finder.find(os.getcwd(), codebase, configuration)

    #source_printer = SourcePrinter(source_tree)
    # source_printer.walk()
    source_tree = state.get_tree(file_path)
    node_associations = state.get_map(file_path)

    source_printer = SourcePrinter(source_tree)
    source_printer.walk()
    print("---")
    source_printer = PreprocessedSourcePrinter(source_tree, node_associations)
    source_printer.walk()
