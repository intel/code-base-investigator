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
  - Follow [PEP8](https://www.python.org/dev/peps/pep-0008/) for Python code, with a line limit of 99 characters and a comment/docstring limit of 72 characters.
- Ensure that the patched code passes all existing tests:  
  ```
  python3 -m unittest
  ```
- Consider checking the quality of your code with [`pylint`](https://github.com/PyCQA/pylint).
- If your patch introduces a new feature, consider adding a new test.
- Open a new GitHub pull request with the patch.

### Hooks
A number of [Git hooks](./hooks) are available to assist contributors in adhering to the guidelines above:
- pre-commit:  
  Optionally run [`pylint`](https://github.com/PyCQA/pylint) and/or [`autopep8`](https://github.com/hhatto/autopep8) on every commit.
- post-commit:   
  Run the full test suite after every commit.

We use `pre-commit` to manage commit workflows to ensure uniform code style, linting, and testing.
As part of getting started, install `pre-commit==3.5.0` and run `pre-commit install` which will
create virtual environments for development packages and install `git commit` hooks.
