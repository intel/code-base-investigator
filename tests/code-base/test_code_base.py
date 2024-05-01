# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import tempfile
import unittest
import warnings
from pathlib import Path

from codebasin import CodeBase


class TestCodeBase(unittest.TestCase):
    """
    Test CodeBase class.
    """

    def setUp(self):
        logging.getLogger("codebasin").disabled = False
        warnings.simplefilter("ignore", ResourceWarning)

        # Create a temporary codebase spread across two directories
        self.tmp1 = tempfile.TemporaryDirectory()
        self.tmp2 = tempfile.TemporaryDirectory()
        p1 = Path(self.tmp1.name)
        p2 = Path(self.tmp2.name)
        open(p1 / "foo.cpp", mode="w").close()
        open(p1 / "bar.cpp", mode="w").close()
        open(p1 / "baz.h", mode="w").close()
        open(p1 / "README.md", mode="w").close()
        open(p2 / "qux.cpp", mode="w").close()
        open(p2 / "quux.h", mode="w").close()
        open(p2 / "README.md", mode="w").close()

    def test_constructor(self):
        """Check directories and exclude_patterns are handled correctly"""
        path = Path(self.tmp1.name)
        codebase = CodeBase(path, exclude_patterns=["*.h"])
        self.assertTrue(codebase.directories == [str(path)])
        self.assertTrue(codebase.exclude_patterns == ["*.h"])

    def test_constructor_validation(self):
        """Check directories and exclude_patterns are valid"""

        with self.assertRaises(TypeError):
            CodeBase(exclude_patterns="*")

        with self.assertRaises(TypeError):
            CodeBase(1, "2", 3)

        with self.assertRaises(TypeError):
            CodeBase(exclude_patterns=[1, "2", 3])

    def test_repr(self):
        """Check implementation of __repr__"""
        path = Path(self.tmp1.name)
        codebase = CodeBase(path, exclude_patterns=["*.h"])
        self.assertTrue(
            codebase.__repr__(),
            f'CodeBase(directories=[{path}], exclude_patterns=[".h"])',
        )

    def test_contains(self):
        """Check implementation of __contains__"""
        p1 = Path(self.tmp1.name)
        p2 = Path(self.tmp2.name)
        codebase = CodeBase(p1, p2, exclude_patterns=["*.h"])

        # Files in the temporary directories should be in the code base.
        self.assertTrue(p1 / "foo.cpp" in codebase)
        self.assertTrue(p1 / "bar.cpp" in codebase)
        self.assertTrue(p2 / "qux.cpp" in codebase)

        # Files that match exclude pattern(s) should not be in the code base.
        self.assertFalse(p1 / "baz.h" in codebase)
        self.assertFalse(p2 / "quux.h" in codebase)

        # Files that don't exist should not be in the code base.
        self.assertFalse(p1 / "asdf.cpp" in codebase)
        self.assertFalse(p2 / "asdf.cpp" in codebase)

        # The temporary directories themselves should not be in the code base.
        self.assertFalse(p1 in codebase)
        self.assertFalse(p2 in codebase)

        # Non-source files should not be in the code base.
        self.assertFalse(p1 / "README.md" in codebase)
        self.assertFalse(p2 / "README.md" in codebase)

    def test_iterator(self):
        """Check implementation of __iter__"""
        p1 = Path(self.tmp1.name)
        p2 = Path(self.tmp2.name)
        codebase = CodeBase(p1, p2, exclude_patterns=["*.h"])

        files = [f for f in codebase]
        expected = [
            str(p1 / "bar.cpp"),
            str(p1 / "foo.cpp"),
            str(p2 / "qux.cpp"),
        ]
        self.assertEqual(files, expected)


if __name__ == "__main__":
    unittest.main()
