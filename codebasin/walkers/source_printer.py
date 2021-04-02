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

class PreprocessedSourcePrinter(TreeWalker):
    """
    TreeWalker that prints preprocessed source code.
    """

    def walk(self):
        """
        Walk the tree, printing the result of each node after preprocessing.
        """
        self.__print_nodes(self.tree.root, self._node_associations)

    def __print_nodes(self, _node, _map):
        """
        Print this specific node, then descend into its children nodes.
        """
        # This is equivalent to isinstance(CodeNode), without needing to
        # import lexer.
        if 'num_lines' in dir(_node) and type(_node).__name__ != 'FileNode':
            association = _map.get_association(_node)
            if association and not isinstance(_node, DirectiveNode):
                print(_node.spelling())
            else:
                # Replace unused code with whitespace
                print()

        for child in _node.children:
            self.__print_nodes(child, _map)
