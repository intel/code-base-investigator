# Copyright (C) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
# pylint: disable=too-many-lines
"""
Contains classes that define:
- Nodes from the tree
- Tokens from lexing a line of code
- Operators to handle tokens
"""

import logging
import collections
import hashlib
import numpy as np
from . import util
from . import walkers

log = logging.getLogger('codebasin')


class TokenError(ValueError):
    """
    Represents an error encountered during tokenization.
    """


class Token():
    """
    Represents a token constructed by the parser.
    """

    def __init__(self, line, col, prev_white, token):
        self.line = line
        self.col = col
        self.prev_white = prev_white
        self.token = token

    def __repr__(self):
        return "Token(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)

    def __str__(self):
        return str(self.token)


class CharacterConstant(Token):
    """
    Represents a character constant.
    """

    def __repr__(self):
        return "CharacterConstant(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)


class NumericalConstant(Token):
    """
    Represents a 'preprocessing number'.
    These cannot necessarily be evaluated by the preprocessor (and may
    not be valid syntax).
    """

    def __repr__(self):
        return "NumericalConstant(line={!r},col={!r},prev_white={!r},value={!r})".format(
            self.line, self.col, self.prev_white, self.token)


class StringConstant(Token):
    """
    Represents a string constant.
    """

    def __repr__(self):
        return "StringConstant(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)

    def __str__(self):
        return "\"{!s}\"".format(self.token)


class Identifier(Token):
    """
    Represents a C identifier.
    """

    def as_str(self):
        return str(self.token)

    def __repr__(self):
        return "Identifier(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)


class Operator(Token):
    """
    Represents a C operator.
    """

    def __repr__(self):
        return "Operator(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)

    def __str__(self):
        return str(self.token)


class Punctuator(Token):
    """
    Represents a punctuator (e.g. parentheses)
    """

    def __repr__(self):
        return "Punctuator(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)


class Unknown(Token):
    """
    Represents an unknown token.
    """

    def __repr__(self):
        return "Unknown(line={!r},col={!r},prev_white={!r},token={!r})".format(
            self.line, self.col, self.prev_white, self.token)


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
        return self.string[self.pos:self.pos + n]

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
            raise TokenError("Expected {}.".format(literal))

    def match_any(self, literals):
        """
        Match one from a list of character/string literals exactly.
        Return the matched index and advance position.
        """
        for (index, literal) in enumerate(literals):
            if self.read(len(literal)) == literal:
                self.pos += len(literal)
                return index

        raise TokenError("Expected one of: {}.".format(", ".join(literals)))

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
                elif self.read().isalpha() or self.read().isdigit() or self.read() in ["_", "."]:
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
            self.match('\'')

            # A character constant may be an escaped sequence
            # We assume a single alpha-numerical character or space
            if self.read() == '\\' and self.read(2).isprintable():
                value = self.read(2)
                self.pos += 2
            elif self.read().isprintable():
                value = self.read()
                self.pos += 1
            else:
                raise TokenError("Expected character.")

            self.match('\'')
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
            self.match('\"')

            chars = []
            while not self.eos() and self.read() != '\"':

                # An escaped " should not close the string
                if self.read(2) == "\\\"":
                    chars.append(self.read(2))
                    self.pos += 2
                else:
                    chars.append(self.read())
                    self.pos += 1

            self.match('\"')
        except TokenError:
            self.pos = col
            raise TokenError("Invalid string constant.")

        constant = StringConstant(self.line, col, self.prev_white, "".join(chars))
        return constant

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

        identifier = Identifier(self.line, col, self.prev_white, "".join(characters))
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
        operators = ["||", "&&", ">>", "<<", "!=", ">=", "<=", "==", "##"] + \
            ["-", "+", "!", "*", "/", "|", "&", "^", "<", ">", "?", ":", "~", "#", "=", "%"]
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
        punctuators = ["(", ")", "{", "}", "[", "]", ",", ".", ";", "'", "\"", "\\"]
        try:
            index = self.match_any(punctuators)

            punc = Punctuator(self.line, col, self.prev_white, punctuators[index])
            return punc
        except TokenError:
            self.pos = col
            raise TokenError("Invalid punctuator.")

    def tokenize_one(self):
        """
        Consume and return next token. Returns None if not possible.
        """
        candidates = [self.number, self.character_constant, self.string_constant,
                      self.identifier, self.operator, self.punctuator]
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
                token = Unknown(self.line, self.pos, self.prev_white, self.read())
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


