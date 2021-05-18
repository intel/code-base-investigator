# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import collections

from .tree_walker import TreeWalker

log = logging.getLogger('codebasin')


class TreeMapper(TreeWalker):
    """
    Used to build a dictionary of associations, along with how many
    lines of code each is associated with.
    """

    def __init__(self, _tree, _node_associations):
        super().__init__(_tree, _node_associations)
        self.line_map = collections.defaultdict(int)

    def walk(self, state):
        """
        Generic tree mapping method. Returns the constructed map.
        """
        if not self.line_map:
            for fn in state.get_filenames():
                self._map_node(state.get_tree(fn).root, state.get_map(fn))
        return self.line_map

    def _map_node(self, node, _map):
        """
        Map a specific node, and descend into the children nodes.
        """
        # pass
