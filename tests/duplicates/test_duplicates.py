# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExampleFile(unittest.TestCase):
    """
    Test ability to detect and report identical files in a codebase.
    Such duplicates may appear in out-of-tree builds and can skew results.
    """

    def setUp(self):
        self.rootdir = "./tests/duplicates/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU']): 11,
                                frozenset(['GPU']): 12,
                                frozenset(['CPU', 'GPU']): 16}


    def test_names(self):
        """duplicates/names.yaml"""
        codebase, configuration = config.load("./tests/duplicates/names.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.expected_setmap = {frozenset(['P0']): 6,
                                frozenset(['P1']): 6}
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


    def test_sizes(self):
        """duplicates/sizes.yaml"""
        codebase, configuration = config.load("./tests/duplicates/sizes.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.expected_setmap = {frozenset(['P0']): 6,
                                frozenset(['P1']): 6}
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


    def test_duplicates(self):
        """duplicates/duplicates.yaml"""
        codebase, configuration = config.load("./tests/duplicates/duplicates.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.expected_setmap = {frozenset(['P0', 'P1']): 6}
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
