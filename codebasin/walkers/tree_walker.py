# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

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
