# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers


class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to recognize different operators when used
    within directives
    """

    def setUp(self):
        self.rootdir = "./tests/operators/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU', 'GPU']): 32}

    def test_yaml(self):
        """operators/operators.yaml"""
        codebase, configuration = config.load("./tests/operators/operators.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = walkers.PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
