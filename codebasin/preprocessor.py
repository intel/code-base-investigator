# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
"""
Contains classes that define:
- Nodes from the tree
- Tokens from lexing a line of code
- Operators to handle tokens
"""

import collections
import logging
import os
from collections.abc import Callable, Iterable
from copy import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Self

import numpy as np

from codebasin import util

log = logging.getLogger(__name__)


def _representation_string(obj, *, name=None, attrs=None):
    """
    Helper function to build representation strings of the form:
    Name(attribute={attribute!r},...)
    """
    if not name:
        name = obj.__class__.__name__
    if not attrs:
        attrs = obj.__dict__
    properties = ",".join(f"{a}={getattr(obj, a)!r}" for a in attrs)
    return f"{name}({properties})"


class TokenError(ValueError):
    """
    Represents an error encountered during tokenization.
    """


class EndofParse(ValueError):
    """
    Represents end of token stream.
    """


class MacroExpandOverflow(ValueError):
    """
    Represents MacroExpander overflow
    """


@dataclass
class Token:
    """
    Represents a token constructed by the parser.
    """

    line: int
    col: int
    prev_white: bool
    token: str

    def __str__(self):
        return "\n".join(self.spelling())

    def spelling(self):
        """
        Return the string representation of this token in the input code.
        Useful primarily for debugging and generating error messages.
        """
        return [str(self.token)]

    def sanitized_str(self):
        """
        Dummy based implementation of string sanitization.
        Overloaded for String Constant.
        """
        return str(self)


@dataclass
class CharacterConstant(Token):
    """
    Represents a character constant.
    """


@dataclass
class NumericalConstant(Token):
    """
    Represents a 'preprocessing number'.
    These cannot necessarily be evaluated by the preprocessor (and may
    not be valid syntax).
    """


@dataclass
class StringConstant(Token):
    """
    Represents a string constant.
    """

    def spelling(self):
        """
        Return the string representation of this token in the input code.
        Useful primarily for debugging and generating error messages.
        """
        return [f'"{self.token!s}"']

    def sanitized_str(self):
        """
        Return this string quoted for stringification.
        """
        out = [r"\""]
        c = 0
        while c < len(self.token):
            if self.token[c] == "\\":
                if c + 1 < len(self.token) and self.token[c + 1] == '"':
                    out.append(r"\\\"")
                    c += 1
                else:
                    out.append("\\\\")
            else:
                out.append(self.token[c])
            c += 1
        out.append(r"\"")
        return "".join(out)


@dataclass
class Identifier(Token):
    """
    Represents a C identifier.
    """

    expandable: bool = field(default=True, init=True)


@dataclass
class Operator(Token):
    """
    Represents a C operator.
    """


@dataclass
class Punctuator(Token):
    """
    Represents a punctuator (e.g. parentheses)
    """


@dataclass
class Unknown(Token):
    """
    Represents an unknown token.
    """


class Lexer:
    """
    A lexer for the C preprocessor grammar.
    """

    def __init__(self, string, line="Unknown"):
        self.string = string
        self.line = line
        self.pos = 0
        self.prev_white = False

    def read(self, n=1):
        """
        Return the next n characters in the string.
        """
        return self.string[self.pos : self.pos + n]

    def eos(self):
        """
        Return True when the end of the string is reached.
        """
        return self.pos == len(self.string)

    def whitespace(self):
        """
        Consume whitespace and advance position.
        """
        while not self.eos() and self.read() in [" ", "\t", "\n", "\r"]:
            self.pos += 1
            self.prev_white = True

    def match(self, literal):
        """
        Match a character/string literal exactly and advance position.
        """
        if self.read(len(literal)) == literal:
            self.pos += len(literal)
        else:
            raise TokenError()

    def match_any(self, literals):
        """
        Match one from a list of character/string literals exactly.
        Return the matched index and advance position.
        """
        for index, literal in enumerate(literals):
            if self.read(len(literal)) == literal:
                self.pos += len(literal)
                return index

        raise TokenError()

    def number(self):
        """
        Construct a NumericalConstant by parsing a string.
        Return a NumericalConstant and advance position.

        <exponent> := ['e'|'E'|'p'|'P']['+'|'-']
        <number> := .?<digit>[<alpha>|<digit>|'_'|'.'|<exponent>]*
        """
        col = self.pos
        try:
            chars = []

            # Match optional period
            if self.read() == ".":
                chars.append(self.read())
                self.pos += 1

            # Match required decimal digit
            if self.read().isdigit():
                chars.append(self.read())
                self.pos += 1
            else:
                raise TokenError("Expected digit.")

            # Match any sequence of letters, digits, underscores,
            # periods and exponents
            exponents = ["e+", "e-", "E+", "E-", "p+", "p-", "P+", "P-"]
            while not self.eos():
                if self.read(2) in exponents:
                    chars.append(self.read(2))
                    self.pos += 2
                elif (
                    self.read().isalpha()
                    or self.read().isdigit()
                    or self.read() in ["_", "."]
                ):
                    chars.append(self.read())
                    self.pos += 1
                else:
                    break

            value = "".join(chars)
        except TokenError:
            self.pos = col
            raise TokenError("Invalid preprocessing number.")

        constant = NumericalConstant(self.line, col, self.prev_white, value)
        return constant

    def character_constant(self):
        """
        Construct a CharacterConstant by parsing a string.
        Return a CharacterConstant and advance position.

        <character-constant> := '''<alpha>'''
        """
        col = self.pos
        try:
            self.match("'")

            # A character constant may be an escaped sequence
            # We assume a single alpha-numerical character or space
            if self.read() == "\\" and self.read(2).isprintable():
                value = self.read(2)
                self.pos += 2
            elif self.read().isprintable():
                value = self.read()
                self.pos += 1
            else:
                raise TokenError("Expected character.")

            self.match("'")
        except TokenError:
            self.pos = col
            raise TokenError("Invalid character constant.")

        constant = CharacterConstant(self.line, col, self.prev_white, value)
        return constant

    def string_constant(self):
        """
        Construct a StringConstant by parsing a string.
        Return a StringConstant and advance position.

        <string-constant> := '"'.*'"'
        """
        col = self.pos
        try:
            self.match('"')

            chars = []
            while not self.eos() and self.read() != '"':
                # An escaped " should not close the string
                if self.read(2) == '\\"':
                    chars.append(self.read(2))
                    self.pos += 2
                else:
                    chars.append(self.read())
                    self.pos += 1

            self.match('"')
        except TokenError:
            self.pos = col
            raise TokenError("Invalid string constant.")

        constant = StringConstant(
            self.line,
            col,
            self.prev_white,
            "".join(chars),
        )
        return constant

    @staticmethod
    def stringify(tokens):
        """
        Return a tokenized string version of an input series of tokens.
        """
        parts = ['"']
        for p in tokens:
            if p.prev_white:
                parts.append(" ")
            parts.append(p.sanitized_str())
        parts.append('"')
        return Lexer("".join(parts)).tokenize_one()

    def identifier(self):
        """
        Construct an Identifier by parsing a string.
        Return an Identifier and advance position.

        <identifier> := [<alpha>|'_'][<alpha>|<digit>|'_']*
        """
        col = self.pos

        # Match a string of characters
        characters = []
        while not self.eos() and (self.read().isalnum() or self.read() == "_"):
            # First character of an identifier cannot be a digit
            if self.pos == col and self.read().isdigit():
                self.pos = col
                raise TokenError("Identifiers cannot start with a digit.")

            characters += self.read()
            self.pos += 1

        if not characters:
            self.pos = col
            raise TokenError("Invalid identifier.")

        identifier = Identifier(
            self.line,
            col,
            self.prev_white,
            "".join(characters),
        )
        return identifier

    def operator(self):
        """
        Construct an Operator by parsing a string.
        Return an Operator and advance position.

        <op> := ['-' | '+' | '!' | '#' | '~' | '*' | '/' | '|' | '&' |
                 '^' | '||' | '&&' | '>>' | '<<' | '!=' | '>=' | '<=' |
                 '==' | '##' | '?' | ':' | '<' | '>' | '%']
        """
        col = self.pos
        operators = ["||", "&&", ">>", "<<", "!=", ">=", "<=", "==", "##"] + [
            "-",
            "+",
            "!",
            "*",
            "/",
            "|",
            "&",
            "^",
            "<",
            ">",
            "?",
            ":",
            "~",
            "#",
            "=",
            "%",
        ]
        try:
            index = self.match_any(operators)

            op = Operator(self.line, col, self.prev_white, operators[index])
            return op
        except TokenError:
            self.pos = col
            raise TokenError("Invalid operator.")

    def punctuator(self):
        """
        Construct a Punctuator by parsing a string.
        Return a Punctuator and advance position.

        <punc> := ['('|')'|'{'|'}'|'['|']'|','|'.'|';'|'''|'"'|'\']
        """
        col = self.pos
        punctuators = [
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            ",",
            ".",
            ";",
            "'",
            '"',
            "\\",
        ]
        try:
            index = self.match_any(punctuators)

            punc = Punctuator(
                self.line,
                col,
                self.prev_white,
                punctuators[index],
            )
            return punc
        except TokenError:
            self.pos = col
            raise TokenError("Invalid punctuator.")

    def tokenize_one(self):
        """
        Consume and return next token. Returns None if not possible.
        """
        candidates = [
            self.number,
            self.character_constant,
            self.string_constant,
            self.identifier,
            self.operator,
            self.punctuator,
        ]
        token = None
        for f in candidates:
            col = self.pos
            pws = self.prev_white
            try:
                token = f()
                self.prev_white = False
                break
            except TokenError:
                self.pos = col
                self.prev_white = pws
        return token

    def tokenize(self):
        """
        Return a list of all tokens in the string.
        """
        tokens = []
        self.whitespace()
        while not self.eos():
            # Try to match a new token
            token = self.tokenize_one()

            # Treat unmatched single characters as unknown tokens
            if token is None:
                token = Unknown(
                    self.line,
                    self.pos,
                    self.prev_white,
                    self.read(),
                )
                self.prev_white = False
                self.pos += 1
            tokens.append(token)

            self.whitespace()

        if not self.eos():
            raise TokenError("Encountered invalid token.")

        return tokens


