# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers


class TestExampleFile(unittest.TestCase):
    """
    Simple test of C-style literal handling.
    e.g. 0x0ULL, 0b11
    """

    def setUp(self):
        self.rootdir = "./tests/literals/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU', 'GPU']): 9}

    def test_yaml(self):
        """literals/literals.yaml"""
        codebase, configuration = config.load("./tests/literals/literals.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = walkers.PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
