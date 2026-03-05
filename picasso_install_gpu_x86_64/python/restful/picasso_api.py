#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
 * @file: picasso_api.py
 * @brief: 图像服务接口
 * @version 1.0
 * @date 2020/4/8
"""

from flask import Blueprint, request
from inference.common import parse_argument, sys_logger, cost_record
from inference.picasso import *
import logging

picasso_api = Blueprint("picasso_api", __name__)

logger = logging.getLogger(sys_logger)


@picasso_api.route('/picasso/image/inference', methods=['POST'])
@cost_record(logger.info)
def picasso_process():
    """[通用图像分析请求接口]
    请求参数:
        image_data: 图像数据
        rect:       检测区域[left, top, right, bottom]
        task_type:  分析任务,server_type1:task_type1;server_type2:task_type2;
        reverse_rect: 反向电子围栏:1;电子围栏:0
    """
    param = parse_argument(request, ['image_data', 'rect', 'task_type','reverse_rect'])
    res = '{"result": "failed", "code": 400, "error_message": "INVALID_ARGUMENTS"}'
    '''
    if param is None or param["task_type"] is None or len(param["task_type"]) <= 0:
        return res
    id_type = param['ID_type'] if 'ID_type' in param else -1
    if param["task_type"] == "identification_server" and (id_type is not None):
        if id_type < 0 or id_type > 1:
            return res
    if id_type is None or id_type is '':
        id_type= -1
    '''
    image_stream = param["img_data"]
    name_list = param["img_name"]
    if len(image_stream) <= 0:
        res = '{"result": "failed", "code": 400, "error_message": "WITHOUT_FILE"}'
        return res

    rect_p = param['rect'] if 'rect' in param else None
    rect_num = len(param['rect']) if 'rect' in param else 0
    reverse_rect = int(param['reverse_rect']) if 'reverse_rect' in param else 0

    server_list = []
    servers = param["task_type"].split(";")

    #若输入图像个数大于1时，输入的rect个数必须是1或者0，输入的服务个数必须是一个或者图像个数
    #输入图像等于1时，可输入多个rect，输入格式为：[],[]
    if len(image_stream) > 1:
        if rect_num > 1:
            res = '{"result": "failed", "code": 400, "error_message": "ERROR_RECT_COUNT"}'
            return res
        if len(servers) != len(image_stream) and len(servers) != 1:
            res = '{"result": "failed", "code": 400, "error_message": "ERROR_SERVER_LIST"}'
            return res

    for single_server in servers:
        if len(single_server) > 0:
            server_id_task_type = single_server.split(":")
            if len(server_id_task_type) == 2 and len(server_id_task_type[1]) > 0:
                server_list.append(server_id_task_type[0])
            else:
                res = '{"result": "failed", "code": 400, "error_message": "error_task_type"}'
                return res
    if(rect_p is None):
        rect_p = [[-1,-1,-1,-1]]
    if (len(server_list) > 1) and (len(rect_p) > 1):
        assert len(server_list) == len(rect_p), "task_type num must be 1 or equal to rect num!"
    if (len(server_list) > 1) and (len(rect_p) == 1):
        temp_list = []
        for i in range(len(server_list)):
            temp_list.append(rect_p[0])
        rect_p = temp_list
    if (len(image_stream) > 1) and (len(rect_p) == 1):
        temp_list = []
        for i in range(len(image_stream)):
            temp_list.append(rect_p[0])
        rect_p = temp_list

    for server in server_list:
        if server in ["grid_slag_server", "siphon_server", "dosing_server", "sed_mud_server", "tube_mud_server", "driver_shelter_server", "switch_server", "yaban_server", "indicator_server", "plate_pollute_clas_server", "huxiqi_break_server"]:
            if rect_p is not None:
                for rect in rect_p:
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    width = min(width, height)
                    rect[2] = rect[0] + width
                    rect[3] = rect[1] + width
            else:
                logger.error("{} don't have parameter 'rect'".format(server))
                return res

    c_rect, c_rect_len = covert_c_rect(rect_p)

    # input only support one key
    image_data, lens, num, img_name = covert_image2ctype(image_stream, name_list)

    res = inferenceV2(image_data, lens, num, img_name, c_rect, c_rect_len, param["task_type"], reverse_rect)
    return res

@picasso_api.route('/verify/feature/extract', methods=['POST'])
@cost_record(logger.info)
def feature_extract():
    param = parse_argument(request, ['image_data', 'rect', 'task_type'])
    res = '{"result": "failed", "code": 400, "error_message": "INVALID_ARGUMENTS"}'
    if param is None or \
       param["task_type"] is None or \
       len(param["task_type"]) <= 0 or \
       param["task_type"] not in ["FEATURE_QUERY", "FEATURE_SAVE"]:
        return res
    image_stream = param["img_data"]
    name_list = param["img_name"]
    if len(image_stream) <= 0:
        res = '{"result": "failed", "code": 400, "error_message": "WITHOUT_FILE"}'
        return res

    rect_p = param['rect'] if 'rect' in param else None
    if(rect_p is None):
        rect_p = []
        for i in range(len(image_stream)):
            rect_p.append([-1,-1,-1,-1])
    # rect_p = param['rect'] if 'rect' in param else None
    # if(rect_p is None):
    #     rect_p = [[-1,-1,-1,-1]]
    
    res = pt_feature_extract('pt_feature_extract_server', image_stream, name_list, rect_p, param["task_type"])
    return res

@picasso_api.route('/verify/feature/comparison', methods=['POST'])
@cost_record(logger.info)
def feature_comparision():
    param = parse_argument(request, ['feature1', 'feature2', 'task_type'])
    if param is None or \
       param["task_type"] is None or \
       param["task_type"] not in ["FEATURE_COM"] or \
       param['feature1'] is None or \
       param["feature2"] is None:
        res = '{"result": "failed", "code": 400, "error_message": "INVALID_ARGUMENTS"}'
        return res

    res = pt_feature_match('pt_feature_server', param['feature1'], param['feature2'], param["task_type"])
    return res

@picasso_api.route('/picasso/object_iou_filter', methods=['POST'])
@cost_record(logger.info)
def object_iou_filter():
    param = parse_argument(request, ['base64_img', 'rect_id', 'task_type', 'iou_range'])

    # 图像数据
    image_stream = param['img_data'] if 'img_data' in param else ""
    if len(image_stream) <= 0:
        res = '{"result": "failed", "code": 400, "error_message": "WITHOUT_FILE"}'
        return res
    name_list = param["img_name"]
    image_data, lens, num, img_name = covert_image2ctype(image_stream, name_list)

    # 坐标框
    rect_id = param['rect_id'] if 'rect_id' in param else ""
    if len(rect_id) <=0:
        res = '{"result": "failed", "code": 400, "error_message": "INVALID_ARGUMENTS"}'
        return res
    if isinstance(rect_id, str):
        rect_id_str = rect_id
    elif isinstance(rect_id, list):
        rect_id_str = json.dumps(rect_id)

    # 算法服务,未填则默认为小行人检测
    task_type = param['task_type'] if 'task_type' in param else "tiny_person_dete_server:DETECT"

    # iou范围,若未传入则默认阈值范围为0-1
    iou_range = param['iou_range'] if 'iou_range' in param else [0,1]
    # 转换传入的iou信息
    iou = []
    for i in iou_range:
        iou.append(i)
    c_iou_range_len = len(iou)
    c_iou_range = (c_float * len(iou))(*iou)

    # 推理
    res = object_filter_inference(image_data, lens, num, img_name, rect_id_str, task_type, c_iou_range, c_iou_range_len)
    return res