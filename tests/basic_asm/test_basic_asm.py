# Copyright (C) 2021-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest
from pathlib import Path

from codebasin import CodeBase, finder


class TestBasicAsm(unittest.TestCase):
    """
    Simple test of ability to handle assembly files.
    """

    def setUp(self):
        self.rootdir = Path(__file__).parent.resolve()
        logging.disable()

        self.expected_setmap = {frozenset(["CPU"]): 24}

    def test_yaml(self):
        """basic_asm/basic_asm.yaml"""
        codebase = CodeBase(self.rootdir)
        entries = []
        for f in codebase:
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
        setmap = state.get_setmap(codebase)
        self.assertDictEqual(
            setmap,
            self.expected_setmap,
            "Mismatch in setmap",
        )

    def test_ptx(self):
        """basic_asm/basic_asm_ptx.yaml"""
        codebase = CodeBase(self.rootdir)
        entry = {
            "file": str(self.rootdir / "test.ptx"),
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
