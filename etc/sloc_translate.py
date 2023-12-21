#!/usr/bin/env python3.6
# Copyright (C) 2019-2020 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Parse source file, reporting sloc and physical lines.
Can optionally print logical line regions and cleaned lines.
"""

import os
import sys
from pathlib import Path

from codebasin.file_source import get_file_source
from codebasin.util import safe_open_read_nofollow


def file_sloc(path, verbose=False):
    """
    Process file in path, reporting total_sloc/loc.
    Optionally print logical regions.
    """
    file_source = get_file_source(path)
    if not file_source:
        raise RuntimeError(
            f"{path} doesn't appear to be a language this tool can process",
        )
    with safe_open_read_nofollow(
        path,
        mode="r",
        errors="replace",
    ) as source_file:
        walker = file_source(source_file, relaxed=False)
        try:
            while True:
                logical_line = next(walker)
                if verbose:
                    start = logical_line.current_physical_start
                    end = logical_line.current_physical_end
                    sloc = logical_line.local_sloc
                    flushed = logical_line.flushed_line
                    category = logical_line.category
                    print(
                        f"{path} [{start}, {end}) ({sloc}): "
                        + f"{flushed} {category}",
                    )
        except StopIteration as it:
            total_sloc, physical_loc = it.value

    return (path, total_sloc, physical_loc)


def walk_sloc(in_root, extensions, verbose=False):
    """
    Run file_sloc on each file that matches regexp under root path.
    """
    in_root = os.path.realpath(in_root)
    for root, _, files in os.walk(in_root):
        for current_file in files:
            full_path = os.path.realpath(os.path.join(root, current_file))
            if Path(full_path).suffix in extensions:
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
        path = os.path.realpath(args[1])
        (filename, total_sloc, physical_loc) = file_sloc(path, verbose=True)
        print(f"{filename}, {total_sloc}, {physical_loc}")
    elif len(args) == 3:
        cleaned = [f".{x}" for x in args[2].split(",")]
        walk_sloc(args[1], cleaned, verbose=True)
    else:
        print(
            "Expected either 1 argument (a single file to parse"
            + " and print) or 2 (a directory root & file pattern)",
        )


if __name__ == "__main__":
    sloc_translate(sys.argv)
