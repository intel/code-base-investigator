# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestDisjointCodebase(unittest.TestCase):
    """
    Test of handling for disjoint code bases:
    - Separate file lists for each platform
    - Separate include paths for each platform
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU"]): 6, frozenset(["GPU"]): 6}

    def test_yaml(self):
        """disjoint/disjoint.yaml"""
        codebase = CodeBase(self.rootdir)
        configuration = {
            "CPU": [
                {
                    "file": str(self.rootdir / "cpu.cpp"),
                    "defines": ["CPU"],
                    "include_paths": [str(self.rootdir / "cpu_headers")],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": str(self.rootdir / "gpu.cpp"),
                    "defines": ["GPU"],
                    "include_paths": [str(self.rootdir / "gpu_headers")],
                    "include_files": [],
                },
            ],
        }
        state = finder.find(str(self.rootdir), codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )


if __name__ == "__main__":
    unittest.main()
