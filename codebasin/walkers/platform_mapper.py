# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import collections
from .tree_mapper import TreeMapper
from codebasin.preprocessor import FileNode, CodeNode

log = logging.getLogger('codebasin')


class PlatformMapper(TreeMapper):
    """
    Specific TreeMapper that builds a mapping of nodes to platforms.
    """

    def __init__(self, codebase, _tree=None, _node_associations=None):
        super().__init__(_tree, _node_associations)
        self.codebase = codebase
        self._null_set = frozenset([])

    def _map_node(self, _node, _map):
        """
        Map a specific node to its platform set, and descend into the
        children nodes.
        """
        # Do not map files that the user does not consider to be part of
        # the codebase
        if isinstance(_node, FileNode) and (_node.filename not in self.codebase["files"] or _node.filename in self.codebase["exclude_files"]):
            return

        if isinstance(_node, CodeNode):
            association = _map[_node]
            platform = frozenset(association)
            self.line_map[platform] += _node.num_lines

        for child in _node.children:
            self._map_node(child, _map)
