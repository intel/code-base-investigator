# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import config, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestInclude(unittest.TestCase):
    """
    Simple test of ability to follow #include directives to additional
    files.
    """

    def setUp(self):
        self.rootdir = "./tests/include/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {
            frozenset(["CPU"]): 11,
            frozenset(["GPU"]): 12,
            frozenset(["CPU", "GPU"]): 16,
        }

    def test_include(self):
        """include/include.yaml"""
        codebase = {
            "files": [],
            "platforms": ["CPU", "GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": os.path.realpath(self.rootdir),
        }

        cpu_path = os.path.realpath(
            os.path.join(self.rootdir, "cpu_commands.json"),
        )
        gpu_path = os.path.realpath(
            os.path.join(self.rootdir, "gpu_commands.json"),
        )
        configuration = {
            "CPU": config.load_database(cpu_path, self.rootdir),
            "GPU": config.load_database(gpu_path, self.rootdir),
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
