#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: common.py
 * @brief: 
 * @version 1.0
 * @date 2019/8/19
"""
from __future__ import absolute_import


import json
import re
import base64
from enum import IntEnum
from ctypes import *
import logging

sys_logger='sys.error'

error_result_js = {"result": "failed", "code": 400, "error_message": "WEB_SERVER_ERROR"}

authenticate_error_code = {200: 'ok', 
                  500: 'Server Error', 
                  404: 'No Response', 
                  1001: 'Authorization Expired', 
                  1002: 'Server Runing', 1003: 'Illegal LicecneID', 
                  1004:'No Authorization File', 
                  1005: 'Upload File Failed', 
                  1006: 'Illegal Authorization File'}

error_code = ['MV_SUCCESS', 
              'MV_NOT_SUPPORTED', 
              'MV_INVALID_DIVICE', 
              'MV_NULL_POINTER', 
              'MV_INVALID_ARGS', 
              'MV_OUT_OF_BOUND', 
              'MV_DIMS_MISMATCHED',
              'MV_OP_NOT_PERMITTED', 
              'MV_ALLOC_FAILED', 
              'MV_EXECUTION_FAILED', 
              'MV_IO_ERROR', 
              'MV_NOT_INITED',
              'MV_ALREADY_INITED', 
              'MV_LICENCE_OUTDATE', 
              'MV_LICENCE_MISMATCH']


def _load_lib():
    """Load library by searching possible path."""
    lib = CDLL("libpicasso.so")
    return lib


_LIB = _load_lib()
char_ptr = c_char_p

logger = logging.getLogger(sys_logger)


class CEnum(IntEnum):
    @classmethod
    def from_param(cls, obj):
        return int(obj)


class TaskType(CEnum):
    TASK_UNSPECIFIED = -1
    CLASSIFY = 0
    DETECT = 1
    FEATURE = 2
    ATTRIBUTE = 3
    SEGMENT = 4
    USER_DEFINE = 5
    DETECT_BEST = 6
    ALL = 7
    FEATURE_SAVE = 8
    FEATURE_QUERY = 9
    FEATURE_COM = 10
    COUNT = 11

    @staticmethod
    def from_str(label):
        if label in ('TASK_UNSPECIFIED'):
            return TaskType.TASK_UNSPECIFIED
        elif label in ('CLASSIFY'):
            return TaskType.CLASSIFY
        elif label in ('DETECT'):
            return TaskType.DETECT
        elif label in ('FEATURE'):
            return TaskType.FEATURE
        elif label in ('ATTRIBUTE'):
            return TaskType.ATTRIBUTE
        elif label in ('SEGMENT'):
            return TaskType.SEGMENT
        elif label in ('USER_DEFINE'):
            return TaskType.USER_DEFINE
        elif label in ('DETECT_BEST'):
            return TaskType.DETECT_BEST
        elif label in ('ALL'):
            return TaskType.ALL
        elif label in ('FEATURE_SAVE'):
            return TaskType.FEATURE_SAVE
        elif label in ('FEATURE_QUERY'):
            return TaskType.FEATURE_QUERY
        elif label in ('FEATURE_COM'):
            return TaskType.FEATURE_COM
        elif label in ('COUNT'):
            return TaskType.COUNT
        else:
            raise NotImplementedError


class ServerHandle(Structure):
    _fields_ = [("server_type", c_char_p),
                ("model_root", c_char_p),
                ("concurrencies", c_char_p),
                ("engine_type", c_char_p),
                ("server", c_void_p)]


class VideoHandle(Structure):
    _fields_ = [("dv_num", c_char_p),
                ("server", c_void_p)]


class VideoTask(CEnum):
    CREATE_TASK = 0
    DELETE_TASK = 1
    QUERY_TASK = 2
    START_TASK = 3
    STOP_TASK = 4
    READ_FRAME = 5
    ALL_QUERY_TASK = 6
    QUERY_OFFLINE_TASK = 7


VideoTaskTxt = ["CREATE_TASK", 
                "DELETE_TASK",
                "QUERY_TASK",
                "START_TASK",
                "STOP_TASK",
                "READ_FRAME",
                "ALL_QUERY_TASK",
                "QUERY_OFFLINE_TASK"]


dv_type_to_device_id = {"0" : "CPU",
                        "1" : "GPU:0",
                        "2" : "GPU:1",
                        "3" : "GPU:2",
                        "4" : "GPU:3",
                        "5" : "GPU:4",
                        "6" : "GPU:5",
                        "7" : "GPU:6",
                        "8" : "GPU:7"}


def parse_argument(request, keys):
    params = {}
    param_str = {}
    if request.args:
        param_js = request.args.to_dict()
        param_str.update(param_js)
    if request.form:
        param_js = request.form.to_dict()
        param_str.update(param_js)
    if request.data:
        param_js = request.data
        param_js = json.loads(param_js, encoding="utf-8")
        param_str.update(param_js)

    for key in keys:
        if key == "image_data" or key == "image_datas":
            data_stream = []
            name_list = []
            if request.files:
                try:
                    re_list = request.files.getlist(key)
                    for r in re_list:
                        data_stream.append(r.read())
                        name_list.append(r.filename)
                except:
                    data_stream.append(request.files[key].read())
                    name_list[-1].append(request.files[key].filename)
            else:				
                # if 'base64' in param_str.keys():
                #     #for s in param_str[key]:
                #     s_list = param_str["base64"].split(',')
                #     data_stream.append(base64.b64decode(s_list[1]))
                #     name_list.append(param_str["file_name"])
                # elif 'image_data' in param_str.keys():
                #     #for s in param_str[key]:
                #     s_list = param_str["image_data"].split(',')
                #     data_stream.append(base64.b64decode(s_list[1]))
                #     name_list.append("base64.jpg")

                for s in param_str[key]:
                    if isinstance(s, str):  # form_data字符串
                        form_data_json = json.loads(param_str[key])
                        for form_data in form_data_json:
                            # form_data为去掉[]后,其中的{}
                            # print("form_data:", form_data)
                            img_base = form_data["base64"].split(',')
                            data_stream.append(base64.b64decode(img_base[1]))
                            name_list.append(form_data["file_name"])
                        break
                    else:   # raw字典
                        s_list = s["base64"].split(',')
                        data_stream.append(base64.b64decode(s_list[1]))
                        name_list.append(s["file_name"])
            params["img_data"] = data_stream
            params["img_name"] = name_list
        elif key == "base64_img":
            name_list = []
            data_stream = []
            img_base = param_str[key].split(',')
            if len(img_base) == 1:
                data_stream.append(base64.b64decode(img_base[0]))
            else:
                data_stream.append(base64.b64decode(img_base[1]))
            name_list.append("unknow.jpg")
            params["img_data"] = data_stream
            params["img_name"] = name_list
        else:
            if key not in param_str.keys():
                continue
            param = param_str[key]
            if key == "rect":
                res = []
                param = eval(param.replace(", ", ",").replace(" ,", ",").replace(" ", ","))
                if isinstance(param, list):
                    res.append(param)
                else:
                    for par in param:
                      res.append(par)
                params["rect"] = res
            else:
                params[key] = param
    return params


def list2char_pp(data_list):
    DataArray = (c_char_p * len(data_list))
    data_array = DataArray()
    for i in range(len(data_list)):
        data_array[i] = data_list[i].encode('utf-8')
    return data_array


def covert_image2ctype(datas, names):
    """
    convert http data stream to c type
    :param datas: http data stream
    :param names: image names
    :return:
    """
    len_list = [len(stream) for stream in datas]
    lengs = (c_int * len(datas))(*len_list)
    image_datas = (c_char_p * len(datas))(*datas)
    NameArray = (c_char_p * len(names))
    img_name = NameArray()
    for i in range(len(names)):
        img_name[i] = names[i].encode("utf-8")
    # img_name = (c_char_p * len(name_list[0]))(*name_list.encode("utf-8"))

    img_num = c_int(len(datas))
    return image_datas, lengs, img_num, img_name


import time
from functools import wraps

def cost_record(output):
    def use_time(func):
        @wraps(func)
        def wraper(*args, **kwargs):
            start = time.time()
            t = func(*args, **kwargs)
            end = time.time()
            output("{} tooks time: {}s, from {} to {}".format(func.__name__, round(time.time() - start, 4),
                                                              time.strftime("%Y-%m-%d %H:%M:%S",
                                                                            time.localtime(int(start))),
                                                              time.strftime("%Y-%m-%d %H:%M:%S",
                                                                            time.localtime(int(end)))))
            return t

        return wraper

    return use_time
