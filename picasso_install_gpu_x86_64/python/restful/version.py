#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
 * @file: version.py
 * @brief: 服务信息查询与密钥管理接口
 * @version 1.0
 * @date 2020/4/8
"""

import configparser
import json
import logging
from flask import Blueprint, request, jsonify
from inference.picasso import destroy_server_handle, get_sdk_version, generate_licence, check_licence, server_handle_dict
from inference.common import parse_argument, error_result_js, sys_logger
from inference import engines, auth_description, picasso_create_engines, createHandleAndGetVersionInfo
from inference import global_var as gv

logger = logging.getLogger(sys_logger)

version_reply = Blueprint("version", __name__)


def base_version():
    __VERIFY_SERVER_HTTP_VERSION__ = '1.2.1'
    bver = {"server_http": __VERIFY_SERVER_HTTP_VERSION__,
            "picasso_sdk": get_sdk_version()}
    return bver

def save_licence_to_config(licence_serial):
    """[将授权码更新到本地的配置文件 ./python/inference/config.ini]

    Args:
        licence_serial ([str]): [毕加索授权码]]
    """
    cfg = configparser.ConfigParser()
    configfile = "./python/inference/config.ini"
    cfg.read(configfile)
    sec = cfg.sections()
    if cfg.has_section("licence") and cfg.get("licence", "serial_num") != licence_serial:
        cfg.set("licence", "serial_num", licence_serial)
        with open(configfile, "w+") as f:
            cfg.write(f)

def read_server_enable_from_config():
    """[读取本地的配置文件中server_list ./python/inference/config.ini]
    """
    cfg = configparser.ConfigParser()
    configfile = "./python/inference/config.ini"
    cfg.read(configfile)
    sec = cfg.sections()
    if cfg.has_section("server"):
        return cfg.get("server", "server_list")

def read_video_param_from_config():
    cfg = configparser.ConfigParser()
    configfile = "./python/inference/config.ini"
    cfg.read(configfile)
    sec = cfg.sections()
    if cfg.has_section("video"):
        repeat_switch = cfg.get("video", "repeat_switch")
        task_per_thread = cfg.get("video", "task_per_thread")
        max_concurrency = cfg.get("video", "max_concurrency")
        return int(repeat_switch), int(task_per_thread), int(max_concurrency)

@version_reply.route('/verify/detail', methods=['GET'])
def verify_detail():
    """[获取服务的基本信息]
    请求参数
        无
    Returns:
        [json]: [json格式的信心串]
    """
    result_dic = {
        "result": "success",
        "data": [{
            "availableImageFormats": [
                "jpg",
                "png",
                "bmp"
            ],
            "maxImageFileSize": 16,
            "maxImageLen": 1920
        }],
        "use_time": 0
    }
    return jsonify(result_dic)


@version_reply.route('/verify/version', methods=['GET'])
def verify_version():
    """[获取服务的版本信息]
    请求参数
        无
    Returns:
        [json]: [json格式的版本信息, e.g.]
        {
            "server_http": "1.2.1",
            "picasso_sdk": "2.0.01.210122",
            "model": {
                "sem_seg_server": "v2.0.1",
                ...
                "smoke_fire_server": "v1.0.0",
                "grid_slag_server": "v0.1.0",
                "dosing_server": "v0.1.0"
            }
        }
    """
    try:
        # cfg = configparser.ConfigParser()
        # configfile = "./python/inference/config.ini"
        # cfg.read(configfile)
        # sec = cfg.sections()
        # createHandleAndGetVersionInfo(cfg)
        v_js = dict()
        v_js.update(base_version())
        v_js["model_info"] = []
        for i in range(len(engines)):
            # 过滤pt_feature_server以及person_proc_server
            if engines[i]["name"] and engines[i]["version"] and engines[i]["description"]:
                # print(f'engines: {engines[i]}')
                v_js["model_info"].append(engines[i])

        result_js = json.dumps(v_js)
    except Exception as ex:
        logger.error("Get Version error: %s"%str(ex))
        result_js = error_result_js
        result_js['Exception'] = str(ex)
        result_js = json.dumps(result_js)
    return result_js
    
# @version_reply.route('/verify/list', methods=['GET'])
# def list_support():
#     # TODO: 根据注册信息列出支持的引擎，以及引擎支持的所有三段式 url 列表
#     # [可选] GET URL 返回帮助信息，用于接口文档的自动维护，便于定位以及调试

#     try:
#         v_js = dict()
#         v_js["servers"] = ';'.join([engine for engine in engines])
#         v_js["urls"] = ';'.join(list(engine_instance.__opt_map__.keys()))

#         for engine in engines:
#             v_js[engine["name"]] = ';'.join(list_urls(e.opt_map))

#         result_js = json.dumps(v_js)
#     except Exception as ex:
#         logger.error("Get Version error: %s"%str(ex))
#         result_js = error_result_js
#         result_js['Exception'] = str(ex)
#         result_js = json.dumps(result_js)
#     return result_js



@version_reply.route('/server/licence/generate', methods=['POST'])
def licence_generate():
    """[获取本机的机器码的接口，请将返回的机器码提供给运维人员生成本机的授权码]
    请求参数
        无
    Returns:
        [json]: [机器码信息或者错误信息]
    成功
        {
            "code": 200,
            "data": {
                "serial_number": "yfjSh+yKS/wDZSvOHYs1S/imOiyBDID9rbUBnniCG85DKxwJ7XZWTR2yU6PipDWI+DaFSuRRkBwtOr6HzqCw6496pywDb7fNUwNV2r+ZxfrT+YTKfap2TRg2H1TvvjOc3JbAsxds9XnJWmkvZt8JAGJk5FzXc1x9vMu93taQ9ew7hLdDJ/oh94RRThERKcQrxXJnpN4qO/3V5Xb6wIpAqw=="
            },
            "result": "success"
        }
    """
    try:
        result_js = generate_licence()
    except Exception as ex:
        logger.error("Licence Code Generate Exception: %s" % str(ex))
        result_js = error_result_js
        result_js['Exception'] = str(ex)
        result_js = json.dumps(result_js)
    return result_js


@version_reply.route('/server/licence/check', methods=['POST'])
def licence_check():
    """[授权码验证]
    请求参数
        licence: base64 编码的授权码
    Returns:
        [json]: [授权的基本信息]
    成功
        {
            "code": 200,
            "data": {
                "enable_servers": ["ENABLE_PERSON", "ENABLE_COMMON"],
                "expired": "2021-12-31",
                "register_status": "success",
                "sign": "e0a21b54fe7413c57098be5cd77a57a3"
            },
            "result": "success"
        }
    失败
        {
            "code": 200,
            "data": {
                "register_status": "unregistered"
            },
            "result": "failed"
        }
    """
    try:
        param_str = parse_argument(request, ["licence"])
        licence_serial = param_str["licence"]

        server_list_old = read_server_enable_from_config().split(";")
        repeat_switch, task_per_thread, max_concurrency = read_video_param_from_config()

        result_js = check_licence(licence_serial)
        js = json.loads(result_js)

        # 授权码校验通过，则自动更新配置文件中的授权码，并启动相关的服务
        if js["data"]["register_status"] == "success":
            save_licence_to_config(licence_serial)
            server_enable_new = list(js["data"]["enable_servers"])
            server_list_new = []
            for server_enable in server_enable_new:
                server_list_new.append(server_enable.replace("ENABLE_", "").lower() + "_server")
            server_list_new.append("video_server")
            server_list_new.append("pt_feature_server")
            if gv.get_value('handle_flag') == False:
                picasso_create_engines(licence_serial, server_list_new, repeat_switch, task_per_thread, max_concurrency)
                gv.set_value('handle_flag', True)
            else:
                new_diff = list(set(server_list_new).difference(set(server_list_old)))
                if new_diff is not None:
                    picasso_create_engines(licence_serial, new_diff, repeat_switch, task_per_thread, max_concurrency)
            
                old_diff = list(set(server_list_old).difference(set(server_list_new)))
                if old_diff is not None:
                    for old_server in old_diff:
                        if len(old_server) > 0 and server_handle_dict.get(old_server) is not None:
                            destroy_server_handle(old_server)
                            print("destroy_handle: {}".format(old_server))

    except Exception as ex:
        logger.error("Licence Check error: %s"%str(ex))
        result_js = error_result_js
        result_js['Exception'] = str(ex)
        result_js = json.dumps(result_js)
    return result_js