class ParseError(ValueError):
    """
    Represents an error encountered during parsing.
    """


class Visit(Enum):
    NEXT = 0
    NEXT_SIBLING = 1


@dataclass(eq=False)
class Node:
    """
    Base class for all other Node types.
    Contains a single parent, and an ordered list of children.
    """

    children: list[Self] = field(default_factory=list, init=False)
    parent: Self | None = field(default=None, init=False)

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    @staticmethod
    def is_start_node():
        """
        Used to determine if a node is a start node of a tree.
        Return False by default.
        """
        return False

    @staticmethod
    def is_cont_node():
        """
        Used to determine if a node is a continue node of a tree.
        Return False by default.
        """
        return False

    @staticmethod
    def is_end_node():
        """
        Used to determine if a node is a end node of a tree.
        Return False by default.
        """
        return False

    def evaluate_for_platform(self, **kwargs):
        """
        Determine if the children of this node are active, by evaluating
        the statement.
        Return False by default.
        """
        return False

    def walk(self) -> Iterable[Self]:
        """
        Returns
        -------
        Iterable[Self]
            An Iterable visiting all descendants of this node via a preorder
            traversal.
        """
        yield self
        for child in self.children:
            yield from child.walk()

    def visit(self, visitor: Callable[[Self], Visit]):
        """
        Visit all descendants of this node via a preorder traversal, using the
        supplied visitor.

        Raises
        ------
        TypeError
            If `visitor` is not callable.
        """
        if not callable(visitor):
            raise TypeError("visitor is not callable.")
        if visitor(self) != Visit.NEXT_SIBLING:
            for child in self.children:
                child.visit(visitor)


@dataclass(eq=False)
class FileNode(Node):
    """
    Typically the root node of a tree. Simply contains a filename after
    inheriting from the Node class.
    """

    filename: str
    num_lines: int = field(default=0, init=False)
    total_sloc: int = field(default=0, init=False)

    def __str__(self):
        return str(self.filename)

    def evaluate_for_platform(self, **kwargs):
        """
        Since a FileNode is always used as a root node, we are only
        interested in its children.
        """
        return True


@dataclass(eq=False, init=False)
class CodeNode(Node):
    """
    Represents any line of code. Contains a start and end line, and the
    number of countable lines occurring between them. Optionally contains
    the original source.
    """

    start_line: int = field(default=-1, init=False)
    end_line: int = field(default=-1, init=False)
    num_lines: int = field(default=0, init=False)
    source: str | None = field(default=None, init=False, repr=False)
    lines: list[str] | None = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __init__(
        self,
        start_line: int = -1,
        end_line: int = -1,
        num_lines: int = 0,
        source: str | None = None,
        lines: list[int] | None = None,
    ):
        super().__init__()
        self.start_line = start_line
        self.end_line = end_line
        self.num_lines = num_lines
        if lines is None:
            self.lines = []
        else:
            self.lines = lines
        self.source = source

    def __str__(self):
        start = self.start_line
        end = self.end_line
        sloc = self.num_lines
        return f"Lines {start}-{end}; SLOC = {sloc};"

    def spelling(self):
        """
        Return the string representation of this code block in the input code.
        Useful primarily for debugging and generating error messages.

        If configured to summarize the input code, the spelling of a CodeNode
        reflects only the total number of lines between preprocessor
        directives.
        """
        if self.source:
            return self.source
        else:
            return [f"/* {self.num_lines} SLOC omitted */"]


