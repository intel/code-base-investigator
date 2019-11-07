# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes and functions for stripping comments and whitespace from C/C++ files
"""

global whitespace_dict
whitespace_dict = dict.fromkeys(' \t\n\r\x0b\x0c\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000')

def is_whitespace(c):
    return c in whitespace_dict

class one_space_line(object):
    def __init__(self):
        self.parts = []
        self.trailing_space = False
    def append_char(self, c):
        if not is_whitespace(c):
            self.parts.append(c)
            self.trailing_space = False
        else:
            if not self.trailing_space:
                self.parts.append(' ')
                self.trailing_space = True
    def append_space(self):
        if not self.trailing_space:
            self.parts.append(' ')
            self.trailing_space = True
    def append_nonspace(self, c):
        self.parts.append(c)
        self.trailing_space = False
    def join(self, other):
        if len(other.parts) > 0:
            if other.parts[0] == ' ' and self.trailing_space:
                self.parts += other.parts[1:]
            else:
                self.parts += other.parts[:]
            self.trailing_space = other.trailing_space
    def is_blank(self):
        return len(self.parts) == 0 or ( len(self.parts) == 1 and self.parts[0] == ' ' )
    def flush(self):
        res= ''.join(self.parts)
        self.__init__()
        return res

class c_cleaner(object):
    def __init__(self, outbuf):
        self.state = ["NO_COMMENT"]
        self.outbuf = outbuf
    def logical_newline(self):
        if self.state[-1] == "IN_INLINE_COMMENT":
            self.state.pop()
            assert self.state == ["NO_COMMENT"]
            self.outbuf.append_space()
        elif self.state[-1] == "FOUND_SLASH":
            self.state.pop()
            assert self.state == ["NO_COMMENT"]
            self.outbuf.append_nonspace('/')
        elif self.state[-1] == "SINGLE_QUOTATION":
            # This probably should give a warning
            self.state.pop()
            assert self.state == ["NO_COMMENT"]
        elif self.state[-1] == "DOUBLE_QUOTATION":
            # This probably should give a warning
            self.state.pop()
            assert self.state == ["NO_COMMENT"]
        elif self.state[-1] == "IN_BLOCK_COMMENT_FOUND_STAR":
            self.state.pop()
            assert self.state[-1] == "IN_BLOCK_COMMENT"
    def process(self, line, start, end):
        pos = start
        while pos < end:
            if self.state[-1] == "NO_COMMENT":
                if line[pos] == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(line[pos])
                elif line[pos] == '/':
                    self.state.append("FOUND_SLASH")
                elif line[pos] == '"':
                    self.state.append("DOUBLE_QUOTATION")
                    self.outbuf.append_nonspace(line[pos])
                elif line[pos] == '\'':
                    self.state.append("SINGLE_QUOTATION")
                    self.outbuf.append_nonspace(line[pos])
                else:
                    self.outbuf.append_char(line[pos])
            elif self.state[-1] == "DOUBLE_QUOTATION":
                if line[pos] == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(line[pos])
                elif line[pos] == '"':
                    self.state.pop()
                    assert self.state == ["NO_COMMENT"]
                    self.outbuf.append_nonspace(line[pos])
                else:
                    self.outbuf.append_nonspace(line[pos])
            elif self.state[-1] == "SINGLE_QUOTATION":
                if line[pos] == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(line[pos])
                elif line[pos] == '/':
                    self.state.append("FOUND_SLASH")
                elif line[pos] == '\'':
                    self.state.pop()
                    assert self.state == ["NO_COMMENT"]
                    self.outbuf.append_nonspace(line[pos])
                else:
                    self.outbuf.append_nonspace(line[pos])
            elif self.state[-1] == "FOUND_SLASH":
                if line[pos] == '/':
                    self.state.pop()
                    self.state.append("IN_INLINE_COMMENT")
                elif line[pos] == '*':
                    self.state.pop()
                    self.state.append("IN_BLOCK_COMMENT")
                else:
                    self.state.pop()
                    self.outbuf.append_char('/')
                    pos -= 1
            elif self.state[-1] == "IN_BLOCK_COMMENT":
                if line[pos] == '*':
                    self.state.append("IN_BLOCK_COMMENT_FOUND_STAR")
            elif self.state[-1] == "IN_BLOCK_COMMENT_FOUND_STAR":
                if line[pos] == '/':
                    self.state.pop()
                    assert self.state[-1] == "IN_BLOCK_COMMENT"
                    self.state.pop()
                    assert self.state == ["NO_COMMENT"]
                    self.outbuf.append_space()
                elif line[pos] != '*':
                    self.state.pop()
                    assert self.state[-1] == "IN_BLOCK_COMMENT"
            elif self.state[-1] == "ESCAPING":
                self.outbuf.append_nonspace(line[pos])
                self.state.pop()
            elif self.state[-1] == "IN_INLINE_COMMENT":
                return
            pos += 1

def c_file_source(fp):

    current_physical_line = one_space_line()
    cleaner = c_cleaner(current_physical_line)

    current_logical_line = one_space_line()

    current_physical_start = 1
    total_sloc = 0
    local_sloc = 0

    physical_line_num = 0
    for (physical_line_num, line) in enumerate(fp, start=1):
        current_physical_line.__init__()
        end = len(line)
        if line[-1] == '\n':
            end -= 1
        else:
            if end > 0 and line[end-1] == '\\':
                raise RuntimeError("file seems to end in \\ with no newline!")

        if end > 0 and line[end-1] == '\\':
            continued = True
            end -= 1
        else:
            continued = False
        cleaner.process(line, 0, end)
        if not continued:
            cleaner.logical_newline()

        if not current_physical_line.is_blank():
            local_sloc += 1

        current_logical_line.join(current_physical_line)

        if not continued:
            if not current_logical_line.is_blank():
                yield ((current_physical_start, physical_line_num+1), local_sloc, current_logical_line.flush())
            else:
                current_logical_line.__init__()
                assert local_sloc == 0

            current_physical_start = physical_line_num + 1
            total_sloc += local_sloc
            local_sloc = 0

    total_physical_lines = physical_line_num

    if not current_logical_line.is_blank():
        yield ((current_physical_start, physical_line_num+1), local_sloc, current_logical_line.flush())

    total_sloc += local_sloc
    assert cleaner.state == ["NO_COMMENT"]

    return (total_sloc, total_physical_lines)
