# Copyright (C) 2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
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

    def test_symlink_directories(self):
        """Check that symlink directories do not count towards divergence."""

        cpufile = str(self.rootdir / "cpu/foo.cpp")
        cpu2file = str(self.rootdir / "cpu2/foo.cpp")

        codebase = CodeBase(self.rootdir, exclude_patterns=["gpu/"])

        configuration = {
            "cpu": [
                {
                    "file": cpufile,
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "cpu2": [
                {
                    "file": cpu2file,
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }

        expected_setmap = {frozenset(["cpu", "cpu2"]): 1}

        state = finder.find(self.rootdir, codebase, configuration)
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

    def test_symlink_files(self):
        """Check that symlink files do not count towards divergence."""
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        with open(p / "base.cpp", mode="w") as f:
            f.write("void foo();")
        os.symlink(p / "base.cpp", p / "symlink.cpp")

        codebase = CodeBase(p)
        configuration = {
            "test": [
                {
                    "file": str(p / "base.cpp"),
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
                {
                    "file": str(p / "symlink.cpp"),
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }

        expected_setmap = {frozenset(["test"]): 1}

        state = finder.find(self.rootdir, codebase, configuration)
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(setmap, expected_setmap, "Mismatch in setmap")

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
