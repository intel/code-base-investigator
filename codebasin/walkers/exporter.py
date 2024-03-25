# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import collections
import logging

from codebasin import util
from codebasin.preprocessor import CodeNode, FileNode
from codebasin.walkers.platform_mapper import exclude
from codebasin.walkers.tree_walker import TreeWalker

log = logging.getLogger("codebasin")


class Exporter(TreeWalker):
    """
    Build a per-platform list of mappings.
    """

    def __init__(self, codebase, *, hash_filenames=True, export_regions=True):
        super().__init__(None, None)
        self.codebase = codebase
        self.exports = None
        self.hash_filenames = hash_filenames
        self.export_regions = export_regions

    def walk(self, state):
        self.exports = collections.defaultdict(
            lambda: collections.defaultdict(list),
        )
        for fn in state.get_filenames():
            if self.hash_filenames:
                fn = util.compute_file_hash(fn)
            self._export_node(
                fn,
                state.get_tree(fn).root,
                state.get_map(fn),
            )
        return self.exports

    def _export_node(self, _filename, _node, _map):
        # Do not export files that the user does not consider to be part of
        # the codebase
        if isinstance(_node, FileNode) and exclude(
            _node.filename,
            self.codebase,
        ):
            return

        if isinstance(_node, CodeNode):
            association = _map[_node]
            for p in frozenset(association):
                if self.export_regions:
                    start_line = _node.start_line
                    end_line = _node.end_line
                    num_lines = _node.num_lines
                    self.exports[p][_filename].append(
                        (start_line, end_line, num_lines),
                    )
                else:
                    lines = _node.lines
                    self.exports[p][_filename].append(lines)

        next_filename = _filename
        if isinstance(_node, FileNode):
            next_filename = _node.filename
        for child in _node.children:
            self._export_node(next_filename, child, _map)
