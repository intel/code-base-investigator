# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestBasicFortran(unittest.TestCase):
    """
    Simple test of ability to handle directives in Fortran code.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

        self.expected_setmap = {
            frozenset(["CPU"]): 2,
            frozenset(["GPU"]): 3,
            frozenset(["CPU", "GPU"]): 8,
        }

    def test_yaml(self):
        """basic_fortran/basic_fortran.yaml"""
        codebase = CodeBase(self.rootdir)
        configuration = {
            "CPU": [
                {
                    "file": str(self.rootdir / "test.f90"),
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": str(self.rootdir / "test.f90"),
                    "defines": ["GPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
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