@dataclass(eq=False)
class DirectiveNode(CodeNode):
    """
    A CodeNode representing a C preprocessor directive.
    We need to track all of the tokens for this directive in addition to
    countable lines and extent.
    """

    tokens: list[Token]

    def spelling(self) -> list[str]:
        """
        Recover the original spelling of this directive in the input code.
        Useful primarily for debugging and generating error messages.

        Returns
        -------
        list[str]
            The string representation of this directive in the input code.
        """
        out = []
        for token in self.tokens:
            if not token:
                continue
            if token.prev_white:
                out.append(" ")
            out.append(str(token))
        return ["".join(out)]


@dataclass(eq=False)
class UnrecognizedDirectiveNode(DirectiveNode):
    """
    A CodeNode representing an unrecognized preprocessor directive
    """


@dataclass(eq=False)
class PragmaNode(DirectiveNode):
    """
    Represents a #pragma directive
    """

    expr: list[Token]

    def evaluate_for_platform(self, **kwargs):
        if self.expr and str(self.expr[0]) == "once":
            kwargs["platform"].add_include_to_skip(kwargs["filename"])


@dataclass(eq=False)
class DefineNode(DirectiveNode):
    """
    A DirectiveNode representing a #define directive.
    """

    identifier: Identifier
    args: list[Token] | None = None
    value: list[Token] | None = None

    def evaluate_for_platform(self, **kwargs):
        """
        Add a definition into the platform, and return false
        """
        macro = make_macro(self.identifier, self.args, self.value)
        kwargs["platform"].define(self.identifier.token, macro)
        return False


@dataclass(eq=False)
class UndefNode(DirectiveNode):
    """
    A DirectiveNode representing an #undef directive.
    """

    identifier: Identifier

    def evaluate_for_platform(self, **kwargs):
        """
        Add a definition into the platform, and return false
        """
        kwargs["platform"].undefine(self.identifier.token)
        return False


class IncludePath:
    """
    Represents an include path enclosed by "" or <>
    """

    def __init__(self, path, system):
        self.path = path
        self.system = system

    def __repr__(self):
        return _representation_string(self)

    def spelling(self):
        """
        Return the string representation of this path in the input code.
        Useful primarily for debugging and generating error messages.

        Assumes that system includes are declared in <>, while non-system
        includes are declared in quotes.
        """
        if self.system:
            return [f"<{self.path!s}>"]
        return [f'"{self.path!s}"']

    def is_system_path(self):
        return self.system


@dataclass(eq=False)
class IncludeNode(DirectiveNode):
    """
    A DirectiveNode representing an #include directive.
    Its value is an IncludePath or a list of tokens.
    """

    value: IncludePath | list[Token]

    def evaluate_for_platform(self, **kwargs):
        """
        Extract the filename from the #include. This cannot happen when
        parsing because of "computed includes" like #include FOO. After
        the filename is extracted, process the include file: build a
        tree for it, and walk it, updating the platform definitions.
        """

        include_path = None
        is_system_include = False
        if isinstance(self.value, IncludePath):
            include_path = self.value.path
            is_system_include = self.value.system
        else:
            expansion = MacroExpander(kwargs["platform"]).expand(self.value)
            path_obj = DirectiveParser(expansion).include_path()
            include_path = path_obj.path
            is_system_include = path_obj.system

        this_path = os.path.dirname(kwargs["filename"])
        include_file = kwargs["platform"].find_include_file(
            include_path,
            this_path,
            is_system_include,
        )

        if include_file and kwargs["platform"].process_include(include_file):
            # include files use the same language as the file itself,
            # irrespective of file extension.
            lang = kwargs["state"].langs[kwargs["filename"]]
            kwargs["state"].insert_file(include_file, lang)
            kwargs["state"].associate(include_file, kwargs["platform"])

        if not include_file:
            filename = kwargs["filename"]
            line = self.start_line
            spelling = self.spelling()[0]
            kind = "system include" if is_system_include else "user include"
            log.warning(
                f"{filename}:{line}: {kind} '{include_path}' not found\n"
                + f"{line:>5} | {spelling}",
            )


@dataclass(eq=False)
class IfNode(DirectiveNode):
    """
    Represents an #if, #ifdef or #ifndef directive.
    """

    expr: list[Token]

    @staticmethod
    def is_start_node():
        return True

    def evaluate_for_platform(self, **kwargs):
        # Perform macro substitution with tokens
        expanded_tokens = MacroExpander(kwargs["platform"]).expand(self.expr)

        # Evaluate the expanded tokens
        return ExpressionEvaluator(expanded_tokens).evaluate()


@dataclass(eq=False)
class ElIfNode(IfNode):
    """
    Represents an #elif directive.
    """

    @staticmethod
    def is_start_node():
        return False

    @staticmethod
    def is_cont_node():
        return True


@dataclass(eq=False)
class ElseNode(DirectiveNode):
    """
    Represents an #else directive.
    """

    @staticmethod
    def is_cont_node():
        return True

    def evaluate_for_platform(self, **kwargs):
        return True


@dataclass(eq=False)
class EndIfNode(DirectiveNode):
    """
    Represents an #endif directive.
    """

    @staticmethod
    def is_end_node():
        return True


