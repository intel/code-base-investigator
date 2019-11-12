#!/usr/bin/env python3.6

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from sloc_translate import file_sloc
from codebasin.file_source import get_file_source
from codebasin.report import divergence

import csv
from pathlib import Path
from collections import defaultdict
import re
import itertools as it
import yaml

def guess_app(inpath):
    path = Path(inpath)
    if path.parts[0] == 'dlpbenchcuda':
        app = 'dlpbench-'  + path.parts[1]
    elif path.parts[0] == 'dlpbenchopencl':
        app = 'dlpbench-'  + path.parts[1]
    elif path.parts[0] == 'dlpbench':
        app = 'dlpbench-'  + path.parts[2]
    elif path.parts[0] == 'cmedia-bench':
        app = None
    elif path.parts[0] == 'DNNBench':
        app = f"DNNBench-{path.parts[1]}"
    else:
        app = path.parts[0]
    return app

def matches(path, regexp):
    return regexp.search(path) != None

class plat_guesser(object):
    def __init__(self, name, pathwl, extwl):
        self.name = name
        self.pathwl = pathwl
        self.pathbl = []
        self.extwl = extwl
        self.extbl = []
    def finalize(self):
        if len(self.pathwl) > 0:
            all_exts = "|".join((f"[^a-z]+{x}|{x}[^a-z]+" for x in (z.replace("+", r"\+") for z in self.pathwl)))
            self.pathwl_re = re.compile(f"{all_exts}")
        else:
            self.pathwl_re = re.compile(r"^\b$")
        if len(self.pathbl) > 0:
            all_exts = "|".join((f"[^a-z]+{x}|{x}[^a-z]+" for x in (z.replace("+", r"\+") for z in self.pathbl)))
            self.pathbl_re = re.compile(f"{all_exts}")
        else:
            self.pathwl_re = re.compile(r"^\b$")
        if len(self.extwl) > 0:
            all_exts = "|".join(self.extwl)
            self.extwl_re = re.compile(f"(.{all_exts})$")
        else:
            self.extwl_re = re.compile(r"^\b$")
        if len(self.extbl) > 0:
            all_exts = "|".join(self.extbl)
            self.extbl_re = re.compile(f"(.{all_exts})$")
        else:
            self.extbl_re = re.compile(r"^\b$")
    def score(self, path):
        neg, pos = False, False
        pos |= matches(path, self.pathwl_re)
        neg |= matches(path, self.pathbl_re)
        pos |= matches(path, self.extwl_re)
        neg |= matches(path, self.extbl_re)
        return self.name, (neg, pos)


guessers = [plat_guesser("cuda",
                         ["cuda"],
                         ["cu"]),
            plat_guesser("opencl",
                         ["opencl", "ocl"],
                         ["cl"]),
            plat_guesser("dpc++",
                         ["dpc++", "dpcpp", "sycl"],
                         []),
            plat_guesser("openmp",
                         ["omp", "openmp"],
                         [])]

all_pathwl = set()
all_extwl = set()
for g in guessers:
    all_pathwl.update(set(g.pathwl))
    all_extwl.update(set(g.extwl))

for g in guessers:
    g.pathbl = list(all_pathwl.difference(set(g.pathwl)))
    g.extbl = list(all_extwl.difference(set(g.extwl)))
    g.finalize()

def guess_platform(inpath):
    path = Path(inpath)
    return path.parts[1]

def categorize_file(inpath):
    res = {}
    path = inpath.lower()
    for g in guessers:
        name, cat = g.score(path)
        res[name] = cat
    return res

def walk_apptree(inroot, regexp):
    apps = defaultdict(list)
    for root, dirs, files in os.walk(inroot):
        for f in files:
            full_path = os.path.join(root, f)
            if regexp.match(full_path):
                app = guess_app(full_path)
                if app:
                    apps[app].append(os.path.relpath(full_path, inroot))
    return apps

def app_groups(files, all_lang=frozenset(['cuda', 'opencl', 'dpc++', 'openmp'])):
    platmap = defaultdict(list)
    for f in files:
        cats = categorize_file(f)
        is_in = set()
        isnt_in = set()
        for k, which in cats.items():
            if which[1]:
                is_in.update([k])
            if which[0]:
                isnt_in.update([k])
        if len(is_in) == 0:
            partial_common = all_lang.difference(isnt_in)
            if len(partial_common) > 0:
                for p in partial_common:
                    platmap[p].append(f)
        else:
            update=is_in.intersection(all_lang)
            if len(update) > 0:
                for p in update:
                    platmap[p].append(f)
    return platmap

def write_yaml(output, files):
    platmap = app_groups(files)
    base = {'codebase' : { 'files' : files, 'platforms' : list(platmap.keys()) }}
    for plat_name, plat_files in platmap.items():
        base[plat_name] = plat_files
    with open(output, "w") as ofp:
        yaml.dump(base, ofp)

os.chdir("/nfs/home/jsewall/CDS-DPCPP-HPCBench/")
apps = walk_apptree(".", re.compile('(.*\.)(cpp|c|hpp|h|cl|cu|cxx|cc|cuh)$'))

for app_name, app_files in apps.items():

    write_yaml(f"{app_name}.yaml", app_files)
    print(f"{app_name}.yaml")

print("done")
