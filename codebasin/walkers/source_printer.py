# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

from .tree_walker import TreeWalker
from codebasin.preprocessor import CodeNode, DirectiveNode, FileNode, Lexer, MacroExpander

class SourcePrinter(TreeWalker):
    """
    TreeWalker that prints preprocessed source.
    """
    def __init__(self, _tree):
        super().__init__(_tree, None)

    def walk(self):
        """
        Walk the tree, printing each node.
        """
        self.__print_nodes(self.tree.root)

    def __print_nodes(self, node):
        """
        Print this specific node, then descend into its children nodes.
        """
        if not isinstance(node, FileNode):
            print("\n".join(node.spelling()))

        for child in node.children:
            self.__print_nodes(child)

class PreprocessedSourcePrinter(TreeWalker):
    """
    TreeWalker that prints preprocessed source code.
    """
    def __init__(self, _tree, _node_associations, _platform, _state, _expand):
        super().__init__(_tree, _node_associations)
        self.platform = _platform
        self.state = _state
        self.expand_macros = _expand

    def walk(self):
        """
        Walk the tree, printing the result of each node after preprocessing.
        """
        self.__print_nodes(self.tree.root, self._node_associations)

    def __print_nodes(self, _node, _map):
        """
        Print this specific node, then descend into its children nodes.
        """
        descend = True
        if isinstance(_node, CodeNode):
            association = _map[_node]

            # Re-evaluating the node during this walk is required to
            # define/undefine macros appropriately
            eval_args = {'platform': self.platform,
                         'filename': self.tree.root.filename,
                         'state': self.state}
            descend = _node.evaluate_for_platform(**eval_args)
            expander = MacroExpander(self.platform)
            if association and not isinstance(_node, DirectiveNode):
                node_lines = _node.spelling()
                output_lines = []
                for line in node_lines:
                    if self.expand_macros:
                        tokens = Lexer(line).tokenize()
                        expansion = expander.expand(tokens)
                        for tok in expansion:
                            if tok.prev_white:
                                output_lines.append(" ")
                            output_lines.append(str(tok))
                    else:
                        output_lines.append(line)
                    output_lines.append("\n")
                print("".join(output_lines))
            else:
                # Replace unused code with whitespace
                print()

        if descend:
            for child in _node.children:
                self.__print_nodes(child, _map)
