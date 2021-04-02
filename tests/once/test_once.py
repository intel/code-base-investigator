# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper

class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to obey #pragma once directives.
    """

    def setUp(self):
        self.rootdir = "./tests/once/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset([]): 4,
                                frozenset(['CPU', 'GPU']): 10}

    def test_yaml(self):
        """once/once.yaml"""
        codebase, configuration = config.load("./tests/once/once.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
