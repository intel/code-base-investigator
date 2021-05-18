# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to follow #include directives to additional
    files.
    """

    def setUp(self):
        self.rootdir = "./tests/include/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU']): 11,
                                frozenset(['GPU']): 12,
                                frozenset(['CPU', 'GPU']): 16}

    def test_yaml(self):
        """include/include.yaml"""
        codebase, configuration = config.load("./tests/include/include.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")

    def test_db(self):
        """include/include-db.yaml"""
        codebase, configuration = config.load("./tests/include/include-db.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
