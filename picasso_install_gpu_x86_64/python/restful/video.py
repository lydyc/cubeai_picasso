#!/usr/bin/env python
# coding: utf-8
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: video.py
 * @brief: 视频服务接口
 * @version 1.0
 * @date 2020/4/8
"""

from flask import Blueprint, request
from inference.common import sys_logger, cost_record, error_result_js, VideoTask
import logging
import json

from inference import video_server

video_reply = Blueprint("video", __name__)

logger = logging.getLogger(sys_logger)

@video_reply.route('/picasso/video/create', methods=['POST'])
@cost_record(logger.info)
def p_create():
    try:
        res_str = video_server.video_process(request, VideoTask.CREATE_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/delete', methods=['POST'])
@cost_record(logger.info)
def p_delete():
    try:
        res_str = video_server.video_process(request, VideoTask.DELETE_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/start', methods=['POST'])
@cost_record(logger.info)
def p_start():
    try:
        res_str = video_server.video_process(request, VideoTask.START_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/stop', methods=['POST'])
@cost_record(logger.info)
def p_stop():
    try:
        res_str = video_server.video_process(request, VideoTask.STOP_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/read', methods=['POST'])
@cost_record(logger.info)
def p_read():
    try:
        res_str = video_server.video_process(request, VideoTask.READ_FRAME)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/query', methods=['GET'])
@cost_record(logger.info)
def p_query():
    try:
        res_str = video_server.video_process(request, VideoTask.QUERY_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str


@video_reply.route('/picasso/video/all_task_query', methods=['GET'])
@cost_record(logger.info)
def p_all_task_query():
    try:
        res_str = video_server.video_process(request, VideoTask.ALL_QUERY_TASK)
    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str

@video_reply.route('/picasso/video/queryOfflineTaskStatus', methods=['POST'])
@cost_record(logger.info)
def p_offline_task_query():
    try:
        res_str = video_server.video_process(request, VideoTask.QUERY_OFFLINE_TASK)
        # 获取 POST 请求中的 task_ids 参数，假设其为一个数组
        param_str = {}
        target_task_ids = []
        if request.form:
            param_js = request.form.to_dict()
            param_str.update(param_js)
            task_ids_str = param_str['task_ids']
            target_task_ids = json.loads(task_ids_str)
        if request.data:
            param_js = request.data
            param_js = json.loads(param_js, encoding="utf-8")
            param_str.update(param_js)
            target_task_ids = param_str['task_ids']

        if not target_task_ids:
            pass
        else:
            # 筛选出 task_id 在目标列表中的数据
            res_str = json.loads(res_str)
            filtered_tasks = [task for task in res_str["data"]["tasks"] if task["task_id"] in target_task_ids]
            filtered_data = {
                "code": res_str["code"],
                "data": {
                    "tasks": filtered_tasks
                },
                "result": res_str["result"]
            }
            res_str = json.dumps(filtered_data)

    except Exception as ex:
        logger.error(str(ex))
        res_str = error_result_js
        res_str['Exception'] = str(ex)
        res_str = json.dumps(res_str)
    return res_str


# @video_reply.route('/picasso/video/alive', methods=['POST'])
# @cost_record(logger.info)
# def p_alive():
#     try:
#         res_str = video_server.video_process(request, VideoTask.TASK_ALIVE)
#     except Exception as ex:
#         logger.error(str(ex))
#         res_str = error_result_js
#         res_str['Exception'] = str(ex)
#         res_str = json.dumps(res_str)
#     return res_str


# @video_reply.route('/picasso/video/resume', methods=['POST'])
# @cost_record(logger.info)
# def rt_resume():
#     try:
#         res_str = self.video_server.video_process(request, VideoTask.TASK_RESUME)
#     except Exception as ex:
#         logger.error(str(ex))
#         res_str = error_result_js
#         res_str['Exception'] = str(ex)
#         res_str = json.dumps(res_str)
#     return res_str


# @video_reply.route('/picasso/video/update', methods=['POST'])
# @cost_record(logger.info)
# def rt_update():
#     try:
#         res_str = self.video_server.video_process(request, VideoTask.TASK_UPDATE)
#     except Exception as ex:
#         logger.error(str(ex))
#         res_str = error_result_js
#         res_str['Exception'] = str(ex)
#         res_str = json.dumps(res_str)
#     return res_str

