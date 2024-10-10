# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder


class TestDuplicates(unittest.TestCase):
    """
    Test ability to detect and report identical files in a codebase.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

    def test_duplicates(self):
        """Check that duplicate files count towards divergence."""

        cpufile = str(self.rootdir / "cpu/foo.cpp")
        gpufile = str(self.rootdir / "gpu/foo.cpp")

        codebase = CodeBase(self.rootdir)

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
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")


if __name__ == "__main__":
    unittest.main()
