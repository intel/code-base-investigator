# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper

class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to handle nested definition scopes
    """

    def setUp(self):
        self.rootdir = "./tests/nesting/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU']): 6,
                                frozenset(['GPU']): 6,
                                frozenset(['CPU', 'GPU']): 5}

    def test_yaml(self):
        """nesting/nesting.yaml"""
        codebase, configuration = config.load("./tests/nesting/nesting.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
