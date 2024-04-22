# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestDisjointCodebase(unittest.TestCase):
    """
    Test of handling for disjoint code bases:
    - Separate file lists for each platform
    - Separate include paths for each platform
    """

    def setUp(self):
        self.rootdir = "./tests/disjoint/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU"]): 6, frozenset(["GPU"]): 6}

    def test_yaml(self):
        """disjoint/disjoint.yaml"""
        files = [
            "cpu.cpp",
            "gpu.cpp",
            "cpu_headers/header.h",
            "gpu_headers/header.h",
        ]
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, f)) for f in files
            ],
            "platforms": ["CPU", "GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        configuration = {
            "CPU": [
                {
                    "file": os.path.realpath(
                        os.path.join(self.rootdir, "cpu.cpp"),
                    ),
                    "defines": ["CPU"],
                    "include_paths": [
                        os.path.realpath(
                            os.path.join(self.rootdir, "cpu_headers"),
                        ),
                    ],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": os.path.realpath(
                        os.path.join(self.rootdir, "gpu.cpp"),
                    ),
                    "defines": ["GPU"],
                    "include_paths": [
                        os.path.realpath(
                            os.path.join(self.rootdir, "gpu_headers"),
                        ),
                    ],
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
