#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2019-4-23

export PICASSO_MODEL_PATH=/data/share/lyc/picasso_v2.0/build_debug/picasso_install_gpu_x86_64/model/configs
export PICASSO_SERVER_PATH=/data/share/lyc/picasso_v2.0/build_debug/picasso_install_gpu_x86_64/server/config
python python/restful_framework.py

@author: Shao Xinqing 0049003134
"""

from restful.app import app
from inference.common import sys_logger 
import sys
import logging
from inference.log_clear import LogClear
from inference.authenticate import Authenticate
import configparser

log_clear = LogClear()
log_clear()

server_url = ""
licence_id = ""

# 解析配置文件，并读取节点信息
conf = configparser.ConfigParser()
configfile = "./python/inference/config.ini"
conf.read(configfile)
sec = conf.sections()

# 读取配置文件中cloud_server_licence节点信息，启动鉴权服务
if conf.has_section("cloud_server_licence"):
    if len(conf["cloud_server_licence"]["server_url"]) > 0:
        server_url = conf["cloud_server_licence"]["server_url"]
    if len(conf["cloud_server_licence"]["licence_id"]) > 0:
        licence_id = conf["cloud_server_licence"]["licence_id"]
    authenticate = Authenticate()
    authenticate(server_url, licence_id)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        p = int(sys.argv[1])
    else:
        p = 9010

    app.run(host='0.0.0.0', port=p, threaded=True)

else:
    # 如果不是直接运行，则将日志输出到 sys 中
    sys_logger = logging.getLogger(sys_logger)
    app.logger.handlers = sys_logger.handlers
    app.logger.setLevel(sys_logger.level)
    app.logger.info("Server is Already.....")