class Parser:
    """
    A generic token parser for matching tokens from a list.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def cursor(self):
        """
        Return the current token in the list.
        """
        try:
            return self.tokens[self.pos]
        except IndexError:
            raise ParseError("No tokens left for cursor to traverse")

    def eol(self):
        """
        Return True when the end of the list is reached.
        """
        return self.pos == len(self.tokens)

    def match_type(self, token_type):
        """
        Match a token of the specified type and advance position.
        """
        if isinstance(self.cursor(), token_type):
            token = self.cursor()
            self.pos += 1
        else:
            raise ParseError(f"Expected {token_type!s}.")
        return token

    def match_value(self, token_type, token_value):
        """
        Match a token of the specified type and value, and advance
        position.
        """
        if (
            isinstance(self.cursor(), token_type)
            and self.cursor().token == token_value
        ):
            token = self.cursor()
            self.pos += 1
        else:
            raise ParseError(f"Expected {token_value!s}.")
        return token


class DirectiveParser(Parser):
    """
    A specialized token parser for recognizing directives.
    """

    def __arg(self):
        """
        Match an Identifier, Identifier... or ...

        <arg> := <identifier>?'...'
        """
        arg = None

        # Match optional identifier
        initial_pos = self.pos
        try:
            arg = self.match_type(Identifier)
        except ParseError:
            self.pos = initial_pos

        # Match optional '...'
        ellipsis_pos = self.pos
        try:
            punc = self.match_value(Punctuator, ".")
            self.match_value(Punctuator, ".")
            self.match_value(Punctuator, ".")
            if arg is None:
                arg = Identifier(punc.line, punc.col, punc.prev_white, "...")
            else:
                arg.token += "..."
        except ParseError:
            self.pos = ellipsis_pos

        if arg is not None:
            return arg
        raise ParseError("Invalid argument")

    def __arg_list(self):
        """
        Match a comma-separated list of arguments.
        Return a tuple of the Token(s) and advances position..

        <arg-list> := [<arg>[','<arg>]*]?
        """
        args = []
        try:
            arg = self.__arg()
            args.append(arg)
            if arg.token.endswith("..."):
                return args

            while True:
                self.match_value(Punctuator, ",")

                arg = self.__arg()
                args.append(arg)
                if arg.token.endswith("..."):
                    return args

        except ParseError:
            return args

    def macro_definition(self):
        """
        Match a macro definition.
        Return a tuple of the Identifier and argument list (or None).
        """
        identifier = self.match_type(Identifier)

        # Match function-like macro definitions
        arg_pos = self.pos
        try:
            # Read a list of arguments between parentheses.
            # whitespace is NOT permitted before the opening paren.
            punctuator = self.match_value(Punctuator, "(")
            if punctuator.prev_white:
                raise ParseError("Not a function-like macro.")
            args = self.__arg_list()
            punctuator = self.match_value(Punctuator, ")")
        except ParseError:
            args = None
            self.pos = arg_pos

        return (identifier, args)

    def define(self):
        """
        Match a define directive.
        Return a tuple of the Define and the new string position.

        <define-macro>    := 'define'<identifier><token-list>?
        <define-function> := 'define'<identifier>
                             '('<identifier-list>?')'
                             <token-list>?
        <identifier-list> := [<identifier>][','<identifier>]*
        <define>          := [<define-macro>|<define-function>]
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "define")
            (identifier, args) = self.macro_definition()

            # Any remaining tokens are the macro expansion
            if not self.eol():
                expansion = self.tokens[self.pos :]
                self.pos = len(self.tokens)
            else:
                expansion = []

            return DefineNode(self.tokens, identifier, args, expansion)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid define directive.")

    def undef(self):
        """
        Match an #undef directive.
        Return an UndefNode.

        <undef> := 'undef'<identifier>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "undef")
            identifier = self.match_type(Identifier)
            return UndefNode(self.tokens, identifier)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid undef directive.")

    def include(self):
        """
        Match an #include directive.
        Return an IncludeNode.

        <include> := 'include'<token-list>
        """
        initial_pos = self.pos

        try:
            self.match_value(Identifier, "include")

            path_pos = self.pos

            # Match system or local include path
            try:
                include_payload = self.include_path()
            except ParseError:
                include_payload = self.tokens[path_pos:]
                self.pos = len(self.tokens)

            return IncludeNode(self.tokens, include_payload)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid include directive.")

    def __path(
        self,
        marker_type=Punctuator,
        initiator_value='"',
        terminator_value='"',
    ):
        """
        Match a path enclosed between the specified initiator and
        terminator values.
        """
        path = []
        self.match_value(marker_type, initiator_value)
        while not self.eol() and not (
            isinstance(self.cursor(), marker_type)
            and self.cursor().token == terminator_value
        ):
            path.append(self.cursor())
            self.pos += 1
        self.match_value(marker_type, terminator_value)
        return path

    def include_path(self):
        """
        Match an include path.
        <include-path> := ['<'<path>'>'|'\"'<path>'>']
        """
        initial_pos = self.pos

        # Match system include
        try:
            path_tokens = self.__path(Operator, "<", ">")
            path_str = "".join([str(t) for t in path_tokens])
            if util.valid_path(path_str):
                return IncludePath(path_str, system=True)
        except ParseError:
            self.pos = initial_pos

        # Match local include
        try:
            path_token = self.match_type(StringConstant)
            path_str = path_token.token
            if util.valid_path(path_str):
                return IncludePath(path_str, system=False)
        except ParseError:
            self.pos = initial_pos

        raise ParseError("Invalid path.")

    def pragma(self):
        """
        Match a #pragma directive.
        Return a PragmaNode.

        <pragma> := 'pragma'<token-list>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "pragma")
            expr = self.tokens[self.pos :]
            self.pos = len(self.tokens)

            return PragmaNode(self.tokens, expr)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid pragma directive.")

    def if_(self):
        """
        Match an #if directive.
        Return an IfNode.

        <if> := 'if'<token-list>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "if")
            expr = self.tokens[self.pos :]
            self.pos = len(self.tokens)

            return IfNode(self.tokens, expr)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid if directive.")

    def ifdef(self):
        """
        Match an #ifdef directive.
        Return an IfNode with defined() in the expression.

        <ifdef> := 'ifdef'<token-list>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "ifdef")
            identifier = self.match_type(Identifier)

            # Wrap expression in "defined()" call
            prefix = [
                Identifier("Unknown", -1, True, "defined"),
                Punctuator("Unknown", -1, False, "("),
            ]
            suffix = [Punctuator("Unknown", -1, False, ")")]
            expr = prefix + [identifier] + suffix

            return IfNode(self.tokens, expr)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid ifdef directive")

    def ifndef(self):
        """
        Match an #ifdef directive.
        Return an IfNode with !defined() in the expression.

        <ifndef> := 'ifndef'<token-list>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "ifndef")
            identifier = self.match_type(Identifier)

            # Wrap expression in "!defined()" call
            prefix = [
                Operator("Unknown", -1, True, "!"),
                Identifier("Unknown", -1, False, "defined"),
                Punctuator("Unknown", -1, False, "("),
            ]
            suffix = [Punctuator("Unknown", -1, False, ")")]
            expr = prefix + [identifier] + suffix

            return IfNode(self.tokens, expr)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid ifndef directive")

    def elif_(self):
        """
        Match an #elif directive.
        Return an ElIfNode.

        <elif> := 'elif'<token-list>
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "elif")
            expr = self.tokens[self.pos :]
            self.pos = len(self.tokens)

            return ElIfNode(self.tokens, expr)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid elif directive.")

    def else_(self):
        """
        Match an #else directive.
        Return an ElseNode.

        <else> := 'else'
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "else")
            return ElseNode(self.tokens)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid else directive.")

    def endif(self):
        """
        Match an #endif directive.
        Return an EndIfNode.

        <endif> := 'endif'
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "endif")
            return EndIfNode(self.tokens)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid endif directive.")

    def parse(self):
        """
        Parse a preprocessor directive.
        Return a DirectiveNode.

        <directive> := '#'[<define>|<undef>|<include>|<ifdef>|<ifndef>|
                           <if>|<elif>|<else>|<endif>]
        """
        try:
            self.match_value(Operator, "#")

            # Check for a match against known directives
            candidates = [
                self.define,
                self.undef,
                self.include,
                self.ifdef,
                self.ifndef,
                self.if_,
                self.elif_,
                self.else_,
                self.endif,
                self.pragma,
            ]
            for f in candidates:
                try:
                    directive = f()
                    if not self.eol():
                        chars = "".join(str(x) for x in self.tokens)
                        log.warning(
                            f"Additional tokens at end of directive: {chars}",
                        )
                    return directive
                except ParseError:
                    pass

            return UnrecognizedDirectiveNode(self.tokens)
        except ParseError:
            raise ParseError("Not a directive.")


