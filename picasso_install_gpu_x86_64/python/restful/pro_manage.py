#!/usr/bin/env python
# coding: utf-8
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: pro_manage.py
 * @brief: 工程管理接口
 * @version 1.0
 * @date 2023/4/7
"""

from flask import Blueprint, request
from inference.common import sys_logger, cost_record, error_result_js
import logging
import json

from inference import pro_manage_server

manage_project_reply = Blueprint("manage_project", __name__)

logger = logging.getLogger(sys_logger)

@manage_project_reply.route('/picasso/manage_project/meminfo', methods=['GET'])
@cost_record(logger.info)
def p_meminfo():
    try:
        res_str = pro_manage_server.get_meminfo_process()
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@manage_project_reply.route('/picasso/manage_project/restart', methods=['GET'])
@cost_record(logger.info)
def p_restart():
    try:
        res_str = pro_manage_server.pro_restart_process()
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@manage_project_reply.route('/picasso/manage_project/version_update', methods=['POST'])
@cost_record(logger.info)
def p_version_update():
    try:
        res_str = pro_manage_server.pro_version_update_process(request)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@manage_project_reply.route('/picasso/manage_project/model_update', methods=['POST'])
@cost_record(logger.info)
def p_model_update():
    try:
        res_str = pro_manage_server.model_update_process(request)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str