class Node():
    """
    Base class for all other Node types.
    Contains a single parent, and an ordered list of children.
    """

    def __init__(self):
        self.children = []
        self.parent = None

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

    # pylint: disable=no-self-use,unused-argument
    def evaluate_for_platform(self, **kwargs):
        """
        Determine if the children of this node are active, by evaluating
        the statement.
        Return False by default.
        """
        return False


class FileNode(Node):
    """
    Typically the root node of a tree. Simply contains a filename after
    inheriting from the Node class.
    """

    def __init__(self, _filename):
        super().__init__()
        self.filename = _filename
        # The length of the file, counting blank lines and comments
        self.num_lines = 0
        # The source lines of code, ignoring blank lines and comments
        self.total_sloc = 0
        self.file_hash = self.__compute_file_hash()

    def __compute_file_hash(self):
        chunk_size = 4096
        hasher = hashlib.sha512()
        with util.safe_open_read_nofollow(self.filename, 'rb') as in_file:
            for chunk in iter(lambda: in_file.read(chunk_size), b""):
                hasher.update(chunk)

        return hasher.hexdigest()

    def __repr__(self):
        return "FileNode(filename={0!r})".format(self.filename)

    def __str__(self):
        return "{}; Hash: {}".format(str(self.filename), str(self.file_hash))

    def evaluate_for_platform(self, **kwargs):
        """
        Since a FileNode is always used as a root node, we are only
        interested in its children.
        """
        return True


class CodeNode(Node):
    """
    Represents any line of code. Contains a start and end line, and the
    number of countable lines occurring between them.
    """

    def __init__(self, start_line=-1, end_line=-1, num_lines=0):
        super().__init__()
        self.start_line = start_line
        self.end_line = end_line
        self.num_lines = num_lines

    def __repr__(self):
        return "CodeNode(start={0!r},end={1!r},lines={2!r}".format(
            self.start_line, self.end_line, self.num_lines)

    def __str__(self):
        return "Lines {}-{}; SLOC = {};".format(self.start_line, self.end_line, self.num_lines)


class DirectiveNode(CodeNode):
    """
    A CodeNode representing a C preprocessor directive.
    We need to track all of the tokens for this directive in addition to
    countable lines and extent.
    """

    def __init__(self):
        super().__init__()


class UnrecognizedDirectiveNode(DirectiveNode):
    """
    A CodeNode representing an unrecognized preprocessor directive
    """

    def __init__(self, tokens):
        super().__init__()
        self.kind = "unrecognized"
        self.tokens = tokens

    def __repr__(self):
        return "DirectiveNode(kind={!r},tokens={!r})".format(self.kind, self.tokens)

    def __str__(self):
        return "{}".format(" ".join([str(t) for t in self.tokens]))


class PragmaNode(DirectiveNode):
    """
    Represents a #pragma directive
    """

    def __init__(self, tokens):
        super().__init__()
        self.kind = "pragma"
        self.tokens = tokens

    def __repr__(self):
        return "DirectiveNode(kind={0!r},tokens={1!r})".format(self.kind, self.tokens)

    def __str__(self):
        return "#pragma {0!s}".format(" ".join([str(t) for t in self.tokens]))

    def evaluate_for_platform(self, **kwargs):
        if self.tokens and str(self.tokens[0]) == 'once':
            kwargs['platform'].add_include_to_skip(kwargs['filename'])


