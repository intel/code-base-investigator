#!/usr/bin/env python3.6
# Copyright (C) 2019-2020 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Parse source file, reporting sloc and physical lines.
Can optionally print logical line regions and cleaned lines.
"""

import os
import sys
import re

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

# pylint: disable=wrong-import-position
from codebasin.file_source import get_file_source


def file_sloc(path, verbose=False):
    """
    Process file in path, reporting total_sloc/loc. Optionally print logical regions.
    """
    file_source = get_file_source(path)
    if not file_source:
        raise RuntimeError(f"{path} doesn't appear to be a language this tool can process")
    with open(path, mode='r', errors='replace') as source_file:
        walker = file_source(source_file, relaxed=False)
        try:
            while True:
                logical_line = next(walker)
                if verbose:
                    print(f"{path} [{logical_line.current_physical_start}," +
                          f" {logical_line.current_physical_end}) ({logical_line.local_sloc}):"
                          f" {logical_line.flushed_line} {logical_line.category}")
        except StopIteration as it:
             # pylint: disable=unpacking-non-sequence
            total_sloc, physical_loc = it.value

    return (path, total_sloc, physical_loc)


def walk_sloc(in_root, regexp, verbose=False):
    """
    Run file_sloc on each file that matches regexp under root path.
    """
    for root, _, files in os.walk(in_root):
        for current_file in files:
            full_path = os.path.join(root, current_file)
            if regexp.match(full_path):
                try:
                    (filename, total_sloc, physical_loc) = file_sloc(full_path)
                    if verbose:
                        print(f"{filename}, {total_sloc}, {physical_loc}")
                except FileNotFoundError:
                    pass


def sloc_translate(args):
    """
    Toplevel routine for script.
    """
    if len(args) == 2:
        (filename, total_sloc, physical_loc) = file_sloc(args[1], verbose=True)
        print(f"{filename}, {total_sloc}, {physical_loc}")
    elif len(args) == 3:
        walk_sloc(args[1], re.compile(args[2]), verbose=True)
    else:
        print("Expected either 1 argument (a single file to parse" +
              " and print) or 2 (a directory root & file pattern)")


if __name__ == '__main__':
    sloc_translate(sys.argv)
