#! /usr/bin/env python
# -*- coding: utf-8 -*-

### Auto generated file, DO NOT Edit   ###

import compileall
import py_compile
import os
import glob

#compileall.compile_dir("/data/dyc/picasso_v2.0/build/picasso_install_gpu_x86_64/python")
for py in glob.iglob("./**/*.py", recursive=True):
    if(os.path.basename(py) == "restful_framework.py"): continue
    py_compile.compile(py, py + 'c')
    os.remove(py)