class DefineNode(DirectiveNode):
    """
    A DirectiveNode representing a #define directive.
    """

    def __init__(self, identifier, args=None, value=None):
        super().__init__()
        self.kind = "define"
        self.identifier = identifier
        self.args = args
        self.value = value

    def __repr__(self):
        return "DirectiveNode(kind={0!r},identifier={1!r},args={2!r},value={3!r})".format(
            self.kind, self.identifier, self.args, self.value)

    def __str__(self):
        value_str = "".join([str(v) for v in self.value])

        if self.args is None:
            return "#define {0!s} {1!s}".format(self.identifier, value_str)
        elif self.args == []:
            return "#define {0!s}() {1!s}".format(self.identifier, value_str)
        else:
            arg_str = ", ".join([str(arg) for arg in self.args])
            return "#define {0!s}({1!s}) {2!s}".format(self.identifier, arg_str, value_str)

    def evaluate_for_platform(self, **kwargs):
        """
        Add a definition into the platform, and return false
        """
        macro = Macro(self.identifier, self.args, self.value)
        kwargs['platform'].define(self.identifier.as_str(), macro)
        return False


class UndefNode(DirectiveNode):
    """
    A DirectiveNode representing an #undef directive.
    """

    def __init__(self, identifier):
        super().__init__()
        self.kind = "undefine"
        self.identifier = identifier

    def __repr__(self):
        return "DirectiveNode(kind={0!r},identifier={1!r})".format(self.kind, self.identifier)

    def __str__(self):
        return "#undef {0!s}".format(self.identifier)

    def evaluate_for_platform(self, **kwargs):
        """
        Add a definition into the platform, and return false
        """
        kwargs['platform'].undefine(self.identifier.as_str())
        return False


class IncludePath():
    """
    Represents an include path enclosed by "" or <>
    """

    def __init__(self, path, system):
        self.path = path
        self.system = system

    def __repr__(self):
        return "IncludePath(path={!r},system={!r})".format(self.path, self.system)

    def __str__(self):
        if self.system:
            return "<{0!s}>".format(self.path)
        return "\"{0!s}\"".format(self.path)

    def is_system_path(self):
        return self.system


class IncludeNode(DirectiveNode):
    """
    A DirectiveNode representing an #include directive.
    Its value is an IncludePath or a list of tokens.
    """

    def __init__(self, value):
        super().__init__()
        self.kind = "include"
        self.value = value

    def __repr__(self):
        return "DirectiveNode(kind={0!r},value={1!r})".format(self.kind, self.value)

    def __str__(self):
        return "#include {0!s}".format(self.value)

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
            expansion = MacroExpander(self.value, kwargs['platform']).expand()
            path_obj = DirectiveParser(expansion).include_path()
            include_path = path_obj.path
            is_system_include = path_obj.system

        include_file = kwargs['platform'].find_include_file(include_path, is_system_include)

        if include_file and kwargs['platform'].process_include(include_file):
            kwargs['state'].insert_file(include_file)

            associator = walkers.TreeAssociator(kwargs['state'].get_tree(
                include_file), kwargs['state'].get_map(include_file))
            associator.walk(kwargs['platform'], kwargs['state'])


class IfNode(DirectiveNode):
    """
    Represents an #if, #ifdef or #ifndef directive.
    """

    def __init__(self, tokens):
        super().__init__()
        self.kind = "if"
        self.tokens = tokens

    @staticmethod
    def is_start_node():
        return True

    def __repr__(self):
        return "DirectiveNode(kind={0!r},tokens={1!r})".format(self.kind, self.tokens)

    def __str__(self):
        return "#if {0!s}".format(" ".join([str(t) for t in self.tokens]))

    def evaluate_for_platform(self, **kwargs):
        # Perform macro substitution with tokens
        expanded_tokens = MacroExpander(self.tokens, kwargs['platform']).expand()

        # Evaluate the expanded tokens
        return ExpressionEvaluator(expanded_tokens).evaluate()


