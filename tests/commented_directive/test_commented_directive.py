# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to recognize #commented_directive directives
    within files.
    """

    def setUp(self):
        self.rootdir = "./tests/commented_directive/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU', 'GPU']): 5}

    def count_children_nodes(self, node):
        my_count = 0
        for child in node.children:
            my_count += 1 + self.count_children_nodes(child)

        return my_count

    def test_yaml(self):
        """commented_directive/commented_directive.yaml"""
        codebase, configuration = config.load(
            "./tests/commented_directive/commented_directive.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)

        node_count = 1
        for fn in state.get_filenames():
            node_count += self.count_children_nodes(state.get_tree(fn).root)

        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")
        self.assertEqual(node_count, 6, "Incorrect number of nodes in tree: {}".format(node_count))


if __name__ == '__main__':
    unittest.main()
