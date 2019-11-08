# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import unittest
import logging
import os
from codebasin import preprocessor, file_parser

class TestExampleFile(unittest.TestCase):
    """
    Test handling of comments
    """

    def test_c_comments(self):
        rootdir = "./tests/comments/"
        parser = file_parser.FileParser(os.path.join(rootdir, "continuation.cpp"))

        tree = parser.parse_file()
        self.assertEqual(tree.root.total_sloc, 25)

if __name__ == '__main__':
    unittest.main()