class ElIfNode(IfNode):
    """
    Represents an #elif directive.
    """

    def __init__(self, tokens):
        super().__init__(tokens)
        self.kind = "elif"

    @staticmethod
    def is_start_node():
        return False

    @staticmethod
    def is_cont_node():
        return True


class ElseNode(DirectiveNode):
    """
    Represents an #else directive.
    """

    def __init__(self):
        super().__init__()
        self.kind = "else"

    @staticmethod
    def is_cont_node():
        return True

    def __repr__(self):
        return "DirectiveNode(kind={0!r})".format(self.kind)

    def __str__(self):
        return "#else"

    def evaluate_for_platform(self, **kwargs):
        return True


class EndIfNode(DirectiveNode):
    """
    Represents an #endif directive.
    """

    def __init__(self):
        super().__init__()
        self.kind = "endif"

    @staticmethod
    def is_end_node():
        return True

    def __repr__(self):
        return "DirectiveNode(kind={0!r})".format(self.kind)

    def __str__(self):
        return "#endif"


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
            raise ParseError("Expected {!s}.".format(token_type))
        return token

    def match_value(self, token_type, token_value):
        """
        Match a token of the specified type and value, and advance
        position.
        """
        if isinstance(self.cursor(), token_type) and self.cursor().token == token_value:
            token = self.cursor()
            self.pos += 1
        else:
            raise ParseError("Expected {!s}.".format(token_value))
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
                if arg.token.endswith("..."):
                    return args

                args.append(arg)
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
                expansion = self.tokens[self.pos:]
                self.pos = len(self.tokens)
            else:
                expansion = []

            return DefineNode(identifier, args, expansion)
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
            return UndefNode(identifier)
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
                path = self.include_path()
                return IncludeNode(path)
            except ParseError:
                self.pos = path_pos

            # Match computed include with a simple macro
            try:
                identifier = self.match_type(Identifier)
                return IncludeNode([identifier])
            except ParseError:
                self.pos = path_pos

            raise ParseError("Invalid include directive.")
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Invalid include directive.")

    def __path(self, marker_type=Punctuator, initiator_value='\"', terminator_value='\"'):
        """
        Match a path enclosed between the specified initiator and
        terminator values.
        """
        path = []
        self.match_value(marker_type, initiator_value)
        while not self.eol() and not (isinstance(self.cursor(), marker_type)
                                      and self.cursor().token == terminator_value):
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
            expr = self.tokens[self.pos:]
            self.pos = len(self.tokens)

            return PragmaNode(expr)
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
            expr = self.tokens[self.pos:]
            self.pos = len(self.tokens)

            return IfNode(expr)
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
            prefix = [Identifier("Unknown", -1, True, "defined"),
                      Punctuator("Unknown", -1, False, "(")]
            suffix = [Punctuator("Unknown", -1, False, ")")]
            expr = prefix + [identifier] + suffix

            return IfNode(expr)
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
            prefix = [Operator("Unknown", -1, True, "!"), Identifier("Unknown", -1,
                                                                     False, "defined"),
                      Punctuator("Unknown",
                                 -1, False, "(")]
            suffix = [Punctuator("Unknown", -1, False, ")")]
            expr = prefix + [identifier] + suffix

            return IfNode(expr)
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
            expr = self.tokens[self.pos:]
            self.pos = len(self.tokens)

            return ElIfNode(expr)
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
            return ElseNode()
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
            return EndIfNode()
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
            candidates = [self.define, self.undef, self.include, self.ifdef,
                          self.ifndef, self.if_, self.elif_, self.else_, self.endif, self.pragma]
            for f in candidates:
                try:
                    directive = f()
                    if not self.eol():
                        log.warning("Additional tokens at end of preprocessor directive")
                    return directive
                except ParseError:
                    pass

            # Any other line beginning with '#' is a preprocessor
            # directive, we just don't handle it (yet). Suppress
            # warnings for common directives that shouldn't impact
            # correctness.
            common_unhandled = ["line", "warning", "error"]
            if len(self.tokens) > 2 and str(self.tokens[1]) not in common_unhandled:
                log.warning("Unrecognized directive")
            return UnrecognizedDirectiveNode(self.tokens)
        except ParseError:
            raise ParseError("Not a directive.")


