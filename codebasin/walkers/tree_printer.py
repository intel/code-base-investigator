# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging

from codebasin.walkers.tree_walker import TreeWalker

log = logging.getLogger("codebasin")


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
        association = self._node_associations[node]
        if association:
            platform = ", ".join(association)
        else:
            platform = ""

        spacing = "  " * (level)
        print(f"{spacing}{node} -- Platforms: {platform}")

        for child in node.children:
            self.__print_nodes(child, level + 1)
