# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes and functions related to parsing a file,
and building a tree of nodes from it.
"""

from os.path import splitext

from . import preprocessor  # pylint : disable=no-name-in-module


class LineGroup:
    """
    Represents a grouping of lines. It contains the extent, and the
    number of countable lines for the group.
    """

    def __init__(self):
        self.line_count = 0
        self.start_line = -1
        self.end_line = -1

    def empty(self):
        """
        Return a boolean that tells if this group contains any line
        information or not.
        """
        if (self.line_count != 0) or (self.start_line != -1) or (self.end_line != -1):
            return False
        return True

    def add_line(self, line_num, is_countable=False):
        """
        Add a line to this line group. Update the extent appropriately,
        and if it's a countable line, add it to the line count.
        """

        if self.start_line == -1:
            self.start_line = line_num

        self.end_line = line_num

        if self.start_line == -1 or line_num < self.start_line:
            self.start_line = line_num

        if line_num > self.end_line:
            self.end_line = line_num

        if is_countable:
            self.line_count += 1

    def reset(self):
        """
        Reset the countable group
        """
        self.line_count = 0
        self.start_line = -1
        self.end_line = -1

    def merge(self, line_group, count=False):
        """
        Merge another line group into this line group, and reset the
        other group.
        """
        if count:
            self.line_count += line_group.line_count

        if self.start_line == -1:
            self.start_line = line_group.start_line
        elif line_group.start_line == -1:
            line_group.start_line = self.start_line
        self.start_line = min(self.start_line, line_group.start_line)

        self.end_line = max(self.end_line, line_group.end_line)
        line_group.reset()


class FileParser:
    """
    Contains methods for parsing an entire source file and returning a
    source tree object, along with utility methods for determining
    information about source lines and helping to build the source tree.
    """

    def __init__(self, _filename):
        self._filename = _filename
        self.full_line = ''

        split = splitext(_filename)
        if len(split) == 2:
            self._file_extension = split[1].lower()
        else:
            self._file_extension = None

    @staticmethod
    def line_info(line):
        """
        Determine if the input line is a directive by checking if the
        first by looking for a '#' as the first non-whitespace
        character. Also determine if the last character before a new
        line is a line continuation character '\'.

        Return a (directive, line_continue) tuple.
        """

        directive = False
        line_continue = False

        for c in line:
            if c == '#':
                directive = True
                break
            elif c not in [' ', '\t']:
                break

        if line.rstrip("\n\r")[-1:] == '\\':
            line_continue = True

        return (directive, line_continue)

    def handle_directive(self, out_tree, line_num, comment_cleaner, groups):
        """
        Handle inserting code and directive nodes, where appropriate.
        Update the file group, and reset the code and directive groups.
        """
        # We will actually use this directive, if it is not empty
        self.full_line = comment_cleaner.strip_comments(self.full_line)
        if self.full_line.strip():
            # We need to finalize the previously started
            # CodeNode (if there was one) before processing
            # this DirectiveNode
            if not groups['code'].empty():
                groups['code'].add_line(line_num - 1)
                self.insert_code_node(out_tree, groups['code'])

                groups['file'].merge(groups['code'])

            self.insert_directive_node(out_tree, groups['directive'])

            groups['file'].merge(groups['directive'])
        else:
            groups['code'].merge(groups['directive'])

    @staticmethod
    def insert_code_node(tree, line_group):
        """
        Build a code node, and insert it into the source tree
        """
        new_node = preprocessor.CodeNode(
            line_group.start_line, line_group.end_line, line_group.line_count)
        tree.insert(new_node)

    def insert_directive_node(self, tree, line_group):
        """
        Build a directive node by parsing a directive line, and insert a
        new directive node into the tree.
        """
        new_node = preprocessor.DirectiveParser(preprocessor.Lexer(
            self.full_line, line_group.start_line).tokenize()).parse()
        new_node.start_line = line_group.start_line
        new_node.end_line = line_group.end_line
        new_node.num_lines = line_group.line_count
        tree.insert(new_node)

    def parse_file(self):
        """
        Parse the file that this parser points at, build a SourceTree
        representing this file, and return it.
        """

        file_comment_cleaner = preprocessor.CommentCleaner(self._file_extension)
        if file_comment_cleaner.filetype == 'c':
            cpp_comment_cleaner = file_comment_cleaner
        else:
            cpp_comment_cleaner = preprocessor.CommentCleaner('.c')

        out_tree = preprocessor.SourceTree(self._filename)
        with open(self._filename, mode='r', errors='replace') as source_file:
            previous_continue = False

            groups = {'code': LineGroup(),
                      'directive': LineGroup(),
                      'file': LineGroup()
                      }

            groups['file'].start_line = 1

            lines = source_file.readlines()
            for (line_num, line) in enumerate(lines, 1):
                # Determine if this line starts with a # (directive)
                # and/or ends with a \ (line continuation)
                (in_directive, continue_line) = self.line_info(line)

                # Only follow continuation for directives
                if previous_continue or in_directive:

                    # Add this into the directive lines, even if it
                    # might not be a directive we count
                    groups['directive'].add_line(line_num, True)

                    # If this line starts a new directive, flush the
                    # line buffer
                    if in_directive and not previous_continue:
                        self.full_line = ''

                    previous_continue = continue_line

                    # If this line also contains a continuation
                    # character
                    if continue_line:
                        self.full_line += line.rstrip("\\\n\r")
                    # If this line ends a previously continued line
                    else:
                        self.full_line += line.rstrip("\n\r")

                        self.handle_directive(out_tree, line_num, cpp_comment_cleaner,
                                              groups)

                # FallBack is that this line is a simple code line.
                else:
                    previous_continue = False

                    # If the line isn't empty after stripping comments,
                    # count it as code
                    if file_comment_cleaner.strip_comments(line[0:-1]).strip():
                        groups['code'].add_line(line_num, True)
                    else:
                        groups['code'].add_line(line_num)

            # Insert any code lines left at the end of the file
            if not groups['code'].empty():
                groups['code'].add_line(len(lines))
                self.insert_code_node(out_tree, groups['code'])

                groups['file'].merge(groups['code'])

            groups['file'].add_line(len(lines))
            out_tree.root.num_lines = groups['file'].end_line
            out_tree.root.total_sloc = groups['file'].line_count
            return out_tree
