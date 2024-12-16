# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import unittest

from codebasin.util import ensure_ext


class TestUtil(unittest.TestCase):
    """
    Test utility functions.
    """

    def setUp(self):
        logging.disable()

    def test_ensure_ext_validation(self):
        """Check ensure_ext raises expected errors"""
        with self.assertRaises(TypeError):
            ensure_ext("path.png", 1)

        with self.assertRaises(TypeError):
            ensure_ext("path.png", [1])

        with self.assertRaises(TypeError):
            ensure_ext("path.png", [".png", 1])

        with self.assertRaises(TypeError):
            not_a_path = 1
            ensure_ext(not_a_path, [".png"])

    def test_ensure_ext(self):
        """Check ensure_ext correctness"""
        with self.assertRaises(ValueError):
            ensure_ext("path.jpg", [".png"])

        ensure_ext("path.png", ".png")
        ensure_ext("path.png", [".png"])
        ensure_ext("path.png", [".jpg", ".png"])
        ensure_ext("path.tar.gz", [".tar.gz"])


if __name__ == "__main__":
    unittest.main()
