# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import logging
import unittest

from codebasin.config import _ExtendMatchAction, _StoreSplitAction


class TestActions(unittest.TestCase):
    """
    Test that custom argparse.Action classes work as expected.
    These classes enable handling of complex user-defined compiler options.
    """

    def setUp(self):
        logging.disable()

    def test_store_split_init(self):
        """Check that store_split recognizes custom arguments"""
        action = _StoreSplitAction(["--foo"], "foo", sep=",", format="$value")
        self.assertEqual(action.sep, ",")
        self.assertEqual(action.format, "$value")

        action = _StoreSplitAction(["--foo"], "foo")
        self.assertEqual(action.sep, None)
        self.assertEqual(action.format, None)

    def test_store_split(self):
        """Check that argparse calls store_split correctly"""
        namespace = argparse.Namespace()
        namespace.passes = {}

        parser = argparse.ArgumentParser()
        parser.add_argument("--foo", action=_StoreSplitAction, sep=",")
        parser.add_argument(
            "--bar",
            action=_StoreSplitAction,
            sep=",",
            format="prefix-$value-suffix",
        )
        parser.add_argument("--baz", action=_StoreSplitAction, type=int)
        parser.add_argument(
            "--qux",
            action=_StoreSplitAction,
            sep=",",
            dest="passes",
        )

        args, _ = parser.parse_known_args(["--foo=one,two"], namespace)
        self.assertEqual(args.foo, ["one", "two"])

        args, _ = parser.parse_known_args(["--bar=one,two"], namespace)
        self.assertEqual(args.bar, ["prefix-one-suffix", "prefix-two-suffix"])

        with self.assertRaises(TypeError):
            args, _ = parser.parse_known_args(["--baz=1"], namespace)

        args, _ = parser.parse_known_args(["--qux=one,two"], namespace)
        self.assertEqual(args.passes, {"--qux": ["one", "two"]})

    def test_extend_match_init(self):
        """Check that extend_match recognizes custom arguments"""
        action = _ExtendMatchAction(
            ["--foo"],
            "foo",
            pattern="*",
            format="$value",
        )
        self.assertEqual(action.pattern, "*")
        self.assertEqual(action.format, "$value")

        action = _ExtendMatchAction(["--foo"], "foo")
        self.assertEqual(action.pattern, None)
        self.assertEqual(action.format, None)

    def test_extend_match(self):
        """Check that argparse calls store_split correctly"""
        namespace = argparse.Namespace()
        namespace.passes = {}

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--foo",
            action=_ExtendMatchAction,
            pattern=r"option_(\d+)",
            default=[],
        )
        parser.add_argument(
            "--bar",
            action=_ExtendMatchAction,
            pattern=r"option_(\d+)",
            format="prefix-$value-suffix",
            default=[],
        )
        parser.add_argument("--baz", action=_ExtendMatchAction, type=int)
        parser.add_argument(
            "--qux",
            action=_ExtendMatchAction,
            pattern=r"option_(\d+)",
            dest="passes",
        )

        args, _ = parser.parse_known_args(
            ["--foo=option_1,option_2"],
            namespace,
        )
        self.assertEqual(args.foo, ["1", "2"])

        args, _ = parser.parse_known_args(
            ["--bar=option_1,option_2"],
            namespace,
        )
        self.assertEqual(args.bar, ["prefix-1-suffix", "prefix-2-suffix"])

        with self.assertRaises(TypeError):
            args, _ = parser.parse_known_args(["--baz=1"], namespace)

        args, _ = parser.parse_known_args(
            ["--qux=option_1,option_2"],
            namespace,
        )
        self.assertEqual(args.passes, {"--qux": ["1", "2"]})


if __name__ == "__main__":
    unittest.main()
