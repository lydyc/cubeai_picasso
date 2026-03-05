#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Created on 2010-3-16

@author: Shao Xinqing 0049003134
"""

from flask import Flask
from .version import version_reply
from .picasso_api import picasso_api
from .video import video_reply
from .pro_manage import manage_project_reply

app = Flask(__name__)

# register restful api
# 接口细节请参考文档: picasso_v2.0/doc/全量解析服务器算法接口文档V2.0.docx
app.register_blueprint(picasso_api)
app.register_blueprint(version_reply)
app.register_blueprint(video_reply)
app.register_blueprint(manage_project_reply)