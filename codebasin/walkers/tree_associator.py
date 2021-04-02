# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import collections

from .tree_walker import TreeWalker

log = logging.getLogger('codebasin')


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