def macro_from_definition_string(string):
    """
    Construct a Macro or MacroFunction by parsing a string of the form
    MACRO=expansion.
    """
    tokens = Lexer(string).tokenize()
    parser = DirectiveParser(tokens)

    (identifier, args) = parser.macro_definition()

    # Any remaining tokens after an "=" are the macro expansion
    if not parser.eol():
        parser.match_value(Operator, "=")
        expansion = parser.tokens[parser.pos :]
        parser.pos = len(parser.tokens)
    else:
        expansion = [NumericalConstant("Unknown", None, False, "1")]

    return make_macro(identifier, args, expansion)


def make_macro(identifier, args, expansion):
    """
    Return a Macro or MacroFunction based on the contents of args.
    """
    if args is None:
        return Macro(identifier, expansion)
    else:
        return MacroFunction(identifier, args, expansion)


class Macro:
    """
    Represents a macro definition.
    """

    def __init__(self, name, replacement):
        self.name = name.token
        self.replacement = replacement

        if isinstance(self.replacement, list) and len(self.replacement) > 0:
            if self.replacement[0].token == "##":
                raise RuntimeError("Found ## operator at start of replacement")
            elif self.replacement[-1].token == "##":
                raise RuntimeError("Found ## operator at end of replacement")
            self.replacement[0].prev_white = False
            self.preproc_replacement()

    def which_arg(self, tok):
        """
        Returns index token occpuies in this Macro's list. -1 if not found.
        """
        return -1

    def preproc_replacement(self):
        """
        Preprocess macroexpansion of ## where it doesn't abut arguments.
        """
        res_tokens = []
        idx = 0

        while idx < len(self.replacement):
            tok = self.replacement[idx]
            if tok.token == "##":
                last = res_tokens.pop()
                arg_idx = self.which_arg(last.token)
                if arg_idx != -1:
                    idx += 1
                    res_tokens.append(last)
                    res_tokens.append(tok)
                    self.has_strcat = True
                    continue
                idx += 1
                nexttok = self.replacement[idx]
                arg_idx = self.which_arg(nexttok.token)
                if arg_idx != -1:
                    idx += 1
                    res_tokens.append(last)
                    res_tokens.append(tok)
                    res_tokens.append(nexttok)
                    self.has_strcat = True
                    continue
                lex = Lexer(last.token + nexttok.token)
                tok = lex.tokenize_one()
                if tok is None:
                    raise ParseError(
                        f"Invalid concatenation: {lex.string}",
                    )
                tok.prev_white = last.prev_white
            elif tok.token == "#":
                if isinstance(self, MacroFunction):
                    self.has_strcat = True
            elif isinstance(tok, Identifier):
                arg_idx = self.which_arg(tok.token)
                if arg_idx != -1:
                    self.arg_needs_expansion[arg_idx] = True
            idx += 1
            res_tokens.append(tok)
        self.replacement = res_tokens

    def __repr__(self):
        return _representation_string(self)

    def spelling(self):
        """
        Return (a list containing) a string with a lexable representation of
        this Macro.
        """
        replacement_str = " ".join([str(t) for t in self.replacement])
        return [f"{self.name!s}={replacement_str!s}"]

    def replace(self):
        """
        Return the expansion list for this Macro.
        """
        return self.replacement


class MacroFunction(Macro):
    """
    Represents a macro function definition.
    """

    def __init__(self, name, args, replacement):
        self.args = [x.token for x in args]
        self.has_strcat = False
        if len(self.args) > 0:
            self.variadic = self.args[-1].endswith("...")
        else:
            self.variadic = False
        if self.variadic:
            if self.args[-1] == "...":
                # An unnamed variable argument replaces __VA_ARGS__
                self.args[-1] = "__VA_ARGS__"
            else:
                # Strip '...' from argument name
                self.args[-1] = self.args[-1][:-3]
        self.arg_needs_expansion = [False for x in self.args]
        super().__init__(name, replacement)

    def which_arg(self, tok):
        """
        Returns index token occupies in this Macro's list. -1 if not found.
        """
        try:
            return self.args.index(tok)
        except ValueError:
            return -1

    def __repr__(self):
        return _representation_string(
            self,
            attrs=["name", "args", "replacement"],
        )

    def spelling(self):
        """
        Return the string representation of this macro in the input code.
        Useful primarily for debugging and generating error messages.
        """
        replacement_str = " ".join([str(t) for t in self.replacement])
        arg_str = ",".join([str(t) for t in self.args])
        return [f"{self.name!s}({arg_str!s})={replacement_str!s}"]

    def replace(self, input_args):
        """
        Return the substituted replacement for this macro.
        input_args is expected to be a list of (original,
        pre-expanded) arguments passed to this.
        """
        # Combine variadic arguments into one, separated by commas
        if self.variadic:
            comma = Punctuator("EXPANSION", -1, False, ",")
            va_args_raw = []
            va_args_exp = []
            for idx in range(len(self.args) - 1, len(input_args) - 1):
                va_args_raw.extend(input_args[idx][0])
                va_args_raw.append(comma)
                va_args_exp.extend(input_args[idx][1])
                va_args_exp.append(comma)
            if len(self.args) - 1 < len(input_args):
                va_args_raw.extend(input_args[-1][0])
                va_args_exp.extend(input_args[-1][1])

            input_args[len(self.args) - 1 :] = [(va_args_raw, va_args_exp)]

        if self.has_strcat:
            res_tokens = []
            last_cat = False
            idx = 0

            while idx < len(self.replacement):
                tok = self.replacement[idx]
                if tok.token == "##":
                    last = res_tokens.pop()
                    prev_white = last.prev_white
                    if not last_cat:
                        try:
                            argidx = self.args.index(last.token)
                            last = input_args[argidx][0]  # Unexpanded arg
                        except ValueError:
                            last = [last]
                    else:
                        last = [last]
                    idx += 1
                    nexttok = self.replacement[idx]
                    try:
                        argidx = self.args.index(nexttok.token)
                        nexttok = input_args[argidx][0]  # Unexpanded arg
                    except ValueError:
                        nexttok = [nexttok]
                    if len(last) > 0:
                        lex = Lexer(last[-1].token + nexttok[0].token)
                        tok = lex.tokenize_one()
                        if tok is None:
                            raise ParseError(
                                f"Invalid concatenation: {lex.string}",
                            )
                        tok.prev_white = last[-1].prev_white
                        toadd = last[:-1] + [tok] + nexttok[1:]
                        if toadd[0].prev_white != prev_white:
                            cp = copy(toadd[0])
                            cp.prev_white = prev_white
                            toadd[0].prev_white = prev_white
                        res_tokens.extend(toadd)
                    else:
                        res_tokens.extend(nexttok)
                    last_cat = True
                elif tok.token == "#":
                    idx += 1
                    if idx == len(self.replacement):
                        raise ParseError(
                            "Found # at end of macro replacement!",
                        )
                    nexttok = self.replacement[idx]
                    try:
                        argidx = self.args.index(nexttok.token)
                        tok = input_args[argidx][0]  # Unexpanded arg
                    except ValueError:
                        raise ParseError(
                            "# was not followed by a macro argument.",
                        )
                    tok = Lexer.stringify(tok)
                    tok.prev_white = tok.prev_white
                    last_cat = True
                    res_tokens.append(tok)
                else:
                    last_cat = False
                    res_tokens.append(tok)
                idx += 1
        else:
            res_tokens = copy(self.replacement)

        # Substitute each occurrence of an argument in the replacement
        substituted_tokens = []
        for token in res_tokens:
            substitution = []

            # If a token matches an argument, it is substituted;
            # otherwise it passes through
            try:
                substitution = input_args[self.args.index(token.token)][1]
                if len(substitution) > 0:
                    substitution[0] = copy(substitution[0])
                    substitution[0].prev_white = token.prev_white
            except (ValueError, ParseError):
                substitution = [token]

            substituted_tokens.extend(substitution)

        return substituted_tokens


