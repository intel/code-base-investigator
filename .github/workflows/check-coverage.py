#!/usr/bin/env python3
import argparse
import json
import subprocess  # nosec B404
import sys

# Parse command-line arguments.
parser = argparse.ArgumentParser()
parser.add_argument("--commits", nargs="+", default=[])
parser.add_argument("file", metavar="<coverage.json>", action="store")
args = parser.parse_args(sys.argv[1:])

# Read the coverage information into an object.
with open(args.file, "rb") as f:
    coverage = json.load(f)

# For each file:
# - Determine which lines were not covered;
# - Check when the lines were last modified;
# - Print details of new, uncovered, lines.
report = {}
for filename, info in coverage["files"].items():
    if not isinstance(filename, str):
        raise TypeError("filename must be a string")

    missing = info["missing_lines"]
    if not missing:
        continue

    for lineno in missing:
        if not isinstance(lineno, int):
            raise TypeError("line numbers must be integers")
        cmd = [
            "git",
            "blame",
            filename,
            "-L",
            f"{lineno},{lineno}",
            "--no-abbrev",
        ]
        completed = subprocess.run(cmd, capture_output=True)
        commit = completed.stdout.decode().split()[0].strip()

        if commit in args.commits:
            if filename not in report:
                report[filename] = []
            report[filename].append(str(lineno))

for filename in report:
    n = len(report[filename])
    print(f'{n} uncovered lines in {filename}: {",".join(report[filename])}')

# Use the exit code to communicate failure to GitHub.
if len(report) != 0:
    sys.exit(1)
else:
    sys.exit(0)
