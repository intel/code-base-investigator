# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import collections

from .tree_walker import TreeWalker

log = logging.getLogger('codebasin')

class TreePrinter(TreeWalker):
    """
    Specific TreeWalker that prints the nodes for the tree
    (with appropriate indentation).
    """

    def walk(self):
        """
        Walk the tree, printing each node.
        """
        self.__print_nodes(self.tree.root, 0)

    def __print_nodes(self, node, level):
        """
        Print this specific node, then descend into it's children nodes.
        """
        spacing = ''
        for _ in range(level):
            spacing = '  {}'.format(spacing)

        association = self._node_associations.get_association(node)
        if association:
            platform = ', '.join(association.platforms)
        else:
            platform = ''

        print('{}{} -- Platforms: {}'.format(spacing, node, platform))

        for child in node.children:
            self.__print_nodes(child, level + 1)
