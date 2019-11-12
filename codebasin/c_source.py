# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes and functions for stripping comments and whitespace from C/C++ files
"""

import itertools as it
from os.path import splitext

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
    def category(self):
        res = "SRC_NONBLANK"
        if len(self.parts) == 0:
            res = "BLANK"
        elif len(self.parts) == 1:
            if self.parts[0] == ' ':
                res = "BLANK"
            elif self.parts[0] == '#':
                res = "CPP_DIRECTIVE"
        elif ( self.parts[0] == ' ' and self.parts[1] == '#' ) or self.parts[0] == '#':
            res = "CPP_DIRECTIVE"
        return res
    def flush(self):
        res= ''.join(self.parts)
        self.__init__()
        return res

class iter_keep1(object):
    def __init__(self, iterator):
        self.iterator = iter(iterator)
        self.single = None
    def __iter__(self):
        return self
    def __next__(self):
        if self.single is not None:
            res, self.single = self.single, None
            return res
        else:
            return next(self.iterator)
    def putback(self, item):
        assert self.single is None
        self.single = item

class c_cleaner(object):
    def __init__(self, outbuf, directives_only=False):
        self.state = ["TOPLEVEL"]
        self.outbuf = outbuf
        self.directives_only = directives_only
    def logical_newline(self):
        if self.state[-1] == "IN_INLINE_COMMENT":
            self.state = ["TOPLEVEL"]
            self.outbuf.append_space()
        elif self.state[-1] == "FOUND_SLASH":
            self.state = ["TOPLEVEL"]
            self.outbuf.append_nonspace('/')
        elif self.state[-1] == "SINGLE_QUOTATION":
            # This probably should give a warning
            self.state = ["TOPLEVEL"]
        elif self.state[-1] == "DOUBLE_QUOTATION":
            # This probably should give a warning
            self.state == ["TOPLEVEL"]
        elif self.state[-1] == "IN_BLOCK_COMMENT_FOUND_STAR":
            self.state.pop()
            assert self.state[-1] == "IN_BLOCK_COMMENT"
        elif self.state[-1] == "CPP_DIRECTIVE":
            self.state = ["TOPLEVEL"]
    def process(self, lineiter):
        inbuffer = iter_keep1(lineiter)
        for char in inbuffer:
            if self.state[-1] == "TOPLEVEL":
                if self.directives_only:
                    if char == '\\':
                        self.state.append("ESCAPING")
                        self.outbuf.append_nonspace(char)
                    elif char == '#' and self.outbuf.category() == "BLANK":
                        self.state.append("CPP_DIRECTIVE")
                        self.outbuf.append_nonspace(char)
                    else:
                        self.outbuf.append_char(char)
                else:
                    if char == '\\':
                        self.state.append("ESCAPING")
                        self.outbuf.append_nonspace(char)
                    elif char == '/':
                        self.state.append("FOUND_SLASH")
                    elif char == '"':
                        self.state.append("DOUBLE_QUOTATION")
                        self.outbuf.append_nonspace(char)
                    elif char == '\'':
                        self.state.append("SINGLE_QUOTATION")
                        self.outbuf.append_nonspace(char)
                    elif char == '#' and self.outbuf.category() == "BLANK":
                        self.state.append("CPP_DIRECTIVE")
                        self.outbuf.append_nonspace(char)
                    else:
                        self.outbuf.append_char(char)
            elif self.state[-1] == "CPP_DIRECTIVE":
                if char == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(char)
                elif char == '/':
                    self.state.append("FOUND_SLASH")
                elif char == '"':
                    self.state.append("DOUBLE_QUOTATION")
                    self.outbuf.append_nonspace(char)
                elif char == '\'':
                    self.state.append("SINGLE_QUOTATION")
                    self.outbuf.append_nonspace(char)
                else:
                    self.outbuf.append_char(char)
            elif self.state[-1] == "DOUBLE_QUOTATION":
                if char == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(char)
                elif char == '"':
                    self.state.pop()
                    self.outbuf.append_nonspace(char)
                else:
                    self.outbuf.append_nonspace(char)
            elif self.state[-1] == "SINGLE_QUOTATION":
                if char == '\\':
                    self.state.append("ESCAPING")
                    self.outbuf.append_nonspace(char)
                elif char == '/':
                    self.state.append("FOUND_SLASH")
                elif char == '\'':
                    self.state.pop()
                    self.outbuf.append_nonspace(char)
                else:
                    self.outbuf.append_nonspace(char)
            elif self.state[-1] == "FOUND_SLASH":
                if char == '/':
                    self.state.pop()
                    self.state.append("IN_INLINE_COMMENT")
                elif char == '*':
                    self.state.pop()
                    self.state.append("IN_BLOCK_COMMENT")
                else:
                    self.state.pop()
                    self.outbuf.append_char('/')
                    inbuffer.putback(char)
            elif self.state[-1] == "IN_BLOCK_COMMENT":
                if char == '*':
                    self.state.append("IN_BLOCK_COMMENT_FOUND_STAR")
            elif self.state[-1] == "IN_BLOCK_COMMENT_FOUND_STAR":
                if char == '/':
                    self.state.pop()
                    assert self.state[-1] == "IN_BLOCK_COMMENT"
                    self.state.pop()
                    self.outbuf.append_space()
                elif char != '*':
                    self.state.pop()
                    assert self.state[-1] == "IN_BLOCK_COMMENT"
            elif self.state[-1] == "ESCAPING":
                self.outbuf.append_nonspace(char)
                self.state.pop()
            elif self.state[-1] == "IN_INLINE_COMMENT":
                return
            else:
                assert None

class fortran_cleaner(object):
    def __init__(self, outbuf):
        self.state = ["TOPLEVEL"]
        self.outbuf = outbuf
        self.verify_continue = []
    def dir_check(self, inbuffer):
        self.found=['!']
        for char in inbuffer:
            if char == '$':
                self.found.append('$')
                for char in self.found:
                    self.outbuf.append_nonspace(char)
                break
            elif char.isalpha():
                self.found.append(char)
            else:
                return
    def process(self, lineiter):
        inbuffer = iter_keep1(lineiter)
        try:
            while True:
                char = next(inbuffer)
                if self.state[-1] == "TOPLEVEL":
                    if char == '\\':
                        self.state.append("ESCAPING")
                        self.outbuf.append_nonspace(char)
                    elif char == '!':
                        self.dir_check(inbuffer)
                        self.state = ["TOPLEVEL"]
                        break
                    elif char == '&':
                        self.verify_continue.append(char)
                        self.state.append("VERIFY_CONTINUE")
                    elif char == '"':
                        self.state.append("DOUBLE_QUOTATION")
                        self.outbuf.append_nonspace(char)
                    elif char == '\'':
                        self.state.append("SINGLE_QUOTATION")
                        self.outbuf.append_nonspace(char)
                    else:
                        self.outbuf.append_char(char)
                elif self.state[-1] == 'CONTINUING_FROM_SOL':
                    if is_whitespace(char):
                        self.outbuf.append_space()
                    elif char == '&':
                        self.state.pop()
                    elif char == '!':
                        self.dir_check(inbuffer)
                        break
                    else:
                        self.state.pop()
                        inbuffer.putback(char)
                        # should complain if we are quoting here, but will ignore for now
                elif self.state[-1] == "DOUBLE_QUOTATION":
                    if char == '\\':
                        self.state.append("ESCAPING")
                        self.outbuf.append_nonspace(char)
                    elif char == '"':
                        self.state.pop()
                        self.outbuf.append_nonspace(char)
                    elif char == '&':
                        self.verify_continue.append(char)
                        self.state.append("VERIFY_CONTINUE")
                    else:
                        self.outbuf.append_nonspace(char)
                elif self.state[-1] == "SINGLE_QUOTATION":
                    if char == '\\':
                        self.state.append("ESCAPING")
                        self.outbuf.append_nonspace(char)
                    elif char == '\'':
                        self.state.pop()
                        self.outbuf.append_nonspace(char)
                    elif char == '&':
                        self.verify_continue.append(char)
                        self.state.append("VERIFY_CONTINUE")
                    else:
                        self.outbuf.append_nonspace(char)
                elif self.state[-1] == "ESCAPING":
                    self.outbuf.append_nonspace(char)
                    self.state.pop()
                elif self.state[-1] == "VERIFY_CONTINUE":
                    if char == '!' and self.state[-2] == "TOPLEVEL":
                        self.dir_check(inbuffer)
                        break
                    elif not is_whitespace(char):
                        for tmp in self.verify_continue:
                            self.outbuf.append_nonspace(tmp)
                        self.verify_continue = []
                        self.state.pop()
                        inbuffer.putback(char)
                else:
                    assert None
        except StopIteration:
            pass
        if self.state[-1] == "CONTINUING_TO_EOL":
            self.state[-1] = "CONTINUING_FROM_SOL"
        elif self.state[-1] == "VERIFY_CONTINUE":
            self.state[-1] = "CONTINUING_FROM_SOL"

def c_file_source(fp, relaxed=False, directives_only=False):

    current_physical_line = one_space_line()
    cleaner = c_cleaner(current_physical_line, directives_only)

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
        cleaner.process(it.islice(line, 0, end))
        if not continued:
            cleaner.logical_newline()

        if not current_physical_line.category() == "BLANK":
            local_sloc += 1

        current_logical_line.join(current_physical_line)

        if not continued:
            line_cat = current_logical_line.category()
            if line_cat != "BLANK":
                yield ((current_physical_start, physical_line_num+1), local_sloc, current_logical_line.flush(), line_cat)
            else:
                current_logical_line.__init__()
                assert local_sloc == 0

            current_physical_start = physical_line_num + 1
            total_sloc += local_sloc
            local_sloc = 0

    total_physical_lines = physical_line_num

    line_cat = current_logical_line.category()
    if line_cat != "BLANK":
        yield ((current_physical_start, physical_line_num+1), local_sloc, current_logical_line.flush(), line_cat)

    total_sloc += local_sloc
    if not relaxed:
        assert cleaner.state == ["TOPLEVEL"]

    return (total_sloc, total_physical_lines)

def fortran_file_source(fp, relaxed=False):

    current_physical_line = one_space_line()
    cleaner = fortran_cleaner(current_physical_line)

    current_logical_line = one_space_line()

    current_physical_start = None
    total_sloc = 0
    local_sloc = 0

    c_walker = c_file_source(fp, directives_only=True)
    try:
        while True:
            ((src_physical_start, src_physical_end), src_line_sloc, src_line, c_category) = next(c_walker)
            #if it's a cpp directive, flush what we have, then emit the directive and start over
            if current_physical_start == None:
                current_physical_start = src_physical_start

            if c_category == "CPP_DIRECTIVE":
                line_cat = current_logical_line.category()
                if line_cat != "BLANK":
                    yield ((current_physical_start, src_physical_end), local_sloc, current_logical_line.flush(), line_cat)
                else:
                    current_logical_line.__init__()
                    assert local_sloc == 0

                current_physical_start = None
                total_sloc += local_sloc
                local_sloc = 0
                yield ((src_physical_start, src_physical_end), src_line_sloc, src_line, c_category)
                total_sloc += src_line_sloc
                continue

            current_physical_line.__init__()
            cleaner.process(it.islice(src_line, 0, len(src_line)))

            if not current_physical_line.category() == "BLANK":
                local_sloc += src_line_sloc

            current_logical_line.join(current_physical_line)

            if cleaner.state[-1] != "CONTINUING_FROM_SOL":
                line_cat = current_logical_line.category()
                if line_cat != "BLANK":
                    yield ((current_physical_start, src_physical_end), local_sloc, current_logical_line.flush(), line_cat)
                else:
                    current_logical_line.__init__()
                    assert local_sloc == 0

                current_physical_start = None
                total_sloc += local_sloc
                local_sloc = 0
    except StopIteration as stopit:
        _, total_physical_lines = stopit.value

    line_cat = current_logical_line.category()
    if line_cat != "BLANK":
        yield ((current_physical_start, total_physical_lines), local_sloc, current_logical_line.flush(), line_cat)

    total_sloc += local_sloc
    if not relaxed:
        assert cleaner.state == ["TOPLEVEL"]

    return (total_sloc, total_physical_lines)


global extension_map
extension_map = {'.f90' : "FREEFORM FORTRAN",
                 '.cxx' : "C FAMILY",
                 '.cl' : "C FAMILY",
                 '.cu' : "C FAMILY",
                 '.cpp' : "C FAMILY",
                 '.c' : "C FAMILY",
                 '.h' : "C FAMILY",
                 '.hpp' : "C FAMILY"}

def guess_language(fname):
    _, ext = splitext(fname)
    try:
        return extension_map[ext.lower()]
    except KeyError:
        return "Unknown"

def get_file_source(path):
    lang = guess_language(path)
    if lang == "FREEFORM FORTRAN":
        return fortran_file_source
    elif lang == "C FAMILY":
        return c_file_source
    else:
        return None
