# Copyright (C) 2021 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
from codebasin import config, finder, walkers
from codebasin.walkers.platform_mapper import PlatformMapper


class TestExampleFile(unittest.TestCase):
    """
    Simple test of ability to handle directives in Fortran code.
    """

    def setUp(self):
        self.rootdir = "./tests/basic_asm/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(['CPU']): 24}

    def test_yaml(self):
        """basic_asm/basic_asm.yaml"""
        codebase, configuration = config.load(
            "./tests/basic_asm/basic_asm.yaml", self.rootdir)
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, self.expected_setmap, "Mismatch in setmap")


if __name__ == '__main__':
    unittest.main()
