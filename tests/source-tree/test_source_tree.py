# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause

import logging
import tempfile
import unittest

from codebasin.file_parser import FileParser
from codebasin.preprocessor import CodeNode, DirectiveNode, FileNode, Visit


class TestSourceTree(unittest.TestCase):
    """
    Test SourceTree class.
    """

    def setUp(self):
        logging.getLogger("codebasin").disabled = False

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
            self.tree = FileParser(f.name).parse_file(summarize_only=False)
            self.filename = f.name

    def test_walk(self):
        """Check that walk() visits nodes in the expected order"""
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
            self.filename,
            "FOO",
            "foo",
            "BAR",
            "bar",
            "else",
            "baz",
            "endif",
            "qux",
        ]
        for i, node in enumerate(self.tree.walk()):
            self.assertTrue(isinstance(node, expected_types[i]))
            if isinstance(node, CodeNode):
                contents = node.spelling()[0]
            else:
                contents = str(node)
            self.assertTrue(expected_contents[i] in contents)

    def test_visit_types(self):
        """Check that visit() validates inputs"""

        class valid_visitor:
            def __call__(self, node):
                return True

        self.tree.visit(valid_visitor())

        def visitor_function(node):
            return True

        self.tree.visit(visitor_function)

        with self.assertRaises(TypeError):
            self.tree.visit(1)

        class invalid_visitor:
            pass

        with self.assertRaises(TypeError):
            self.tree.visit(invalid_visitor())

    def test_visit(self):
        """Check that visit() visits nodes as expected"""

        # Check that a trivial visitor visits all nodes.
        class NodeCounter:
            def __init__(self):
                self.count = 0

            def __call__(self, node):
                self.count += 1

        node_counter = NodeCounter()
        self.tree.visit(node_counter)
        self.assertEqual(node_counter.count, 9)

        # Check that returning NEXT_SIBLING prevents descent.
        class TopLevelCounter:
            def __init__(self):
                self.count = 0

            def __call__(self, node):
                if not isinstance(node, FileNode):
                    self.count += 1
                if isinstance(node, DirectiveNode):
                    return Visit.NEXT_SIBLING
                return Visit.NEXT

        top_level_counter = TopLevelCounter()
        self.tree.visit(top_level_counter)
        self.assertEqual(top_level_counter.count, 5)


if __name__ == "__main__":
    unittest.main()
