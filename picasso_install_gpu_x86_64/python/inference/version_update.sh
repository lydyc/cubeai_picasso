#!/bin/bash

# get current path
picasso_old_path=$(pwd)
#picasso_old_path="${picasso_old_path}/picasso_install_gpu_x86_64/"

# get command line arguments
picasso_new_path=$1

model_file="${picasso_new_path}/model_install.sh"
server_file="${picasso_new_path}/server.sh"
conf_file="${picasso_new_path}/python/inference/config.ini"

# check whether the path exists
if [ -d "${picasso_new_path}" ]; then
    echo "new picasso path exists"
    cd $picasso_new_path
    if [ -e "$model_file" ]; then
        echo "the file: model_install.sh exists"
    else
        echo "the file: model_install.sh dose not exists"
        return -3
    fi
    if [ -e "$server_file" ]; then
        echo "the file: server.sh exists"
    else
        echo "the file: server.sh dose not exists"
    fi
    if [ -e "$conf_file" ]; then
        echo "the file: config.ini exists"
    else
        echo "the file: config.ini dose not exists"
    fi
else
    echo "new picasso path does not exist"
    return -1
fi

# get the parent directory of current directory
#picasso_parent_path="$(dirname "$(pwd)")"#output error
picasso_parent_path="$(dirname ${picasso_old_path})"

echo "******************************"
echo "${picasso_old_path}"
echo "${picasso_parent_path}"
echo "${picasso_new_path}"
echo "******************************"

# step1 : cp config.ini
echo "---------------------step1---------------------------"
if [ -e "${picasso_old_path}/python/inference/config.ini" ] && [ -d "${picasso_new_path}/python/inference/" ]; then
    \cp "${picasso_old_path}/python/inference/config.ini" "${picasso_new_path}/python/inference/"
else
    echo "config.ini file does not exist"
    return -2
fi

#step2 : cp request_task_file.json
echo "---------------------step2---------------------------"
if [ -e "${picasso_old_path}/python/inference/request_task_file.json" ]; then
    \cp "${picasso_old_path}/python/inference/request_task_file.json" "${picasso_new_path}/python/inference/"
else
    echo "request_task_file.json does not exist"
fi

# step3 : install models
echo "---------------------step3---------------------------"
if [ -e "${picasso_new_path}/model_install.sh" ]; then
    cd "${picasso_new_path}"
    sh model_install.sh
else
    echo "Mode install script file does not exist"
    return -3
fi

#step4 : backup old picasso and stop server
echo "---------------------step4---------------------------"
tar -zcvf "${picasso_parent_path}/picasso_install_gpu_x86_64_backup.tar.gz" "${picasso_old_path}"
mv "${picasso_old_path}" "${picasso_parent_path}/picasso_install_gpu_x86_64_backup"
cd "${picasso_parent_path}/picasso_install_gpu_x86_64_backup"
sh server.sh stop
sleep 2s

#step5 : mv new picasso directory to old picasso_new_path and start server
echo "---------------------step5---------------------------"
mv "${picasso_new_path}" "${picasso_parent_path}"
cd "${picasso_parent_path}/picasso_install_gpu_x86_64"
#mv "${picasso_parent_path}/picasso_install_gpu_x86_64_backup/log/" "${picasso_parent_path}/picasso_install_gpu_x86_64"
sh server.sh start