class ExpanderHelper:
    """
    Class to act as token stream for expansion stack.
    """

    def __init__(self, tokens):
        self.tokens = copy(tokens)
        self.pos = 0
        self.pre_expand = False

    def eol(self):
        """
        Returns boolean value of the read point being past end of stream.
        """

        return self.pos >= len(self.tokens)

    def splice(self, upper_helper):
        """
        Insert upper_helper ExpanderHelper into this
        stream's pos, advancing pos to end of insertion.
        """

        start = list(filter(None, self.tokens[: self.pos]))

        self.tokens = (
            start
            + list(filter(None, upper_helper.tokens))
            + list(filter(None, self.tokens[self.pos :]))
        )
        self.pos = len(start)

    def peek_tok(self):
        """
        Return at the current token without advancing.
        """

        t = self.tokens[self.pos]
        return t

    def consume_tok(self):
        """
        Consume the current token, advance, and return it.
        """

        t = self.tokens[self.pos]
        self.tokens[self.pos] = None
        self.pos += 1
        return t

    def replace_tok(self, item):
        """
        Replace the token at the current position with item. Advance.
        """

        self.tokens[self.pos] = item
        self.pos += 1


class MacroExpander:
    """
    A specialized token parser for recognizing and expanding macros.
    """

    def __init__(self, platform):
        self.platform = platform
        self.parser_stack = []
        self.no_expand = []

        # Prevent infinite recursion. CPP standard requires this be at
        # least 15, but cpp has been implemented to handle 200.
        self.max_level = 200

    def pop(self):
        """
        Pop top of parser stack off and splice tokens in it into below parser.
        If top of stack is also bottom, instead throw EndofParse.
        """
        if len(self.parser_stack) == 1 or self.parser_stack[-1].pre_expand:
            raise EndofParse("Hit end of input streams")
        top_toks = self.parser_stack[-1]
        self.parser_stack.pop()
        self.no_expand.pop()
        self.parser_stack[-1].splice(top_toks)

    def push(self, tokens, ident=None):
        """
        Push a new ExpanderHelper for tokens with new no_expand ident onto
        stack.
        """
        self.parser_stack.append(ExpanderHelper(tokens))
        self.parser_stack[-1].pre_expand = False
        self.no_expand.append(ident)
        self.overflow_check()

    def advance_tok(self):
        """
        Advance top expander's position, possibly popping to get to where that
        can be done.
        """
        while self.parser_stack[-1].eol():
            self.pop()
        self.parser_stack[-1].pos += 1

    def peek_tok_pop(self):
        """
        Peek at top expander's token, possibly popping to get to where that
        can be done.
        """
        while self.parser_stack[-1].eol():
            self.pop()
        return self.parser_stack[-1].peek_tok()

    def peek_tok(self):
        """
        Return the next logical token, or None if exhausted
        This may require us to peek 'down' in the stack.
        """
        pos = len(self.parser_stack) - 1
        while True:
            if self.parser_stack[pos].eol():
                if pos == 0 or self.parser_stack[pos].pre_expand:
                    return None
                else:
                    pos -= 1
            else:
                return self.parser_stack[pos].peek_tok()

    def consume_tok(self):
        """
        Consume top parser's current token, possibly popping to get where that
        can be done.
        """
        while self.parser_stack[-1].eol():
            self.pop()
        return self.parser_stack[-1].consume_tok()

    def replace_tok(self, tok):
        """
        Replace top parser's current token with tok, possibly popping to get
        where that can be done.
        """
        while self.parser_stack[-1].eol():
            self.pop()
        self.parser_stack[-1].replace_tok(tok)

    def overflow_check(self):
        """
        Raise MacroExpandOverflow if we exceed the allowable # of levels.
        """
        if len(self.parser_stack) >= self.max_level:
            raise MacroExpandOverflow

    def not_expandable(self, ident):
        """
        Return if this token is in the no-expansion list.
        """
        return not ident.expandable or ident.token in self.no_expand

    def defined(self, identifier):
        """
        Expand a call to defined(X) or defined X.
        """
        value = self.platform.is_defined(str(identifier))
        return NumericalConstant(
            "EXPANSION",
            identifier.line,
            identifier.prev_white,
            value,
        )

    def expand(self, tokens, ident=None, pre_expand=False):
        """
        Expand a list of input tokens using the specified definitions.
        Return a list of new tokens, representing the result of macro
        expansion.
        """
        self.overflow_check()

        if len(tokens) == 0:
            return tokens

        self.parser_stack.append(ExpanderHelper(tokens))
        self.parser_stack[-1].pre_expand = pre_expand
        self.no_expand.append(str(ident))

        try:
            while True:
                ctok = self.peek_tok_pop()

                if not isinstance(ctok, Identifier):
                    self.advance_tok()
                    continue

                _ = self.consume_tok()
                if ctok.token == "defined":
                    try:
                        tok = self.peek_tok()
                        if tok.token == "(":
                            _ = self.consume_tok()
                            ident = self.consume_tok()
                            paren = self.peek_tok()
                            if paren.token != ")":
                                raise ParseError(
                                    "Expected ')' after 'defined' identifier",
                                )
                        else:
                            ident = tok
                        if not isinstance(ident, Identifier):
                            raise ParseError(
                                "Expected identifier after 'defined'",
                            )
                        self.replace_tok(self.defined(ident))
                    except IndexError:
                        raise ParseError(
                            "Expected identifier after 'defined'",
                        )
                    continue

                if self.not_expandable(ctok):
                    itok = copy(ctok)
                    itok.expandable = False
                    self.parser_stack[-1].pos -= 1
                    self.replace_tok(itok)
                    continue

                macro_lookup = self.platform.get_macro(ctok.token)
                if not macro_lookup:
                    self.parser_stack[-1].pos -= 1
                    self.replace_tok(ctok)
                    continue

                if isinstance(macro_lookup, MacroFunction):
                    paren = self.peek_tok()
                    if not paren or paren.token != "(":
                        self.parser_stack[-1].pos -= 1
                        self.replace_tok(ctok)
                        continue
                    else:
                        _ = self.consume_tok()
                    args = []
                    current_arg = []
                    open_paren_count = 1

                    while True:
                        tok = self.consume_tok()
                        if tok.token == "," and open_paren_count == 1:
                            args.append(current_arg)
                            current_arg = []
                            continue

                        if tok.token == "(":
                            open_paren_count += 1
                        elif tok.token == ")":
                            open_paren_count -= 1
                            if open_paren_count == 0:
                                args.append(current_arg)
                                break

                        current_arg.append(tok)

                    pre_expanded = []
                    for i, arg in enumerate(args):
                        if (
                            i >= len(macro_lookup.arg_needs_expansion)
                            or macro_lookup.arg_needs_expansion[i]
                        ):
                            arg_expansion = self.expand(
                                arg,
                                ident=None,
                                pre_expand=True,
                            )
                            pre_expanded.append((arg, arg_expansion))
                        else:
                            pre_expanded.append((arg,))
                    # Proper expand
                    replacement = macro_lookup.replace(pre_expanded)
                    if isinstance(replacement, list) and len(replacement) > 0:
                        replacement[0] = copy(replacement[0])
                        replacement[0].prev_white = ctok.prev_white
                    self.push(replacement, macro_lookup.name)
                elif isinstance(macro_lookup, Macro):
                    replacement = macro_lookup.replace()
                    if isinstance(replacement, list) and len(replacement) > 0:
                        replacement[0] = copy(replacement[0])
                        replacement[0].prev_white = ctok.prev_white
                    self.push(replacement, macro_lookup.name)
                else:
                    raise ParseError("Unexpected error in macro expansion")
        except EndofParse:
            res_tokens = list(filter(None, self.parser_stack[-1].tokens))
            self.parser_stack.pop()
            self.no_expand.pop()
            return res_tokens
        except MacroExpandOverflow:
            self.__init__(self.platform)
            return [NumericalConstant("EXPANSION", -1, False, "0")]


