# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, config, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestInclude(unittest.TestCase):
    """
    Simple test of ability to follow #include directives to additional
    files.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {
            frozenset(["CPU"]): 11,
            frozenset(["GPU"]): 12,
            frozenset(["CPU", "GPU"]): 16,
        }

    def test_include(self):
        """include/include.yaml"""
        codebase = CodeBase(self.rootdir)

        cpu_path = self.rootdir / "cpu_commands.json"
        gpu_path = self.rootdir / "gpu_commands.json"
        configuration = {
            "CPU": config.load_database(str(cpu_path), str(self.rootdir)),
            "GPU": config.load_database(str(gpu_path), str(self.rootdir)),
        }

        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )


if __name__ == "__main__":
    unittest.main()
