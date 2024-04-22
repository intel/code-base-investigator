# Copyright (C) 2021-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import unittest

from codebasin import finder
from codebasin.walkers.platform_mapper import PlatformMapper


class TestBasicAsm(unittest.TestCase):
    """
    Simple test of ability to handle assembly files.
    """

    def setUp(self):
        self.rootdir = "./tests/basic_asm/"
        logging.getLogger("codebasin").disabled = True

        self.expected_setmap = {frozenset(["CPU"]): 24}

    def test_yaml(self):
        """basic_asm/basic_asm.yaml"""
        files = ["test.s", "test.S", "test.asm"]
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, f)) for f in files
            ],
            "platforms": ["CPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        entries = []
        for f in codebase["files"]:
            entries.append(
                {
                    "file": f,
                    "defines": [],
                    "include_paths": [],
                    "include_files": [],
                },
            )
        configuration = {"CPU": entries}
        state = finder.find(self.rootdir, codebase, configuration)
        mapper = PlatformMapper(codebase)
        setmap = mapper.walk(state)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )

    def test_ptx(self):
        """basic_asm/basic_asm_ptx.yaml"""
        codebase = {
            "files": [
                os.path.realpath(os.path.join(self.rootdir, "test.ptx")),
            ],
            "platforms": ["GPU"],
            "exclude_files": set(),
            "exclude_patterns": [],
            "rootdir": self.rootdir,
        }
        entry = {
            "file": codebase["files"][0],
            "defines": [],
            "include_paths": [],
            "include_files": [],
        }
        configuration = {"GPU": [entry]}
        self.assertRaises(
            RuntimeError,
            finder.find,
            self.rootdir,
            codebase,
            configuration,
        )


if __name__ == "__main__":
    unittest.main()
