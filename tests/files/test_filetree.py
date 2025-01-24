# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os
import tempfile
import unittest
from pathlib import Path

from codebasin.report import FileTree


class TestFileTree(unittest.TestCase):
    """
    Test FileTree functionality.
    """

    @classmethod
    def setUpClass(self):
        logging.disable()

        self.setmap = {
            frozenset(["X"]): 1,
            frozenset(["Y"]): 2,
            frozenset(["X", "Y"]): 3,
            frozenset([]): 6,
        }

        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        open(self.path / "file.cpp", mode="w").close()
        open(self.path / "other.cpp", mode="w").close()
        os.symlink(self.path / "file.cpp", self.path / "symlink.cpp")

    @classmethod
    def tearDownClass(self):
        self.tmp.cleanup()

    def test_constructor(self):
        """Check FileTree constructor."""
        tree = FileTree(self.path)
        self.assertEqual(tree.root.path, self.path)
        self.assertTrue(tree.root.is_root)

    def test_insert(self):
        """Check insertion into FileTree."""
        tree = FileTree(self.path)

        tree.insert(self.path / "file.cpp", setmap={"X": 1})
        self.assertEqual(len(tree.root.children), 1)
        self.assertCountEqual(tree.root.platforms, ["X"])
        self.assertEqual(tree.root.setmap, {"X": 1})
        self.assertEqual(tree.root.sloc, 1)

        # NB: information from symlinks doesn't propagate upwards!
        tree.insert(self.path / "symlink.cpp", setmap={"Y": 2})
        self.assertEqual(len(tree.root.children), 2)
        self.assertCountEqual(tree.root.platforms, ["X"])
        self.assertEqual(tree.root.setmap, {"X": 1})
        self.assertEqual(tree.root.sloc, 1)

        tree.insert(self.path / "other.cpp", setmap={"Y": 2})
        self.assertEqual(len(tree.root.children), 3)
        self.assertCountEqual(tree.root.platforms, ["X", "Y"])
        self.assertEqual(tree.root.setmap, {"X": 1, "Y": 2})
        self.assertEqual(tree.root.sloc, 3)

        children_names = [node for node in tree.root.children]
        expected_names = ["file.cpp", "symlink.cpp", "other.cpp"]
        self.assertCountEqual(children_names, expected_names)
        self.assertFalse(tree.root.children["file.cpp"].is_symlink())
        self.assertFalse(tree.root.children["other.cpp"].is_symlink())
        self.assertTrue(tree.root.children["symlink.cpp"].is_symlink())

    def test_print(self):
        """Check print for specific cases."""
        tree = FileTree(self.path)
        meta = tree.root._meta_str(tree.root)
        lines = tree._print(tree.root)
        self.assertEqual(lines, [f"{meta} o \033[94m{self.path}/\033[0m"])

        tree.insert(self.path / "file.cpp", setmap={"X": 1})
        node = tree.root.children["file.cpp"]
        meta = node._meta_str(tree.root)
        lines = tree._print(node)
        self.assertEqual(lines, [f"{meta} \u2500\u2500 file.cpp\033[0m"])

        tree.insert(self.path / "symlink.cpp", setmap={"Y": 2})
        node = tree.root.children["symlink.cpp"]
        self.assertTrue(node.is_symlink())
        meta = node._meta_str(tree.root)
        lines = tree._print(node)
        expected_name = "\033[96msymlink.cpp\033[0m"
        expected_link = f"{str(self.path / 'file.cpp')}\033[0m"
        self.assertEqual(
            lines,
            [f"{meta} \u2500\u2500 {expected_name} -> {expected_link}"],
        )


if __name__ == "__main__":
    unittest.main()
