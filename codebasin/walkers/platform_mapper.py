# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os

from codebasin.preprocessor import CodeNode, FileNode
from codebasin.walkers.tree_mapper import TreeMapper

log = logging.getLogger("codebasin")


def exclude(filename, cb):
    if filename in cb["exclude_files"]:
        log.info(f"Excluding {filename}; matches 'exclude_files'.")
        return True
    elif filename in cb["files"]:
        return False
    else:
        path = os.path.realpath(filename)
        if not path.startswith(cb["rootdir"]):
            log.info(f"Excluding {filename}; outside of root directory.")
            return True

    return False


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
        if isinstance(_node, FileNode) and exclude(
            _node.filename,
            self.codebase,
        ):
            return

        if isinstance(_node, CodeNode):
            association = _map[_node]
            platform = frozenset(association)
            self.line_map[platform] += _node.num_lines

        for child in _node.children:
            self._map_node(child, _map)