class Macro():
    """
    Represents a macro definition.
    """

    def __init__(self, name, args=None, expansion=None):
        self.name = str(name)
        if args is not None:
            self.args = [str(a) for a in args]
        else:
            self.args = None
        self.expansion = expansion

    def __repr__(self):
        return "Macro(name={0!r},args={1!r},expansion={2!r})".format(
            self.name, self.args, self.expansion)

    def __str__(self):
        expansion_str = " ".join([str(t) for t in self.expansion])
        if self.args is None:
            return "{0!s}={1!s}".format(self.name, expansion_str)
        arg_str = ",".join(self.args)
        return "{0!s}({1!s})={2!s}".format(self.name, arg_str, expansion_str)

    def is_function(self):
        """
        Return true if macro is function-like
        """
        return self.args is not None

    def is_variadic(self):
        """
        Return true if macro is variadic
        """
        if self.is_function() and self.args:
            return self.args[-1].endswith("...")
        return False

    def variable_argument(self):
        """
        Return the name of the variable argument for a variadic macro.
        If the macro is not variadic, return None.
        """
        if self.is_variadic():
            if self.args[-1] == '...':
                # An unnamed variable argument replaces __VA_ARGS__
                return "__VA_ARGS__"
            else:
                # Strip '...' from argument name
                return self.args[-1][:-3]
        else:
            return None

    @staticmethod
    def from_definition_string(string):
        """
        Construct a Macro by parsing a string of the form
        MACRO=expansion.
        """
        tokens = Lexer(string).tokenize()
        parser = DirectiveParser(tokens)

        (identifier, args) = parser.macro_definition()

        # Any remaining tokens after an "=" are the macro expansion
        if not parser.eol():
            parser.match_value(Operator, "=")
            expansion = parser.tokens[parser.pos:]
            parser.pos = len(parser.tokens)
        else:
            expansion = NumericalConstant("Unknown", None, False, 1)

        return Macro(identifier, args, expansion)


class MacroStack:
    """
    Tracks previously expanded macros during recursive expansion.
    """

    def __init__(self, level, no_expand):
        self.level = level
        self.no_expand = no_expand

        # Prevent infinite recursion. CPP standard requires this be at
        # least 15, but cpp has been implemented to handle 200.
        self.max_level = 200

    def __contains__(self, identifier):
        return str(identifier) in self.no_expand

    def push(self, identifier):
        self.level += 1
        self.no_expand.append(str(identifier))

    def pop(self):
        self.level -= 1
        self.no_expand.pop()

    def overflow(self):
        return self.level >= self.max_level


