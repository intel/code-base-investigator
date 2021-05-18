# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExampleFile(unittest.TestCase):
    """
    Test of handling for disjoint code bases:
    - Separate file lists for each platform
    - Separate include paths for each platform
    """

    def setUp(self):
        self.rootdir = "./tests/disjoint/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU']): 6,
                                frozenset(['GPU']): 6}

    def test_yaml(self):
        """disjoint/disjoint.yaml"""
        codebase, configuration = config.load("./tests/disjoint/disjoint.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
