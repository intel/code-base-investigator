# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
import unittest
from pathlib import Path

from codebasin import file_parser


class TestPreprocessorWarnings(unittest.TestCase):
    """
    Test that preprocessor generates warnings for weird corner cases.
    """

    def setUp(self):
        self.cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self.cwd)

    def test_backslash_eof(self):
        """Check backslash-newline at EOF is only a warning"""
        tmp = tempfile.TemporaryDirectory()
        path = Path(tmp.name)
        os.chdir(tmp.name)

        with open(path / "test.hpp", mode="w") as f:
            f.write("#define BAD_MACRO \\\n")

        parser = file_parser.FileParser(path / "test.hpp")

        logging.disable(logging.NOTSET)
        logger = logging.getLogger("codebasin")
        with self.assertLogs(logger, level="WARNING") as cm:
            _ = parser.parse_file()
        logging.disable()
        self.assertRegex(cm.output[0], "backslash-newline at end of file")

        tmp.cleanup()
