# Copyright (C) 2019-2024 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
import shlex
import warnings

import codebasin.source
import codebasin.walkers

warnings.warn(
    "Calling codebasin package internals is deprecated. "
    + "Please call the codebasin script directly instead. "
    + "A new, stable, package interface will be introduced in "
    + "a future release of Code Base Investigator.",
    DeprecationWarning,
)


class CompileCommand:
    """
    A single compile command from a compilation database.

    Attributes
    ----------
    filename: string
        The name of the source file compiled by this command.

    directory: string, optional
        The working directory for this command.

    arguments: list[string], optional
        The `argv` for this command, including the executable as `argv[0]`.

    output: string, optional
        The name of the file produced by this command, or None if not
        specified.
    """

    def __init__(
        self,
        filename,
        directory=None,
        arguments=None,
        command=None,
        output=None,
    ):
        """
        Raises
        ------
        ValueError
            If both arguments and command are None.
        """
        self._filename = filename
        self._directory = directory
        if arguments is None and command is None:
            raise ValueError("CompileCommand requires arguments or command.")
        self._arguments = arguments
        self._command = command
        self._output = output

    @property
    def directory(self):
        return self._directory

    @property
    def filename(self):
        return self._filename

    @property
    def arguments(self):
        if self._arguments is None:
            return shlex.split(self._command)
        else:
            return self._arguments

    @property
    def output(self):
        return self._output

    def __str__(self):
        if self._command is None:
            return " ".join(self._arguments)
        else:
            return self._command

    def is_supported(self):
        """
        Returns
        -------
        bool
            True if the command can be emulated and False otherwise.
            Commands that are not supported will not impact analysis.
        """
        # Commands must be non-empty in order to do something.
        # Commands must operate on source files.
        if len(self.arguments) > 0 and codebasin.source.is_source_file(
            self.filename,
        ):
            return True

        return False

    @classmethod
    def from_json(cls, instance: dict):
        """
        Parameters
        ----------
        instance: dict
            A JSON object representing a single compile command.

        Returns
        -------
        CompileCommand
            A CompileCommand corresponding to the JSON object.
        """
        directory = instance.get("directory", None)
        arguments = instance.get("arguments", None)
        command = instance.get("command", None)
        output = instance.get("output", None)
        return cls(
            instance["file"],
            directory=directory,
            arguments=arguments,
            command=command,
            output=output,
        )