class ExpressionEvaluator(Parser):
    """
    A specialized token parser for recognizing/evaluating expressions.
    """

    # Operator precedence, associativity and Python equivalent
    # Lower numbers = higher precedence
    # Based on:
    # https://en.cppreference.com/w/cpp/language/operator_precedence
    OpInfo = collections.namedtuple("OpInfo", ["prec", "assoc"])
    UnaryOperators = {
        "-": OpInfo(12, "RIGHT"),
        "+": OpInfo(12, "RIGHT"),
        "!": OpInfo(12, "RIGHT"),
        "~": OpInfo(12, "RIGHT"),
    }
    BinaryOperators = {
        "?": OpInfo(1, "RIGHT"),
        "||": OpInfo(2, "LEFT"),
        "&&": OpInfo(3, "LEFT"),
        "|": OpInfo(4, "LEFT"),
        "^": OpInfo(5, "LEFT"),
        "&": OpInfo(6, "LEFT"),
        "==": OpInfo(7, "LEFT"),
        "!=": OpInfo(7, "LEFT"),
        "<": OpInfo(8, "LEFT"),
        "<=": OpInfo(8, "LEFT"),
        ">": OpInfo(8, "LEFT"),
        ">=": OpInfo(8, "LEFT"),
        "<<": OpInfo(9, "LEFT"),
        ">>": OpInfo(9, "LEFT"),
        "+": OpInfo(10, "LEFT"),
        "-": OpInfo(10, "LEFT"),
        "*": OpInfo(11, "LEFT"),
        "/": OpInfo(11, "LEFT"),
        "%": OpInfo(11, "LEFT"),
    }

    def call(self):
        """
        Match a built-in call or function-like macro and return 0.

        <call> := <identifier>'('<expression-list>?')'
        """
        initial_pos = self.pos
        try:
            self.match_type(Identifier)

            # Read a list of arguments
            self.match_value(Punctuator, "(")
            self.__expression_list()
            self.match_value(Punctuator, ")")

            # Any function call that still exists after substitution
            # evaluates to false
            return np.int64(0)
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid function call.")

    def term(self):
        """
        Match a constant, function call or identifier and convert it to
        Python syntax.

        <term> := [<integer-constant>|<character-constant>|<call>|
                   <identifier>]
        """
        initial_pos = self.pos

        # Match an integer constant.
        # Convert from C-style literals to Python integers.
        try:
            constant = self.match_type(NumericalConstant)

            # Use prefix (if present) to determine base
            base = 10
            bases = {"0x": 16, "0X": 16, "0b": 2, "0B": 2}
            try:
                prefix = constant.token[0:2]
                base = bases[prefix]
                value = constant.token[2:]
            except KeyError:
                value = constant.token

            # Strip suffix (if present)
            suffix = None
            suffixes = [
                "ull",
                "ULL",
                "ul",
                "UL",
                "ll",
                "LL",
                "u",
                "U",
                "l",
                "L",
            ]
            for s in suffixes:
                if value.endswith(s):
                    suffix = s
                    value = value[: -len(s)]
                    break

            # Convert to decimal and then to integer with correct sign
            # Preprocessor always uses 64-bit arithmetic!
            int_value = int(value, base)
            if suffix and "u" in suffix.lower():
                return np.uint64(int_value)
            else:
                return np.int64(int_value)
        except ParseError:
            self.pos = initial_pos

        # Match a character constant.
        # Convert from character literals to integer value.
        try:
            constant = self.match_type(CharacterConstant)
            return np.int64(ord(constant.token))
        except ParseError:
            self.pos = initial_pos

        # Match a function call.
        try:
            return self.call()
        except ParseError:
            self.pos = initial_pos

        # Match an identifier.
        # Any identifier that still exists after substitution evaluates
        # to false
        try:
            self.match_type(Identifier)
            return np.int64(0)
        except ParseError:
            self.pos = initial_pos

        raise ParseError(
            "Expected integer constant, character constant, identifier or "
            + "function call.",
        )

    def primary(self):
        """
        Match a simple expression
        <primary> := [<unary-op><expression>|'('<expression>')'|<term>]
        """
        initial_pos = self.pos

        # Match <unary-op><expression>
        try:
            operator = self.match_type(Operator)
            if operator.token in ExpressionEvaluator.UnaryOperators:
                (prec, assoc) = ExpressionEvaluator.UnaryOperators[
                    operator.token
                ]
            else:
                raise ParseError("Not a UnaryOperator")
            expr = self.expression(prec)
            return self.__apply_unary_op(operator.token, expr)
        except ParseError:
            self.pos = initial_pos

        # Match '('<expression>')'
        try:
            self.match_value(Punctuator, "(")
            expr = self.expression()
            self.match_value(Punctuator, ")")
            return expr
        except ParseError:
            self.pos = initial_pos

        # Match <term>
        try:
            term = self.term()
            return term
        except ParseError:
            self.pos = initial_pos

        raise ParseError(
            "Expected unary expression, expression in parens, or "
            + "identifier/constant.",
        )

    def expression(self, min_precedence=0):
        """
        Match a preprocessor expression.
        Minimum precedence used to match operators during precedence
        climbing.

        <expression> := <primary>[<binary-op><expression>]?
        """
        expr = self.primary()

        # Recursion is terminated based on operator precedence
        while (
            not self.eol()
            and (self.cursor().token in ExpressionEvaluator.BinaryOperators)
            and (
                ExpressionEvaluator.BinaryOperators[self.cursor().token].prec
                >= min_precedence
            )
        ):
            operator = self.match_type(Operator)
            (prec, assoc) = ExpressionEvaluator.BinaryOperators[operator.token]

            # The ternary conditional operator is treated as a
            # special-case of a binary operator:
            # lhs "?"<expression>":" rhs
            if operator.token == "?":
                true_result = self.expression()
                self.match_value(Operator, ":")

            # Minimum precedence for right-hand side depends on
            # associativity
            if assoc == "LEFT":
                rhs = self.expression(prec + 1)
            elif assoc == "RIGHT":
                rhs = self.expression(prec)
            else:
                raise ValueError(
                    "Encountered a BinaryOperator with no associativity.",
                )

            # Converting C ternary to Python requires us to swap
            # expression order:
            # - C:      (condition) ? true_result : false_result
            # - Python: true_result if (condition) else false_result
            if operator.token == "?":
                condition = expr
                false_result = rhs
                expr = true_result if condition else false_result
            else:
                expr = self.__apply_binary_op(operator.token, expr, rhs)

        return expr

    def __expression_list(self):
        """
        Match a comma-separated list of expressions.
        Return an empty list or the expressions.

        <expression-list> := [<expression>][','<expression-list>]*
        """
        exprs = []
        try:
            expr = self.expression()
            exprs.append(expr)

            while True:
                self.match_value(Punctuator, ",")
                expr = self.expression()
                exprs.append(expr)
        except ParseError:
            return exprs

    @staticmethod
    def __apply_unary_op(op, operand):
        """
        Apply the specified unary operator: op operand
        """
        if op == "-":
            return -operand
        elif op == "+":
            return +operand
        elif op == "!":
            return not operand
        elif op == "~":
            return ~operand
        else:
            raise ValueError("Not a valid unary operator.")

    @staticmethod
    def __apply_binary_op(op, lhs, rhs):
        """
        Apply the specified binary operator: lhs op rhs
        """
        if op == "||":
            return lhs or rhs
        elif op == "&&":
            return lhs and rhs
        elif op == "|":
            return lhs | rhs
        elif op == "^":
            return lhs ^ rhs
        elif op == "&":
            return lhs & rhs
        elif op == "==":
            return lhs == rhs
        elif op == "!=":
            return lhs != rhs
        elif op == "<":
            return lhs < rhs
        elif op == "<=":
            return lhs <= rhs
        elif op == ">":
            return lhs > rhs
        elif op == ">=":
            return lhs >= rhs
        elif op == "<<":
            return lhs << rhs
        elif op == ">>":
            return lhs >> rhs
        elif op == "+":
            return lhs + rhs
        elif op == "-":
            return lhs - rhs
        elif op == "*":
            return lhs * rhs
        elif op == "/":
            return lhs // rhs  # force integer division
        elif op == "%":
            return lhs % rhs
        else:
            raise ValueError("Not a binary operator.")

    def evaluate(self):
        """
        Evaluate a preprocessor expression.
        Return True/False or raises an exception if the expression is
        not recognized.
        """
        try:
            test_val = self.expression()
            return test_val != 0
        except ValueError:
            raise ParseError("Could not evaluate expression.")


