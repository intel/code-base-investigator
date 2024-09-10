# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import os
import shutil
import tempfile
import unittest

from codebasin import util


class TestSafeWrite(unittest.TestCase):
    """
    Test that safe_open_write_binary properly opens non-symlinks and
    bails on symlinks.
    """

    def setUp(self):
        self.testdir = tempfile.mkdtemp()
        self.path_linkfail = os.path.join(self.testdir, "nowrite.bin")
        self.path_link = os.path.join(self.testdir, "link.bin")
        self.path_write = os.path.join(self.testdir, "write.bin")
        self.path_create = os.path.join(self.testdir, "create.bin")

        self.initial = bytes("MAGIC", "utf-8")
        self.updated = bytes("GOOD", "utf-8")

        with open(self.path_linkfail, "wb") as fp:
            fp.write(self.initial)

        shutil.copyfile(self.path_linkfail, self.path_write)

        os.symlink(self.path_linkfail, self.path_link)

    def tearDown(self):
        shutil.rmtree(self.testdir)

    def test_linkfail(self):
        """Check that we fail to open a symlink for writing"""
        with self.assertRaises(os.error):
            with util.safe_open_write_binary(self.path_link) as fp:
                fp.write(bytes("BAD", "utf-8"))

        with open(self.path_linkfail, "rb") as fp:
            got = fp.read(5)
            self.assertEqual(got, self.initial)
            st = os.fstat(fp.fileno())
            self.assertEqual(st.st_mode & 0o111, 0)

        with open(self.path_link, "rb") as fp:
            got = fp.read(5)
            self.assertEqual(got, self.initial)
            st = os.fstat(fp.fileno())
            self.assertEqual(st.st_mode & 0o111, 0)

    def test_write(self):
        """Check that we can write to existing non-symlink files"""
        with util.safe_open_write_binary(self.path_write) as fp:
            fp.write(self.updated)

        with open(self.path_write, "rb") as fp:
            got = fp.read(5)
            self.assertEqual(got, self.updated)
            st = os.fstat(fp.fileno())
            self.assertEqual(st.st_mode & 0o111, 0)

    def test_create(self):
        """Check that we can write to non-existing files"""
        with util.safe_open_write_binary(self.path_create) as fp:
            fp.write(self.updated)

        with open(self.path_create, "rb") as fp:
            got = fp.read(5)
            self.assertEqual(got, self.updated)
            st = os.fstat(fp.fileno())
            self.assertEqual(st.st_mode & 0o111, 0)


if __name__ == "__main__":
    unittest.main()
