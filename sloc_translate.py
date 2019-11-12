#!/usr/bin/env python3.6
# Copyright (C) 2019-2020 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

from codebasin.c_source import get_file_source
import os
import sys
import re

def file_sloc(path, verbose=False):
    file_source = get_file_source(path)
    if not file_source:
        raise RuntimeError(f"{path} doesn't appear to be a language this tool can process")
    with open(path, mode='r', errors='replace') as source_file:
        walker = file_source(source_file, relaxed=False)
        try:
            while True:
                (interval, sloc, line, line_cat) = next(walker)
                if verbose:
                    print(f"{path} [{interval[0]}, {interval[1]}) ({sloc}): {line} {line_cat}")
        except StopIteration as it:
            total_sloc, physical_loc = it.value

    return (path, total_sloc, physical_loc)

def walk_sloc(root, regexp, verbose=False):
    for root, dirs, files in os.walk(root):
        for f in files:
            full_path = os.path.join(root, f)
            if regexp.match(full_path):
                try:
                    (filename, total_sloc, physical_loc)  = file_sloc(full_path)
                    print(f"{filename}, {total_sloc}, {physical_loc}")
                except FileNotFoundError:
                    pass

if __name__ == '__main__':
    if len(sys.argv) == 2:
        filename = sys.argv[1]
        (filename, total_sloc, physical_loc)  = file_sloc(filename, verbose=True)
        print(f"{filename}, {total_sloc}, {physical_loc}")
    elif len(sys.argv) == 3:
        walk_sloc(sys.argv[1], re.compile(sys.argv[2]))
    else:
        print("Expected either 1 argument (a single file to parse and print) or 2 (a directory root & file pattern)")