class SourceTree:
    """
    Represents a source file as a tree of directive and code nodes.
    """

    def __init__(self, filename):
        self.root = FileNode(filename)
        self._latest_node = self.root

    def walk(self) -> Iterable[Node]:
        """
        Returns
        -------
        Iterable[Node]
            An Iterable visiting all nodes in the tree via a preorder
            traversal.
        """
        yield from self.root.walk()

    def visit(self, visitor: Callable[[Node], Visit]):
        """
        Visit each node in the tree via a preorder traversal, using the
        supplied visitor.

        Raises
        ------
        TypeError
            If `visitor` is not callable.
        """
        self.root.visit(visitor)

    def associate_file(self, filename):
        self.root.filename = filename

    def walk_to_tree_insertion_point(self):
        """
        This function modifies self._latest_node to be a node that can
        be a valid sibling of a tree continue node or a tree end node.
        These nodes can only be inserted after an open tree start node,
        or a tree continue node.
        """

        while not (
            self._latest_node.is_start_node()
            or self._latest_node.is_cont_node()
        ):
            self._latest_node = self._latest_node.parent
            if self._latest_node == self.root:
                log.error(
                    "Found root while trying to find an insertion point.",
                )
                break

    def __insert_in_place(self, new_node, parent):
        parent.add_child(new_node)
        self._latest_node = new_node

    def insert(self, new_node):
        """
        Handle the logic of proper node insertion.
        """

        # If there haven't been any nodes added, add this new node as a
        # child of the root node.
        if self._latest_node == self.root:
            self.__insert_in_place(new_node, self._latest_node)
        # Tree start nodes should be inserted as siblings of the
        # previous node, unless it was a tree start, or tree continue
        # node. In which case it's a child.
        elif new_node.is_start_node():
            if (
                self._latest_node.is_start_node()
                or self._latest_node.is_cont_node()
            ):
                self.__insert_in_place(new_node, self._latest_node)
            else:
                self.__insert_in_place(new_node, self._latest_node.parent)

        # If the node is a tree continue or a tree end node, it must be
        # added as a sibling of a valid / active tree node.
        elif new_node.is_cont_node() or new_node.is_end_node():
            # Need to walk back to find the previous level where an else
            # or an end can be added
            self.walk_to_tree_insertion_point()

            self.__insert_in_place(new_node, self._latest_node.parent)

        # Otherwise, if the previous node was a tree start or a tree
        # continue, the new node is a child. If not, it's a sibling.
        else:
            if (
                self._latest_node.is_start_node()
                or self._latest_node.is_cont_node()
            ):
                self.__insert_in_place(new_node, self._latest_node)
            else:
                self.__insert_in_place(new_node, self._latest_node.parent)
