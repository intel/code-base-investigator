# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

class SourcePrinter(TreeWalker):
    """
    TreeWalker that prints preprocessed source.
    """

    def walk(self):
        """
        Walk the tree, printing each node.
        """
        self.__print_nodes(self.tree.root)

    def __print_nodes(self, node):
        """
        Print this specific node, then descend into its children nodes.
        """
        if type(node).__name__ != 'FileNode':
            print(node.spelling())

        for child in node.children:
            self.__print_nodes(child)
