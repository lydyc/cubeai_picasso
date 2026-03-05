#!/bin/bash

<< readme
服务启停脚本
  Usage: vae_server {start|stop|restart|status}
依赖变量:
  server_ps_str: 程序启动命令
readme

SCRIPT_DIR=$(cd $(dirname $0); pwd)

# 依赖库路径
unset LD_LIBRARY_PATH
export LD_LIBRARY_PATH=${SCRIPT_DIR}/lib
# 模型配置文件路径
unset PICASSO_MODEL_PATH
export PICASSO_MODEL_PATH=${SCRIPT_DIR}/model/configs
# 组合服务配置文件路径
unset PICASSO_SERVER_PATH
export PICASSO_SERVER_PATH=${SCRIPT_DIR}/server/config
# config.ini文件路径
unset PICASSO_CONFIG_PATH
export PICASSO_CONFIG_PATH=${SCRIPT_DIR}/python/inference/config.ini
export PYTHONPATH=${SCRIPT_DIR}/python:${SCRIPT_DIR}/python/verify_server:${SCRIPT_DIR}/python/inference:${SCRIPT_DIR}/python/restful
# glog日志等级：0-INFO,1-WARNING,2-ERROR, 3-FATAL
export GLOG_minloglevel=0
# int，指定日志文件最大size，超过会被切割，单位为MB
GLOG_max_log_size=100
# 请求任务信息保存路径
export REQUEST_TASK_FILE=${SCRIPT_DIR}/python/inference/request_task_file.json

start() {
    echo "start server ..."
    mkdir -p ./log
    pid=`ps -ef|grep "uwsgi --ini python/uwsgi.ini"| grep -v grep | awk '{print $2}'`
    if [ -n "${pid}" ];then
        echo "vae_server is runing. Pid is ${pid}"
    else
        uwsgi --ini python/uwsgi.ini
    fi
}

stop() {
    echo "stop vae server ..."
    pid=`ps -ef|grep "uwsgi --ini python/uwsgi.ini"| grep -v grep | awk '{print $2}'`
    for i in $pid
    do
        rm -rf $REQUEST_TASK_FILE
        echo "Kill the $1 process [ $i ]"
        kill -9 $i
    done
}

restart(){
    stop
    sleep 2s
    start
}

autorestart(){
  echo "auto restart picasso server ..."
  pid=`ps -ef|grep "uwsgi --ini python/uwsgi.ini"| grep -v grep | awk '{print $2}' | sort -n -r | head -n 1`
  echo "pid [ $pid ]"
  kill -9 ${pid}
}

status() {
    pid=`ps -ef|grep "uwsgi --ini python/uwsgi.ini"| grep -v grep | awk '{print $2}'`
    if [ -n "${pid}" ];then
        echo "vae_server is running. Pid is ${pid}"
    else
        echo "vae_server is not running."
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: vae_server {start|stop|restart|status}"
esac
