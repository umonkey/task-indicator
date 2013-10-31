#!/usr/bin/env python
# encoding=utf-8

from __future__ import print_function

import re
import sys


def find_version(fn, pattern):
    with open(fn, "rb") as f:
        for v in re.findall(pattern, f.read(), re.M):
            return v


search = [
    ("NEWS", r'\(version ([0-9.]+)\)'),
    ("Makefile", "VERSION=([0-9.]+)"),
    ("setup.py", "version\s*=\s*'([0-9.]+)'"),
    ]

version = None
mismatch = []
for fn, pattern in search:
    v = find_version(fn, pattern)
    if version is None:
        version = v
    elif version != v:
        mismatch.append(fn)

if mismatch:
    print("Old version number in {0}.".format(", ".join(mismatch)))
    sys.exit(1)
