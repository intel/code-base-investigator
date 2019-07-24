#!/bin/bash

# Setup git hooks for style formatting and testing
echo " This script will help set up the git hooks for Code Base Investigator"
echo
echo " The hooks are configured using git config variables."
echo " Below are a description of the variables, and their possible values."
echo "    hooks.autopep8 = {never, always}"
echo "        - never = autopep8 is never run prior to creating a commit."
echo "        - always = autopep8 is always run prior to creating a commit."
echo "    hooks.pylint = {never, relaxed, strict}"
echo "        - never = pylint is never run prior to creating a commit."
echo "        - relaxed = pylint is always run prior to creating a commit, but errors do not prevent commits."
echo "        - strict = pylint is always run prior to creating a commit, and errors prevent commits."
echo "    hooks.tests = {never, always}"
echo "        - never = unit tests are never run after creating a commit."
echo "        - always = unit tests are always run after creating a commit."
echo
echo " The default settings are:"
echo "   hooks.autopep8 = never"
echo "   hooks.pylint = never"
echo "   hooks.tests = never"
echo
echo " To change these use:"
echo "    git config --replace-all hooks.autopep8 [value]"
echo "    git config --replace-all hooks.pylint [value]"
echo "    git config --replace-all hooks.tests [value]"

git config --replace-all hooks.autopep8 never
git config --replace-all hooks.pylint never
git config --replace-all hooks.tests never

ROOT=`git rev-parse --show-toplevel`

cp ${ROOT}/hooks/* ${ROOT}/.git/hooks/.
