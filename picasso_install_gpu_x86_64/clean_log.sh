#!/bin/sh
if [ -z $atlantis_install_dir ];   then
    echo "source /etc/profile.d/vae.sh"
    source /etc/profile.d/vae.sh
fi
log_path=$atlantis_install_dir/picasso_install_gpu_x86_64/log/
if [ ! -d ${log_path} ]; then
    echo "${log_path} not exist!"
else
    find ${log_path} -name picasso_* -mtime +3 |xargs rm -rf {} 
    find ${log_path} -name server.log.* -mtime +3 |xargs rm -rf {} 
fi
