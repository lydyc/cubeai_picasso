#!/usr/bin/env python
# coding: utf-8
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: __init__.py
 * @brief: 
 * @version 1.0
 * @date 2019/10/30
"""

import requests
import os, sys, shutil
import json
from .picasso import *
from .common import _LIB, dv_type_to_device_id, logger, VideoTask
from .video_server import VideoServer
from inference import global_var as gv
import configparser


video_server = VideoServer()
server_list = []    # 系统配置的服务列表: list of server_id
engines = []    # Picasso SDK 支持的引擎信息: list of server_info
device = []    # 设备列表: list of dv_type
auth_description = []  # 授权服务对应json中的描述名

gv._init()
gv.set_value('handle_flag', False)   # 引擎句柄初始化标志：flag of engine handle

def load_json(file_path, device_new):
    '''[读取file_path所在路径下模型配置文件, 读取"infer_device"键值对, 若与输入device_new不匹配，则更新并返回整个json对象]

    Args:
        file_path ([str]): [模型配置文件所在路径]
        device_new ([str]): [分号分隔的设备列表，如GPU:0;GPU:1]
    '''
    with open(file_path, "r", encoding="utf_8") as fp:
        info = json.load(fp)

        infer_device = info.get("infer_device", "")
        if device_new != infer_device:
            info["infer_device"] = device_new
        return info

def dump_json(file_path, info):
    '''[打开file_path所在路径下模型配置文件, 将内容为info的json对象保存为指定json文件]

    Args:
        file_path ([str]): [模型配置文件所在路径]
        info ([json_object]): [更新infer_device后的json对象]
    '''
    with open(file_path, "w", encoding="utf_8") as fp:
        json.dump(info, fp, indent=4, ensure_ascii=False) # ensure_ascii=False表示不要对非ASCII字符进行转义, 因此中文字符将以原始形式保存在文件中

def picasso_create_engines(licence_serial, server_enable, repeat_switch, task_per_thread, max_concurrency):
    """[创建所需的服务，用于后续的分析使用]

    Args:
        licence_serial ([str]): [机器授权码]
    """
    for server_id in server_enable:
        if server_id in ["video_server"]:  # 动态视频服务
            video_server.create_server_handle(device[0], licence_serial, repeat_switch, task_per_thread, max_concurrency)
        else:  # 静态图片服务
            create_image_server_handle(server_id, licence_serial, "", "", device[0])
        print("init_handle: {}".format(server_id))

def createHandleAndGetVersionInfo(conf):
    # 若配置文件有 serverlist 字段, 则根据配置文件中服务列表通过 api 获取引擎信息及创建句柄
    # 若配置文件无 serverlist 字段或为空, 则默认获取 picasso 支持的所有引擎信息及创建所有句柄 
    if conf.has_section("server") and len(conf["server"]) > 0:
        server_str = conf["server"]["server_list"]

    # 通过 picasso api 获取引擎信息
    server_infos = register_server_list(server_str)

    for server in server_infos.split(";"):
        combined_server_id = server.split(":")[0]
        combined_server_info = server.split(":")[1].split("+")
        # print(combined_server_info)
        single_engines = []
        # TODO:需要在此处根据每个单服务的名称, 获取对应的json中的全部信息, 提取出description
        for single_server_info in combined_server_info:
            server_info = {}
            single_server_id = single_server_info.split(",")[0]
            single_server_version = single_server_info.split(",")[1]
            # 每个引擎组合name和version信息构成字典，并追加至single_engines和engines列表中
            server_info["name"] = single_server_id
            server_info["version"] = single_server_version

            description_result = c_char_p()
            server_list_desciption = _LIB.mvGetModelDescription
            server_list_desciption.restype = c_char_p
            server_list_desciption(c_char_p(single_server_id.encode('utf-8')), byref(description_result))  # 返回的是执行状态
            server_info["description"] = str(description_result.value, encoding="utf-8")
            # single_engines列表用于打印消息
            single_engines.append(server_info)
            # engines用于/verify/version接口显示模型信息
            engines.append(server_info)

            status = destroy_result(description_result)
            if status != 0:
                print("Destroy Description Result Error!")

        server_list.append(combined_server_id)
        print("registered server [{}] -> {}".format(combined_server_id, single_engines))


def picasso_start():
    """[根据配置文件初始化 picasso SDK, 并启动所需的引擎]

    配置文件示例:
        [server]
        server_list = safety_wear_server;non_vehicle_server;...;face_server

        [device]
        dv_type = 1;

        [licence]
        serial_num = ...
    """
    licence = ""
    server_str = ""

    # 解析配置文件，并读取节点信息
    conf = configparser.ConfigParser()
    configfile = "./python/inference/config.ini"
    conf.read(configfile)
    sec = conf.sections()

    # 读取配置文件中licence节点信息，并由licence创建服务和初始化相关信息
    if conf.has_section("licence"):
        if len(conf["licence"]["serial_num"]) > 0:
            licence = conf["licence"]["serial_num"]

    # 读取配置文件中device节点信息，并由device创建服务和初始化相关信息
    if conf.has_section("device") and len(conf["device"]["dv_type"]) > 0:
        dv_type = conf["device"]["dv_type"]
        device.append(dv_type)

    dv_arr = device[0].split(";")
    device_new = ""
    for i in dv_arr:
        if len(i) <= 0:
            continue
        elif int(i) < 0 or int(i) > 8:
            logger.info("DEVICE_ID is unknow in Python: {}".format(i))
        device_new += dv_type_to_device_id[i] + ";"
    device_new = device_new[:-1]

    repeat_switch = 0
    task_per_thread = 10
    max_concurrency = 50
    if conf.has_section("video"):
        repeat_switch = int(eval(conf["video"]["repeat_switch"]))
        task_per_thread = int(eval(conf["video"]["task_per_thread"])) 
        max_concurrency = int(eval(conf["video"]["max_concurrency"]))

    env_dist = os.environ # environ是在os.py中定义的一个dict environ = {}
    model_configs_dir = env_dist.get('PICASSO_MODEL_PATH')
    # model_configs_dir = "./model/configs/"
    for root, dirs, files in os.walk(model_configs_dir):  
        for file in files:
            file_path = os.path.join(model_configs_dir, file)
            
            if file_path.endswith(".json"):
                info = load_json(file_path, device_new)
                dump_json(file_path, info)

    # 通过 api 完成初始化操作
    init_picasso()
    createHandleAndGetVersionInfo(conf)
    '''
    # 若配置文件有 serverlist 字段, 则根据配置文件中服务列表通过 api 获取引擎信息及创建句柄
    # 若配置文件无 serverlist 字段或为空, 则默认获取 picasso 支持的所有引擎信息及创建所有句柄 
    if conf.has_section("server") and len(conf["server"]) > 0:
        server_str = conf["server"]["server_list"]

    # 通过 picasso api 获取引擎信息
    server_infos = register_server_list(server_str)

    for server in server_infos.split(";"):
        combined_server_id = server.split(":")[0]
        combined_server_info = server.split(":")[1].split("+")
        # print(combined_server_info)
        single_engines = []
        for single_server_info in combined_server_info:
            server_info = {}
            single_server_id = single_server_info.split(",")[0]
            single_server_version = single_server_info.split(",")[1]
            # 每个引擎组合name和version信息构成字典，并追加至single_engines和engines列表中
            server_info["name"] = single_server_id
            server_info["version"] = single_server_version
            # single_engines列表用于打印消息
            single_engines.append(server_info)
            # engines用于/verify/version接口显示模型信息
            engines.append(server_info)
        server_list.append(combined_server_id)
        print("registered server [{}] -> {}".format(combined_server_id, single_engines))
    '''
    if licence:
        gv.set_value('handle_flag', True)
        server_list.append("video_server")
        picasso_create_engines(licence, server_list, repeat_switch, task_per_thread, max_concurrency)
        print("activate init_server with device: {} and licence: {} ".format(device[0], licence))

#查看实时、轮询任务请求文件是否存在数据，若存在，说明当前任务需要重启
def view_request_task_file():
    filename = './python/inference/request_task_file.json'
    if not os.path.exists(filename):
        os.system(r"touch {}".format(filename))#调用系统命令行来创建文件
        
    try:
        real_time_task_count = 0
        patrol_task_count = 0
        with open(filename,'r') as load_f:
            for line in load_f.readlines():
                try: #防止文件中数据格式有问题导致的崩溃
                    data = json.loads(line)
                except ValueError:
                    continue
                #取出task_mode字段，判断当前任务是轮询还是实时
                task_mode = data['task_mode'] if 'task_mode' in data else None
                if task_mode is None:
                    continue
                #若task_mode为1，则为实时任务
                if int(task_mode) is 1:
                    video_server.video_process(data,VideoTask.CREATE_TASK)
                    video_server.video_process(data,VideoTask.START_TASK)
                    real_time_task_count = real_time_task_count + 1
                #若task_mode为0，则为轮询任务
                if int(task_mode) is 0:
                    video_server.video_process(data,VideoTask.CREATE_TASK)
                    patrol_task_count = patrol_task_count + 1
            
            if real_time_task_count != 0 or patrol_task_count != 0 :
                output_str = 'Restarting the tasks, These include ' + str(real_time_task_count) + \
                            ' real_time video tasks and ' + str(patrol_task_count) + ' patrol video tasks.'
                print(output_str)
                
    except IOError:
        return
    load_f.close()

picasso_start()
view_request_task_file()
