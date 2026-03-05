#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: authenticate.py
 * @brief: 
 * @version 1.0
 * @date 2021/7/22
"""

import threading
import os
import time
import requests
import base64
import json
from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from . import global_var as gv
from . import server_list, device
from .picasso import *
from .video_server import VideoServer
from .common import logger, authenticate_error_code, _LIB
from ctypes import *

__all__ = ['Authenticate']

video_server = VideoServer()
server_list.append("video_server")  # server_list增加 video_server

licence = "Y2xvdWRfc2VydmVy"  # cloud_server base64编码结果
private_key_data = ""
public_key_data = ""

with open('./key/authenticate_public.pem', 'rb') as f:
    public_key_data = f.read()

with open('./key/picasso_private.pem', 'rb') as f:
    private_key_data = f.read()

# 公钥加密
def rsa_encode(message, public_key):
    rsakey = RSA.importKey(public_key)  # 导入读取到的公钥
    cipher = PKCS1_v1_5.new(rsakey)  # 生成对象
    # 通过生成的对象加密message明文，注意，在python3中加密的数据必须是bytes类型的数据，不能是str类型的数据
    cipher_text = base64.b64encode(cipher.encrypt(bytes(message.encode(encoding="utf-8"))))
    # 公钥每次加密的结果不一样跟对数据的padding（填充）有关
    return cipher_text.decode()

# 私钥解密
def rsa_decode(cipher_text, private_key):
    rsakey = RSA.importKey(private_key)  # 导入读取到的私钥
    cipher = PKCS1_v1_5.new(rsakey)  # 生成对象
    # 将密文解密成明文，返回一个bytes类型数据，需要自行转换成str
    text = cipher.decrypt(base64.b64decode(cipher_text), "ERROR")
    return text.decode()

# 鉴权线程入口函数
def authenticate_picasso(_url, _id):
    # 请求url
    REST_AUTHENTICATE_URL = 'http://{0}/aiss/picasso/request/authorize/verify'.format(_url)
    data = {'licenceId': _id}
    headers = {'sign': ''}

    while True:
        print('[INFO] -- Authenticate Start <{}>'.format(REST_AUTHENTICATE_URL))
        res = requests.post(REST_AUTHENTICATE_URL, data=data, headers=headers)
        res_data = res.json()
        
        authen_flag = False
        if res.status_code == 200:
            print("[INFO] -- Authenticate Request OK: {}".format(json.dumps(res_data).encode(encoding="utf-8")))
            uuid_str = res.headers.get('token')
            if uuid_str is not None:
                # print('uuid_str:{}'.format(uuid_str))
                decrypt_uuid = rsa_decode(uuid_str, private_key_data)
                sign_update = {'licenceId':_id, 'uuid':decrypt_uuid}
                sign_str = rsa_encode(json.dumps(sign_update), public_key_data)
                headers.update({'sign': sign_str})
                authen_flag = True
            else:
                raise RuntimeWarning('Get Error Token!')
        else:
            err_message = authenticate_error_code[res['code']] if 'code' in res else 'Unkonw Error'
            raise RuntimeError(err_message)

        cloud_licence = _LIB.mvSetCloudLicence
        cloud_licence.restype = c_int
        cloud_licence(c_bool(authen_flag))
        
        for server_id in server_list:
            if server_id in ["video_server"]:
                video_server.create_server_handle(device[0], licence)
            else:
                create_image_server_handle(server_id, licence, "", "", device[0])
            print("init_handle: {}".format(server_id))

        print("activate init_server with device: {0} and licence: {1}".format(device[0], licence))
        gv.set_value('handle_flag', True)
        time.sleep(60*10) # 每隔10min鉴权一次


class Authenticate:
    def __call__(self, server_url, licence_id):
        self.server_url = server_url
        self.licence_id = licence_id
        authe_th = threading.Thread(target=authenticate_picasso, args=(self.server_url, self.licence_id))
        authe_th.setDaemon(False)
        authe_th.start()


if __name__ == '__main__':
    authenticate = Authenticate()
    authenticate()
