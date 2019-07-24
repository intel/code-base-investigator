Code Base Investigator Configuration File Format
================================================

Information about the type of analysis to be performed on a code base is communicated to Code Base Investigator through a configuration file expressed in YAML. This file contains information about what files should be analyzed, what platforms should be considered, and at least partial information about how the code is built on for each platform. What follows is a description of the configuration file format; users are also encouraged to consult the example configurations in the `examples/` directory.

## YAML

YAML is a markup language with similarities to JSON that is intended to be expressive and human readable/writable. The full details of the format are quite complex and can be found at [yaml.org](https://yaml.org/); only a subset of the full expressiveness of the format is required for Code Base Investigator. Here are the basics:

- The format is plain text; in most cases, UTF-8 will be sufficient
- The line comment character is '#'
- YAML supports multiple 'documents' in a single stream (file), but Code Base Investigator will only load the first such document in any file.
- YAML has two main compound types: _sequences_, which express ordered relationships between values, and _mappings_, which express unordered key-value pairs. There are also numerous scalar types that YAML understands natively, including real numbers and strings.
- There are two main ways to express compound types: block-style, which rely on newlines and indentation, and 'inline', which relies on special delimiters and largely ignores whitespace.
  Block-style sequences are indicated using `-` characters:

        - Item 1
        - Item 2
        - Item 3

  Inline-style sequences are indicated using bracket delimiters `[`, `]` and comma separators:

        [ Item 1, Item 2, Item 3 ]

  Block-style mappings use the colon `:` to separate keys and values:

        key 1: item 1
        key 2: item 2
        key 3: item 3

  Inline-style mapping use curly braces `{`, `}` and commas to enclose key-value pairs:

        { key 1: item 1, key 2: item 2, key 3: item 3 }

## Code Base Investigator Configuration

The configuration file is structured as a mapping at the top level. A single `codebase` key with associated mapping is required, and a key for each platform along with platform mappings should be provided.

### Codebase Mapping

A `codebase` key is required, which should contain a mapping containing: the key `files`, which is a sequence of file specifiers, and `platforms`, which is a sequence of user-defined names for platforms to be considered.

    codebase:
        files: [ <file-spec>,+ ]
        platforms: [ <platform-name>,+ ]

The `<file-spec>` is a string that specifies a (relative) path to files in the source tree. It can be a literal path to a file, or globs are supported (for Python 3.5 and later).  The files are expanded with respect to the `--rootdir` specified on the commandline at invocation, or the default, which is the working directory where Code Base Investigator was invoked.

`<platform-name>` can be any string; they are referred to by later platform definitions in the configuration file.

### Platform Mappings

There should be a key for each platform that appears in the codebase platform sequence discussed above, and each such key should be accompanied by a mapping that describes the 'configuration': how the code base fed to a compiler for said platform. There are two supported methods: manual specification and compilation databases.

#### Manual Platform Specification

With manual specification, the mapping for a platform should contain a `files` key with a sequences of `<file-spec>`s, just as with the `codebase` mapping. The distinction is that the `files` for a platform may well be a subset of the whole set specified for the `codebase`.

Additionally, the user may specify one each of the keys `defines` and `include_paths`, each with a sequence. `defines` is a sequence of C preprocessor symbols that should be applied when interpreting the `files` for this platform. They may be specified in the form `[-D]<directive>[=<value>]`; the optional `-D` prefix is permitted to emulate the command-line option setting of preprocessor directives found in gcc and other compilers.

`include_paths` is used to specify (absolute) directory paths that should be included when processing `#include` directives in the source code.

#### Compilation Database Platform Specification

Compilation databases are simple markup files that contain information about how a compiler was invoked. They are typically named `compilation_commands.json` and are located in the build directories of projects. There are tools for generating compilation databases for most build systems:

- CMake: add `-DCMAKE_EXPORT_COMPILE_COMMANDS` to the `cmake` invocation.
- Ninja: invoke `ninja` with `-t compdb`.
- Others: [Build EAR](https://github.com/rizsotto/Bear)

To use a compilation database, specify the relative path in the value associated with a `commands` key under the platform mapping. Code Base Investigator will then load that compilation database and use its contents to define the configuration for that platform.

#### Combining Manual Platform Specifications with Compilation Databases

It is possible to combine the manual platform specification and the compilation database platform specification by specifying both the `commands` key along with some or all of the `files`/`defines`/`include_paths` used in manual specification; if either set of rules indicates that a source line belongs to the platform, the line will be associated with said platform. This is useful when the user wishes to expand the scope of what is associated with a platform beyond what a single compilation database contains.
