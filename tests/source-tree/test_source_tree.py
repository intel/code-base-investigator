# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import tempfile
import unittest
import warnings

from codebasin.file_parser import FileParser
from codebasin.preprocessor import CodeNode, DirectiveNode, FileNode


class TestSourceTree(unittest.TestCase):
    """
    Test SourceTree class.
    """

    def setUp(self):
        logging.getLogger("codebasin").disabled = False
        warnings.simplefilter("ignore", ResourceWarning)

    def test_walk(self):
        """Check that walk() visits nodes in the expected order"""

        # TODO: Revisit this when SourceTree can be built without a file.
        with tempfile.NamedTemporaryFile(
            mode="w",
            delete_on_close=False,
            suffix=".cpp",
        ) as f:
            source = """
                #if defined(FOO)
                void foo();
                #elif defined(BAR)
                void bar();
                #else
                void baz();
                #endif

                void qux();
                """
            f.write(source)
            f.close()

            # TODO: Revisit this when __str__() is more reliable.
            tree = FileParser(f.name).parse_file(summarize_only=False)
            expected_types = [
                FileNode,
                DirectiveNode,
                CodeNode,
                DirectiveNode,
                CodeNode,
                DirectiveNode,
                CodeNode,
                DirectiveNode,
                CodeNode,
            ]
            expected_contents = [
                f.name,
                "FOO",
                "foo",
                "BAR",
                "bar",
                "else",
                "baz",
                "endif",
                "qux",
            ]
            for i, node in enumerate(tree.walk()):
                self.assertTrue(isinstance(node, expected_types[i]))
                if isinstance(node, CodeNode):
                    contents = node.spelling()[0]
                else:
                    contents = str(node)
                self.assertTrue(expected_contents[i] in contents)


if __name__ == "__main__":
    unittest.main()
