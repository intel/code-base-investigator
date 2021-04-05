# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions and classes related to finding
and parsing source files as part of a code base.
"""

import logging
import collections

from . import file_parser
from . import platform
from . import preprocessor
from .walkers.tree_associator import TreeAssociator

log = logging.getLogger("codebasin")


class ParserState():
    """
    Keeps track of the overall state of the parser.
    Contains all of the SourceTree objects created from parsing the
    source files, along with association maps, that associate nodes to
    platforms.
    """

    def __init__(self, summarize_code):
        self.trees = {}
        self.maps = {}
        self.summarize_code = summarize_code

    def insert_file(self, fn):
        """
        Build a new tree for a source file, and create an association
        map for it.
        """
        if fn not in self.trees:
            parser = file_parser.FileParser(fn)
            self.trees[fn] = parser.parse_file(self.summarize_code)
            self.maps[fn] = collections.defaultdict(set)

    def get_filenames(self):
        """
        Return all of the filenames for files parsed so far.
        """
        return self.trees.keys()

    def get_tree(self, fn):
        """
        Return the SourceTree associated with a filename
        """
        if fn not in self.trees:
            return None
        return self.trees[fn]

    def get_map(self, fn):
        """
        Return the NodeAssociationMap associated with a filename
        """
        if fn not in self.maps:
            return None
        return self.maps[fn]


# FIXME: Should this be kwargs?
def find(rootdir, codebase, configuration, summarize_code=True):
    """
    Find codepaths in the files provided and return a mapping of source
    lines to platforms.
    """

    # Build a tree for each unique file for all platforms.
    state = ParserState(summarize_code)
    for f in codebase["files"]:
        state.insert_file(f)
    for p in configuration:
        for e in configuration[p]:
            if e['file'] not in codebase["files"]:
                log.warning(
                    "%s found in definition of platform %s but missing from codebase",
                    e['file'], p)
            state.insert_file(e['file'])

    # Process each tree, by associating nodes with platforms
    for p in configuration:
        for e in configuration[p]:
            file_platform = platform.Platform(p, rootdir)

            for path in e['include_paths']:
                file_platform.add_include_path(path)

            for definition in e['defines']:
                macro = preprocessor.macro_from_definition_string(definition)
                file_platform.define(macro.name, macro)

            # Process include files.
            # These modify the file_platform instance, but we throw away
            # the active nodes after processing is complete.
            for include in e['include_files']:
                include_file = file_platform.find_include_file(include)
                if include_file:
                    state.insert_file(include_file)

                    associator = TreeAssociator(state.get_tree(
                        include_file), state.get_map(include_file))
                    associator.walk(file_platform, state)

            # Process the file, to build a list of associate nodes
            associator = TreeAssociator(state.get_tree(e['file']),
                                        state.get_map(e['file']))
            associator.walk(file_platform, state)

    return state
