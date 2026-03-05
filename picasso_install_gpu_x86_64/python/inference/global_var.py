#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: global.py
 * @brief: 
 * @version 1.0
 * @date 2021/6/28
"""
from __future__ import absolute_import

def _init():
    """ 全局变量字典初始化 """
    global _global_dict
    _global_dict = {}


def set_value(key, value):
    """ 创建全局变量 """
    _global_dict[key] = value


def get_value(key):
    """ 获取全局变量"""
    return _global_dict.get(key)
