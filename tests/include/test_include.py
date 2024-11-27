# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
import unittest
from pathlib import Path

from codebasin import CodeBase, config, finder


class TestInclude(unittest.TestCase):
    """
    Simple test of ability to follow #include directives to additional
    files.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

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
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )

    def test_include_from_symlink(self):
        """Check included file correctly identifies its parent"""
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name)
        with open(p / "test.cpp", mode="w") as f:
            f.write('#include "test.h"')
        open(p / "test.h", mode="w").close()
        os.symlink(p / "test.cpp", p / "symlink.cpp")

        codebase = CodeBase(p)
        configuration = {
            "test": [
                {
                    "file": str(p / "symlink.cpp"),
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
        }
        _ = finder.find(self.rootdir, codebase, configuration)

        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