class MacroExpander(Parser):
    """
    A specialized token parser for recognizing and expanding macros.
    """

    def __init__(self, tokens, platform, stack=None):
        super().__init__(tokens)
        self.platform = platform
        if stack is None:
            self.stack = MacroStack(0, [])
        else:
            self.stack = stack

    # pylint: disable=unused-argument
    def defined(self):
        """
        Expand a call to defined(X) or defined X.
        """
        initial_pos = self.pos
        try:
            self.match_value(Identifier, "defined")

            # Match an identifier in parens
            defined_pos = self.pos
            try:
                self.match_value(Punctuator, "(")
                identifier = self.match_type(Identifier)
                self.match_value(Punctuator, ")")

                value = self.platform.is_defined(str(identifier))
                return [NumericalConstant("EXPANSION", identifier.line,
                                          identifier.prev_white, value)]
            except ParseError:
                self.pos = defined_pos

            # Match an identifier without parens
            try:
                identifier = self.match_type(Identifier)
                value = self.platform.is_defined(str(identifier))
                return [NumericalConstant("EXPANSION", identifier.line,
                                          identifier.prev_white, value)]
            except ParseError:
                raise ParseError("Expected identifier after \"defined\" operator")

        except ParseError:
            self.pos = initial_pos
            raise ParseError("Not a defined operator.")

    def __arg(self):
        """
        Match an argument to a function-like macro, where:
        - An argument is a (potentially empty) list of tokens
        - Arguments are separated by a ","
        - "(" must be matched with a ")" within an argument
        """
        arg = []
        open_parens = 0
        while not self.eol():
            t = self.cursor()
            if isinstance(t, Punctuator):
                if t.token == "(":
                    open_parens += 1
                elif t.token == ")" and open_parens > 0:
                    open_parens -= 1
                elif (t.token == "," or t.token == ")") and open_parens == 0:
                    return arg
            arg.append(t)
            self.pos += 1

        if open_parens > 0:
            raise ParseError("Mismatched parentheses in macro argument.")
        raise ParseError("Invalid macro argument.")

    def __arg_list(self):
        """
        Match a list of function-like macro arguments.
        """
        arg = self.__arg()
        args = [arg]
        try:
            while not self.eol():
                self.match_value(Punctuator, ",")
                arg = self.__arg()
                args.append(arg)
        except ParseError:
            pass
        return args

    def subexpand(self, tokens, ident=None):
        if ident is not None:
            self.stack.push(ident)
        expansion = MacroExpander(tokens, self.platform, self.stack).expand()
        if ident is not None:
            self.stack.pop()

        return expansion

    def function_macro(self):
        """
        Expand a function-like macro, returning a list of tokens.

        Follows the rules outlined in:
        https://gcc.gnu.org/onlinedocs/cpp/Macro-Arguments.html#Macro-Arguments
        """
        initial_pos = self.pos
        try:
            identifier = self.match_type(Identifier)
            if identifier in self.stack:
                raise ParseError('Cannot expand token')

            self.match_value(Punctuator, "(")
            args = self.__arg_list()
            self.match_value(Punctuator, ")")
        except ParseError:
            self.pos = initial_pos
            raise ParseError("Not a function-like macro.")

        macro = self.platform.get_macro(str(identifier))
        if not macro:
            raise ParseError("Not a function-like macro.")

        # Argument pre-scan
        # Macro arguments are macro-expanded before substitution
        expanded_args = [self.subexpand(arg) for arg in args]

        # Combine variadic arguments into one, separated by commas
        va_args = None
        if macro.is_variadic():
            va_args = []
            for idx in range(len(macro.args) - 1, len(expanded_args) - 1):
                va_args.append(expanded_args[idx])
                va_args.append([Punctuator("EXPANSION", -1, False, ",")])
            if len(macro.args) - 1 < len(expanded_args):
                va_args.append(expanded_args[-1])

        # Substitute each occurrence of an argument in the expansion
        substituted_tokens = []
        for token in macro.expansion:

            substitution = []

            # If a token matches an argument, it is substituted;
            # otherwise it passes through
            try:
                substitution = expanded_args[macro.args.index(token.token)]
            except (ValueError, ParseError):
                substitution = [token]

            # If a token matches the variable argument, substitute
            # precomputed va_args
            if macro.is_variadic() and token.token == macro.variable_argument() and va_args:

                # Whether the token was preceded by whitespace should be
                # tracked through substitution
                for t in va_args[0]:
                    t.prev_white = token.prev_white
                substitution = [item for lst in va_args for item in lst]

            substituted_tokens.extend(substitution)

        # Check the expansion for macros to expand
        return self.subexpand(substituted_tokens, identifier)

    def macro(self):
        """
        Expand a macro.
        """
        initial_pos = self.pos
        try:
            identifier = self.match_type(Identifier)
            if identifier in self.stack:
                raise ParseError('Cannot expand this token')

            macro = self.platform.get_macro(str(identifier))
            if not macro:
                raise TokenError('Not a macro.')

            return self.subexpand(macro.expansion, identifier)
        except TokenError:
            self.pos = initial_pos
            raise ParseError("Not a macro.")

    def expand(self):
        """
        Expand a list of input tokens using the specified definitions.
        Return a list of new tokens, representing the result of macro
        expansion.
        """

        if self.stack.overflow():
            return [NumericalConstant("EXPANSION", -1, False, "0")]

        self.tokens = self.expand_cat()
        self.pos = 0

        try:
            expanded_tokens = []
            while not self.eol():
                # Match and expand special tokens
                expansion = None
                test_pos = self.pos

                candidates = [self.defined, self.function_macro, self.macro]
                for f in candidates:
                    try:
                        expansion = f()
                        break
                    except ParseError:
                        self.pos = test_pos

                # Pass all other tokens through unmodified
                if expansion is None:
                    expansion = [self.cursor()]
                    self.pos += 1

                expanded_tokens.extend(expansion)
            return expanded_tokens
        except ParseError:
            raise ValueError("Error in macro expansion.")

    def expand_cat(self):
        """Traverses tokens and applies concatenation operator.
        Modifies self.pos. Returns new list of tokens."""
        output_tokens = []
        current_cat = []

        assert self.pos == 0

        last_tok = None
        while not self.eol():
            tok = self.cursor()
            self.pos += 1
            if tok.token == "##":
                if last_tok is None:
                    raise TokenError("Got cat token (##) as first token!")
                if last_tok.token == "##":
                    raise TokenError("Got successive cat tokens (##)")
                current_cat.append(last_tok)
                last_tok = tok
            else:
                if last_tok is None:
                    last_tok = tok
                elif last_tok.token == "##":
                    last_tok = tok
                else:
                    if len(current_cat) > 0:
                        current_cat.append(last_tok)
                        lex = Lexer("".join((x.token for x in current_cat)))
                        newtok = lex.tokenize_one()
                        if newtok is None:
                            raise ParseError(
                                f"Concatenation didn't result in valid token {lex.string}")
                        output_tokens.append(newtok)
                        current_cat = []
                        last_tok = tok
                    else:
                        output_tokens.append(last_tok)
                        last_tok = tok
        if len(current_cat) > 0:
            current_cat.append(last_tok)
            lex = Lexer("".join((x.token for x in current_cat)))
            newtok = lex.tokenize_one()
            if newtok is None:
                raise ParseError(
                    f"Concatenation didn't result in valid token {lex.string}")
            output_tokens.append(newtok)
            current_cat = []
            last_tok = tok
        elif last_tok is not None:
            output_tokens.append(last_tok)
        return output_tokens


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
        '-': OpInfo(12, "RIGHT"),
        '+': OpInfo(12, "RIGHT"),
        '!': OpInfo(12, "RIGHT"),
        '~': OpInfo(12, "RIGHT")
    }
    BinaryOperators = {
        '?': OpInfo(1, "RIGHT"),
        '||': OpInfo(2, "LEFT"),
        '&&': OpInfo(3, "LEFT"),
        '|': OpInfo(4, "LEFT"),
        '^': OpInfo(5, "LEFT"),
        '&': OpInfo(6, "LEFT"),
        '==': OpInfo(7, "LEFT"),
        '!=': OpInfo(7, "LEFT"),
        '<': OpInfo(8, "LEFT"),
        '<=': OpInfo(8, "LEFT"),
        '>': OpInfo(8, "LEFT"),
        '>=': OpInfo(8, "LEFT"),
        '<<': OpInfo(9, "LEFT"),
        '>>': OpInfo(9, "LEFT"),
        '+': OpInfo(10, "LEFT"),
        '-': OpInfo(10, "LEFT"),
        '*': OpInfo(11, "LEFT"),
        '/': OpInfo(11, "LEFT"),
        '%': OpInfo(11, "LEFT"),
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
            suffixes = ['ull', 'ULL', 'ul', 'UL', 'll', 'LL', 'u', 'U', 'l', 'L']
            for s in suffixes:
                if value.endswith(s):
                    suffix = s
                    value = value[:-len(s)]
                    break

            # Convert to decimal and then to integer with correct sign
            # Preprocessor always uses 64-bit arithmetic!
            int_value = int(value, base)
            if suffix and 'u' in suffix:
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
            "Expected an integer constant, character constant, identifier or function call.")

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
                # pylint: disable=unused-variable
                (prec, assoc) = ExpressionEvaluator.UnaryOperators[operator.token]
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
            "Expected a unary expression, an expression in parens or an identifier/constant.")

    def expression(self, min_precedence=0):
        """
        Match a preprocessor expression.
        Minimum precedence used to match operators during precedence
        climbing.

        <expression> := <primary>[<binary-op><expression>]?
        """
        expr = self.primary()

        # Recursion is terminated based on operator precedence
        while not self.eol() and (self.cursor().token in ExpressionEvaluator.BinaryOperators) and (
                ExpressionEvaluator.BinaryOperators[self.cursor().token].prec >= min_precedence):

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
                raise ValueError("Encountered a BinaryOperator with no associativity.")

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
        if op == '-':
            return -operand
        elif op == '+':
            return +operand
        elif op == '!':
            return not operand
        elif op == '~':
            return ~operand
        else:
            raise ValueError("Not a valid unary operator.")

    # pylint: disable=too-many-branches,too-many-return-statements
    @staticmethod
    def __apply_binary_op(op, lhs, rhs):
        """
        Apply the specified binary operator: lhs op rhs
        """
        if op == '||':
            return lhs or rhs
        elif op == '&&':
            return lhs and rhs
        elif op == '|':
            return lhs | rhs
        elif op == '^':
            return lhs ^ rhs
        elif op == '&':
            return lhs & rhs
        elif op == '==':
            return lhs == rhs
        elif op == '!=':
            return lhs != rhs
        elif op == '<':
            return lhs < rhs
        elif op == '<=':
            return lhs <= rhs
        elif op == '>':
            return lhs > rhs
        elif op == '>=':
            return lhs >= rhs
        elif op == '<<':
            return lhs << rhs
        elif op == '>>':
            return lhs >> rhs
        elif op == '+':
            return lhs + rhs
        elif op == '-':
            return lhs - rhs
        elif op == '*':
            return lhs * rhs
        elif op == '/':
            return lhs // rhs  # force integer division
        elif op == '%':
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


class SourceTree():
    """
    Represents a source file as a tree of directive and code nodes.
    """

    def __init__(self, filename):
        self.root = FileNode(filename)
        self._latest_node = self.root

    def associate_file(self, filename):
        self.root.filename = filename

    def walk_to_tree_insertion_point(self):
        """
        This function modifies self._latest_node to be a node that can
        be a valid sibling of a tree continue node or a tree end node.
        These nodes can only be inserted after an open tree start node,
        or a tree continue node.
        """

        while not (self._latest_node.is_start_node() or self._latest_node.is_cont_node()):
            self._latest_node = self._latest_node.parent
            if self._latest_node == self.root:
                log.error('Latest node == root while trying to find an insertion point.')
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
            if self._latest_node.is_start_node() or self._latest_node.is_cont_node():
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
            if self._latest_node.is_start_node() or self._latest_node.is_cont_node():
                self.__insert_in_place(new_node, self._latest_node)
            else:
                self.__insert_in_place(new_node, self._latest_node.parent)
