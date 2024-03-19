# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestDuplicates(unittest.TestCase):
    """
    Test ability to detect and report identical files in a codebase.
    """

    def setUp(self):
        self.rootdir = str(Path(__file__).parent)
        logging.getLogger("codebasin").disabled = True

    def test_duplicates(self):
        """Check that duplicate files count towards divergence."""

        cpufile = str(Path(__file__).parent.joinpath("cpu/foo.cpp"))
        gpufile = str(Path(__file__).parent.joinpath("gpu/foo.cpp"))

        codebase = {
            "files": [cpufile, gpufile],
            "platforms": ["cpu", "gpu"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }

        configuration = {
            "cpu": [
                {
                    "file": cpufile,
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "gpu": [
                {
                    "file": gpufile,
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }

        expected_setmap = {frozenset(["cpu"]): 1, frozenset(["gpu"]): 1}

        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")


if __name__ == "__main__":
    unittest.main()
