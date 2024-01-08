# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains functions and classes related to finding
and parsing source files as part of a code base.
"""

import collections
import logging
import os

from codebasin import file_parser, platform, preprocessor, util
from codebasin.language import FileLanguage
from codebasin.walkers.tree_associator import TreeAssociator

log = logging.getLogger("codebasin")


class FileInfo:
    """
    Data class storing (path, size, sha) for a file.
    """

    def __init__(self, path, size=None, sha=None):
        self.path = path
        self.size = size
        self.sha = sha


class ParserState:
    """
    Keeps track of the overall state of the parser.
    Contains all of the SourceTree objects created from parsing the
    source files, along with association maps, that associate nodes to
    platforms.
    """

    def __init__(self, summarize_only):
        self.trees = {}
        self.maps = {}
        self.langs = {}
        self.summarize_only = summarize_only
        self.fileinfo = collections.defaultdict(list)
        self.merge_duplicates = True

    def _map_filename(self, fn):
        """
        Map the real filename to an internal filename used by the parser.
        Enables duplicate files to be merged.
        """
        if not self.merge_duplicates:
            return fn

        # The first time we encounter a filename, store limited info
        bn = os.path.basename(fn)
        if bn not in self.fileinfo:
            self.fileinfo[bn] = [FileInfo(fn)]
            return fn

        # If filename has been encountered, check for matching size/hash
        size = os.path.getsize(fn)
        sha = None
        for fi in self.fileinfo[bn]:
            # Fill in missing size information
            if fi.size is None:
                fi.size = os.path.getsize(fi.path)

            # If sizes don't match, the file is different
            if fi.size != size:
                continue

            # Fill in missing hash information
            if sha is None:
                sha = util.compute_file_hash(fn)
            if fi.sha is None:
                fi.sha = util.compute_file_hash(fi.path)

            # Use hash to determine if file is duplicate or not
            if fi.sha != sha:
                continue
            return fi.path

        # If no match, this is the first time encountering this file
        self.fileinfo[bn].append(FileInfo(fn, size, sha))
        return fn

    def insert_file(self, fn, language=None):
        """
        Build a new tree for a source file, and create an association
        map for it.
        """
        fn = self._map_filename(fn)
        if fn not in self.trees:
            parser = file_parser.FileParser(fn)
            self.trees[fn] = parser.parse_file(
                summarize_only=self.summarize_only,
                language=language,
            )
            self.maps[fn] = collections.defaultdict(set)
            if language:
                self.langs[fn] = language
            else:
                self.langs[fn] = FileLanguage(fn).get_language()

    def get_filenames(self):
        """
        Return all of the filenames for files parsed so far.
        """
        return self.trees.keys()

    def get_tree(self, fn):
        """
        Return the SourceTree associated with a filename
        """
        fn = self._map_filename(fn)
        if fn not in self.trees:
            return None
        return self.trees[fn]

    def get_map(self, fn):
        """
        Return the NodeAssociationMap associated with a filename
        """
        fn = self._map_filename(fn)
        if fn not in self.maps:
            return None
        return self.maps[fn]


def find(rootdir, codebase, configuration, *, summarize_only=True):
    """
    Find codepaths in the files provided and return a mapping of source
    lines to platforms.
    """

    # Build a tree for each unique file for all platforms.
    state = ParserState(summarize_only)
    for f in codebase["files"]:
        state.insert_file(f)
    for p in configuration:
        for e in configuration[p]:
            if e["file"] not in codebase["files"]:
                filename = e["file"]
                log.warning(
                    f"{filename} found in definition of platform {p} "
                    + "but missing from codebase",
                )
            state.insert_file(e["file"])

    # Process each tree, by associating nodes with platforms
    for p in configuration:
        for e in configuration[p]:
            file_platform = platform.Platform(p, rootdir)

            for path in e["include_paths"]:
                file_platform.add_include_path(path)

            for definition in e["defines"]:
                macro = preprocessor.macro_from_definition_string(definition)
                file_platform.define(macro.name, macro)

            # Process include files.
            # These modify the file_platform instance, but we throw away
            # the active nodes after processing is complete.
            for include in e["include_files"]:
                include_file = file_platform.find_include_file(
                    include,
                    os.path.dirname(e["file"]),
                )
                if include_file:
                    state.insert_file(include_file)

                    associator = TreeAssociator(
                        state.get_tree(include_file),
                        state.get_map(include_file),
                    )
                    associator.walk(file_platform, state)

            # Process the file, to build a list of associate nodes
            associator = TreeAssociator(
                state.get_tree(e["file"]),
                state.get_map(e["file"]),
            )
            associator.walk(file_platform, state)

    return state
