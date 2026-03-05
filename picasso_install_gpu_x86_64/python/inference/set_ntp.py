import ntplib
import time
import datetime
import configparser
import os

#ntp时钟同步
def set_ntp_process():
    """
    通过ntp server获取网络时间
    :param ntp_server_url: 传入的服务器的地址
    :param port: 端口号
    :param time_interval: 同步的时间间隔
    :return: time.strftime()格式化后的时间和日期
    """

    ntp_server_url = ""
    port = 123
    time_interval = 3600

    while True:
        #读文件，获取ntp参数
        conf = configparser.ConfigParser()
        configfile = "./python/inference/ntp_conf.ini"
        conf.read(configfile)
        if conf.has_section("ntp_server"):
            if len(conf["ntp_server"]["addr"]) > 0:
                ntp_server_url = conf["ntp_server"]["addr"]
                print("ntp_server_url: ",ntp_server_url)
        if conf.has_section("ntp_port") and len(conf["ntp_port"]["port"]) > 0:
            port = int(eval(conf["ntp_port"]["port"]))
            print("port: ",port)
        if conf.has_section("check_interval") and len(conf["check_interval"]["interval"]) > 0:
            time_sec = int(eval(conf["check_interval"]["interval"]))
            print("time_sec: ",time_sec)
            time_interval = time_sec* 60
        
        #设置ntp同步
        ntp_client = ntplib.NTPClient()
        try:
            #获取网络时间
            ntp_stats = ntp_client.request(ntp_server_url,port=port)
            ntp_server_time = time.strftime('%X', time.localtime(ntp_stats.tx_time))
            ntp_server_date  = time.strftime('%Y-%m-%d', time.localtime(ntp_stats.tx_time))
            print("ntp_server_time:---",ntp_server_time)
            print("ntp_server_date:---",ntp_server_date)
            #设置时间
            os.system('date -s \"{} {}\"'.format(ntp_server_date, ntp_server_time))
            #将2个{}放在一个字符串中当成一个整体，输入2个参数：日期和时间
        except ntplib.NTPException as e:
            print(f"NTP exception: {e}")
        
        # 休眠时间
        time.sleep(time_interval)

set_ntp_process()

    #通过os.system来设置时间,需要管理员权限
    # 设置系统时间
        # 注意：设置系统时间需要管理员权限，可能需要使用 sudo 运行脚本
        # 请确保你有足够的权限来设置系统时间

        # 使用 time 模块设置系统时间
        # 由于 time 模块使用的是自纪元以来的秒数，需要将服务器时间转换为秒数
        # 注意：这将改变整个系统的时间，谨慎使用


