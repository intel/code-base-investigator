# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestOnce(unittest.TestCase):
    """
    Simple test of ability to obey #pragma once directives.
    """

    def setUp(self):
        self.rootdir = "./tests/once/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {
            frozenset([]): 4,
            frozenset(["CPU", "GPU"]): 10,
        }

    def test_yaml(self):
        """once/once.yaml"""
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, "main.cpp")),
                os.path.realpath(os.path.join(self.rootdir, "once.h")),
            ],
            "platforms": ["CPU", "GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        configuration = {
            "CPU": [
                {
                    "file": codebase["files"][0],
                    "defines": ["CPU"],
                    "include_paths": [],
                    "include_files": [],
                },
            ],
            "GPU": [
                {
                    "file": codebase["files"][0],
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
