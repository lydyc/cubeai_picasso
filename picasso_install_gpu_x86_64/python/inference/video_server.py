#!/usr/bin/env python
# coding: utf-8
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: video_server.py
 * @brief: 
 * @version 1.0
 * @date 2020/4/8
"""

from datetime import datetime, timedelta
from pickle import TRUE
from .common import _LIB, logger, parse_argument, VideoHandle, VideoTaskTxt, VideoTask
from ctypes import *
import json
import os
import threading

# 创建一个锁对象
lock = threading.Lock()
#主要用于统计实时任务请求状态
real_task_state = {}
#处理实时、轮询请求的数据
#params:dict,video_task:任务请求状态,task_mode:任务类型（轮询/实时）
def local_file_process(params, task_mode, video_task):
    filename = "./python/inference/request_task_file.json"
    global real_task_state
    task_id = params["task_id"] if "task_id" in params else ""

    exist_flag = False #判断当前任务是否已经存在，防止多次写入
    usable_list = []   #用于保存删除后的数据
    with lock:
        try:
            with open(filename,'r') as f:   #先判断当前文件中是否包含该任务
                for line in f.readlines():
                    try:
                        data = json.loads(line)
                        current_task_id = data['task_id'] if 'task_id' in data else ""   #取出task_id字段
                        if task_id == current_task_id:
                            exist_flag = True
                            continue
                    except ValueError:
                        continue
                    usable_list.append(line)
        except IOError:
            return

        #实时任务经过两个步骤则保存任务
        if (task_mode==1 and (task_id in real_task_state) and real_task_state[task_id]==2 and exist_flag==False):
            with open(filename,"a+") as f:
                f.write(json.dumps(params) + "\n")
                del[real_task_state[task_id]]
        #轮询任务保存
        if (task_mode==0 and video_task==VideoTask.CREATE_TASK and exist_flag==False):
            with open(filename,"a+") as f:
                f.write(json.dumps(params) + "\n")
        #任务请求状态为DELETE_TASK时，删除任务
        if video_task==VideoTask.DELETE_TASK and os.path.exists(filename):
            with open(filename,"w+") as f:
                f.writelines(usable_list)
        #关闭文件        
        f.close()

# 计算时间
def calculate_offset_time(time_str, offset):
    try:
        # 将时间字符串转换为 datetime 对象
        time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # 格式不正确，返回空字符串
        return ""

    # 计算偏移后的时间
    offset_time = time_obj + timedelta(seconds=offset)
    # 返回偏移后的时间字符串
    return offset_time.strftime('%Y-%m-%d %H:%M:%S')

class VideoServer:
    def __init__(self):
        self.status = False
        self.video_handle = None
        self.param = True
        self.repeat_switch = False

    def __del__(self):
        if self.video_handle is not None:
            handle_destroy = _LIB.mvVideoHandleDestroy
            handle_destroy.restype = c_int
            status = handle_destroy(self.video_handle)
            if status != 0:
                raise Exception("Destroy Server Error.")

    def create_server_handle(self, decode_dv, licence, repeat_switch, task_per_thread, max_concurrency):
        if decode_dv is None or licence is None:
            logger.warning("video_server init failed!")
            self.status = False
            return
        licence = c_char_p(licence.encode('utf-8'))
        decode_dv = c_char_p(decode_dv.encode('utf-8'))
        task_per_thread = c_int(task_per_thread)
        max_concurrency = c_int(max_concurrency)
        if self.video_handle is None:
            self.video_handle = POINTER(VideoHandle)()
            handle_creator = _LIB.mvVideoHandleCreate
            handle_creator.restype = c_int

            status = handle_creator(byref(self.video_handle), licence, decode_dv, task_per_thread, max_concurrency)

            if status != 0:
                self.status = False
                self.video_handle = None
                logger.error("video_server init failed!")
            else:
                self.repeat_switch = repeat_switch
                self.status = True

    def video_process(self, data_stream, video_task):
        if not self.status or self.video_handle is None:
            logger.error("Not Support Video Process!")
            res = {"code": 500,
                   "result": "error",
                   "error_message": "Not Support"}
            return json.dumps(res)
        keys = ["task_id", "source_url", "result_url", "streaming_media_type", "task_mode", \
                "task_type", "interval", "precise_interval", "skip_frame_sec", "encoder_type", \
                "track_flag", "frame_frequency","start_time", "time_offset"]

        #如果是从文件中读取的，则为字典形式，不需要进行解析
        if isinstance(data_stream,dict):
            params = data_stream
        else:#直接从requests请求中解析
            params = parse_argument(data_stream, keys)
            #获取当前任务类型为实时还是轮询
            curr_task_mode = int(params["task_mode"]) if "task_mode" in params else 0
            #获取当前任务id
            curr_task_id = params["task_id"] if "task_id" in params else ""
            global real_task_state
            #实时任务需要经过create和start两个步骤，需要统计状态
            if curr_task_mode == 1 and video_task == VideoTask.CREATE_TASK:
                real_task_state[curr_task_id] = 1
            if curr_task_mode == 1 and video_task == VideoTask.START_TASK:
                if curr_task_id in real_task_state and real_task_state[curr_task_id] == 1 :
                    real_task_state[curr_task_id] = 2
            local_file_process(params, curr_task_mode, video_task)
        
        task_id = params["task_id"] if "task_id" in params else ""
        in_url = params["source_url"] if "source_url" in params else ""
        out_url = params["result_url"] if "result_url" in params else ""
        task_type = params["task_type"] if "task_type" in params else ""
        video_type = int(params["streaming_media_type"]) if "streaming_media_type" in params else 0
        task_mode = int(params["task_mode"]) if "task_mode" in params else 0
        interval = int(params["interval"]) if "interval" in params else 1
        precise_interval = str(params["precise_interval"] if "precise_interval" in params else "")
        skip_frame_sec = int(params["skip_frame_sec"]) if "skip_frame_sec" in params else 0
        encoder_type = params["encoder_type"] if "encoder_type" in params else ""
        track_flag = str(params["track_flag"]) if "track_flag" in params else "0" #默认关闭跟踪
        start_time = str(params["start_time"]) if "start_time" in params else "" #针对离线视频，给定视频文件的实际起始时间
        frame_frequency = float(params["frame_frequency"]) if "frame_frequency" in params else 0 #抽帧频率
        time_offset = int(params["time_offset"]) if "time_offset" in params else 0 #起始时间偏移值
        new_start_time = calculate_offset_time(start_time, time_offset)

        repeat_switch = int(self.repeat_switch)
        if encoder_type == "H264":
            encoder_type = 0
        elif encoder_type == "H265":
            encoder_type = 1
        else:
            encoder_type = 2

        processor = _LIB.mvRtspVideoTaskProcess
        processor.restype = c_int

        result_str = c_char_p()
        status = processor(self.video_handle, video_task, c_char_p(task_id.encode('utf-8')), 
                c_char_p(in_url.encode('utf-8')), c_char_p(out_url.encode('utf-8')), c_int(video_type), 
                c_int(encoder_type), c_char_p(task_type.encode('utf-8')), c_int(task_mode), 
                c_int(interval), c_char_p(precise_interval.encode('utf-8')), c_int(repeat_switch), 
                c_float(skip_frame_sec), byref(result_str), c_char_p(track_flag.encode('utf-8')), 
                c_char_p(new_start_time.encode('utf-8')), c_float(frame_frequency))

        res = str(result_str.value, encoding='utf-8')
        if status != 0:
            logger.error("Video Task Executed Failed: {} {} {}".format(VideoTaskTxt[video_task], params, res))
        destroy_res = _LIB.mvDestroyResult
        destroy_res.restype = c_int
        status = destroy_res(result_str)
        if status != 0:
            logger.error("Destroy Result Error!")
        return res
