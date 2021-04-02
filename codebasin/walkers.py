# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes to help walk a tree of nodes, and create associations
between nodes and platform sets.
"""

import logging
import collections

log = logging.getLogger('codebasin')


class TreeWalker():
    """
    Generic tree walker class.
    """

    def __init__(self, _tree, _node_associations):
        self.tree = _tree
        self._node_associations = _node_associations


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


class TreeAssociator(TreeWalker):
    """
    Specific TreeWalker that build associations with platforms.
    """

    def walk(self, platform, state):
        """
        Walk the tree, associating nodes with platforms
        """
        _ = self._associate_nodes(self.tree.root, platform, state, True)

    def _associate_nodes(self, node, platform, state, process_children):
        """
        Associate this node with the platform. Evaluate the node,
        and (if the evaluation say to) descend into the children nodes.
        """
        self._node_associations[node].add(platform.name)

        node_processed = False
        eval_args = {'platform': platform,
                     'filename': self.tree.root.filename,
                     'state': state}

        if process_children and node.evaluate_for_platform(**eval_args):
            # node_processed tells us if a child node was processed.
            # This is useful for tracking which branch was taken in a
            # multi-branch directive.
            node_processed = True

            # process_child is used to ignore children of branch nodes
            # that shouldn't be evaluated because a previous branch was
            # taken
            process_child = True
            for child in node.children:
                child_processed = self._associate_nodes(child, platform, state, process_child)

                if child_processed and (child.is_start_node() or child.is_cont_node()):
                    process_child = False
                elif not process_child and child.is_end_node():
                    process_child = True

        return node_processed


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
        if type(_node).__name__ == 'FileNode' and _node.filename not in self.codebase["files"]:
            return

        # This is equivalent to isinstance(CodeNode), without needing to
        # import lexer.
        if 'num_lines' in dir(_node) and type(_node).__name__ != 'FileNode':
            association = _map[_node]
            platform = frozenset(association)
            self.line_map[platform] += _node.num_lines

        for child in _node.children:
            self._map_node(child, _map)
