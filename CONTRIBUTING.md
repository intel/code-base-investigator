# Contributing to Code Base Investigator
Thanks for taking the time to contribute to Code Base Investigator!

## Bug Reports
- Open a GitHub issue containing as much information as possible, including configuration files and source code.
- If your code base is large and/or cannot be shared, we would greatly appreciate it if you could construct a minimal working example.

## Feature Requests
- Open a GitHub issue detailing the expected behavior of the feature.
- Where appropriate, please include sample input/output of the requested feature.

## Submitting a Patch
- Follow the style guidelines for all commits and code:  
  - Limit the first line of Git commit messages to 50 characters, and other lines to 72 characters.
  - Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for Python code, with a line limit of 79 characters and a comment/docstring limit of 72 characters. `black` is part of the `pre-commit` hooks, and if installed should automatically format your code.
- Ensure that the patched code passes all existing tests:  
  ```
  python3 -m unittest
  ```
- Please consider linting your code with `flake8`; alongside `black` for style, it is configured to be part of the `pre-commit` workflow.
- If your patch introduces a new feature, consider adding a new test.
- Open a new GitHub pull request with the patch.

### Hooks

We use `pre-commit` to manage commit workflows to ensure uniform code style, linting, and testing.
As part of getting started, install `pre-commit==3.5.0` and run `pre-commit install` which will
create virtual environments for development packages and install `git commit` hooks.
