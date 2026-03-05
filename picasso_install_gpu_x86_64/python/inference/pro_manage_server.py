#!/usr/bin/env python
# coding: utf-8
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: pro_manage_server.py
 * @brief: 
 * @version 1.0
 * @date 2023/4/7
"""

from pickle import TRUE
from .common import _LIB, logger, parse_argument
from ctypes import *
import json
import os
import psutil as p
import time
import datetime
import subprocess

#-----------------获取内存信息
def get_pid(pname):
    list_pid = []
    for proc in p.process_iter():
        if proc.name() == pname:
            list_pid.append(proc.pid)
            # print(proc.pid)

    if len(list_pid) == 0:
        print("该进程不存在！")
        return None
    
    return list_pid

def get_meminfo_process():
    pid_list = get_pid("uwsgi")
    res_list = ''
    for pid in pid_list:
        ps = p.Process(pid)
        cpu_percent = ps.cpu_percent(interval=0.1)
        mem_percent = ps.memory_percent()
        print("cpu: {:.2f}%, memory: {:.2f}%".format(cpu_percent,mem_percent))
        if cpu_percent >= 0 and mem_percent >= 0:
            res_list = '{"result": "success","cpu": "%.2f%%","memory": "%.2f%%"}' % (cpu_percent,mem_percent)
        elif cpu_percent < 0 or mem_percent < 0:
            res_list = '{"result": "failed","The cpu or memery values are less than 0 "}'
    return res_list


#-------------------------工程重启
def pro_restart_process():
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    target_script_path = os.path.join(curr_dir,"restart_picasso.py")
    #创建子进程
    child_process = subprocess.Popen(["python",target_script_path])
   
    return '{"result": "success","message": "picasso restarted!"}'

    # shell_path = '/data/rguo/picasso_v2.0/build/picasso_install_gpu_x86_64/server.sh'
    # shell_args = ['autorestart']
    # result = subprocess.run(['sh']+[shell_path] + shell_args)
    # return '{"result": "success","message": "picasso restarted!"}'


#-------------------------版本更新

def pro_version_update_process(data):
    keys = ["version_update"]
    params = parse_argument(data, keys)
    version_update_path = params["version_update"] if "version_update" in params else ""
    if version_update_path != "":
        processor = _LIB.mvProjectVersionUpdate
        processor.restype = c_int
        status = processor(c_char_p(version_update_path.encode('utf-8')))
        if status != 0:
            logger.error("Project Update Task Error!")
    return '{"result": "success","message": "picasso updated!"}'
    

#-------------------------模型热更新
def model_update_process(data):
    keys = ["model_update"]
    params = parse_argument(data, keys)
    model_update = params["model_update"] if "model_update" in params else ""
    print("path is: ",model_update)
    if len(model_update) == 0:
        print("the update dir is empty")
    else:
        files = os.listdir(model_update)
        for k in range(len(files)):
            files[k] = os.path.splitext(files[k])[1]  # 提取文件夹内所有文件的后缀
        model = '.m'
        config = '.json'
        label = '.txt'
        if model in files:
            print("the model file exists")
        else:
            print("the model file dose not exists")
        if config in files:
            print("the config file exists")
        else:
            print("the config file dose not exists")
        if label in files:
            print("the label file exists")
        else:
            print("the label file dose not exists")
    
    processor = _LIB.mvProjectManageTaskProcess
    processor.restype = c_int
    status = processor(c_char_p(model_update.encode('utf-8')))
    if status != 0:
        logger.error("Model Update Task Error!")
    return "{\"result\": \"success\",\"code\": 200}"
