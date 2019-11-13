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
    if path.parts[0] == 'dlpbenchcuda' and path.parts[1] != 'utils':
        app = 'dlpbench-'  + path.parts[1]
    elif path.parts[0] == 'dlpbenchopencl':
        app = 'dlpbench-'  + path.parts[1]
    elif path.parts[0] == 'dlpbench' and path.parts[1] != 'common' and path.parts[1] !='deprecated_workloads' and path.parts[1] != 'csa':
        app = 'dlpbench-'  + path.parts[2]
    elif path.parts[0] in ['cmedia-bench', "config", "infrastructure", "Test-Infrastructure"]:
        app = None
    elif path.parts[0] == 'DNNBench' and not path.parts[1] == 'common':
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
    paths = {}
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
                    platmap[p].append(Path(f))
        else:
            update=is_in.intersection(all_lang)
            if len(update) > 0:
                for p in update:
                    platmap[p].append(Path(f))
    return platmap

def write_yaml(output, files, langs_names_map, strip_prefix=Path(".")):

    platmap = app_groups(files, frozenset(langs_names_map.values()))
    all_files = set()
    for plat, pfiles in platmap.items():
        all_files.update([str(f.relative_to(strip_prefix)) for f in pfiles])
    if len(all_files) == 0:
        return False
    base = {'codebase' : { 'files' : list(all_files) }}
    plats = set()
    for export_name, plat_name in langs_names_map.items():
        plat_files = [str(f.relative_to(strip_prefix)) for f in platmap[plat_name]]
        if len(plat_files) > 0:
            base[export_name] = {'files': plat_files}
            plats.update([export_name])
        elif len(langs_names_map) < 4: #Hack
            return False
    base['codebase']['platforms'] = list(plats)
    with open(output, "w") as ofp:
        yaml.dump(base, ofp)
    return True

os.chdir("/nfs/home/jsewall/CDS-DPCPP-HPCBench/")
apps = walk_apptree(".", re.compile('(.*\.)(cpp|c|hpp|h|cl|cu|cxx|cc|cuh)$'))

#os.chdir("/nfs/home/jsewall/CDS-DPCPP-HPCBench/configs")
for app_name, app_files in apps.items():

    prefixed= [f"./{p}" for p in app_files]
    app_path = Path(os.path.commonpath(prefixed))
    if app_path.is_file():
        app_path = app_path.parent

    outpath = app_path / "cbi-configs"
    try:
        os.makedirs(outpath)
    except FileExistsError:
        pass
    for suffix, config in [("all", dict(zip(*it.repeat(['cuda', 'opencl', 'dpc++', 'openmp'],2)))),
                           ("dpcpp", {'dpc++-gpu' : 'dpc++', 'dpc++-cpu' : 'dpc++'}),
                           ("ducttape", {'gpu' : 'cuda', 'cpu' : 'openmp'})]:
        outfile = outpath / f"{app_name}-{suffix}.yaml"
        write = write_yaml(outfile, app_files, config, strip_prefix=app_path)
        if write:
            print(outfile)

print("done")
