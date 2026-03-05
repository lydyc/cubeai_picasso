#!/usr/bin/env python
# -*- encoding: utf-8 -*-

"""
    [ Picasso 模型转换与配置文件生成脚本 ]
模型涉及:
    代码仓库 example/model  原始模型
    编译目录 build/example/model/tensorrt   单元测试 ctest 使用的转换后的 tensorrt 模型，执行 create_nv_model.sh 生成
    安装目录 picasso_install_gpu_x86_64/model   发布包下面的 .m 模型文件，存在两个状态
        make install 之后, .m 是原始模型的拷贝
        执行 model_install.sh 现场安装之后, .m 是转换的设备模型( 一般是tensorrt, 与编译目录下相同 )
配置涉及:
    安装目录的 config.ini
    单元测试的 test_config.ini

功能:
1. 将 Onnx/Caffe 模型转为 TensorRT 模型脚本
    依赖工具:
      caffe 模型: ./bin/nvModeDecode -t 1 -m in_onnx_modelfile -b batch_size -e out_TensorRT_modelfile
      onnx 模型: ./bin/nvModeDecode -t 0 -m in_onnx_modelfile -b batch_size -e out_TensorRT_modelfile

    a. 代替原来的 create_nv_model.sh, runc of ctest 使用
        将 example/model 下的 Onnx/Caffe 模型转换为 TensorRT 模型保存到 example/model/tensorrt 下
    b. 代替原来的 model_install.sh, 安装脚本使用
        将安装目录 model 下的模型转换为本地设备使用的引擎模型

2. 生成 config.ini   
    model_helper.py -m -c picasso.cfg

"""

import os, sys, shutil
import subprocess, platform
import argparse
import hashlib
from collections import namedtuple
from string import Template
import configparser
import json
import threadpool
from pynvml import *
import time

def get_file_md5(filename, blocksize=2**20):
    """计算文件的MD5值"""
    if not os.path.isfile(filename):
        return ''

    m = hashlib.md5()
    with open(filename, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update( buf )
    return m.hexdigest().lower()


# 编译环境变量
ROOT_CODE_DIR = ".." # "@ROOT_CODE_DIR@"
SERVER_LIST = "@SERVER_LIST@"   # cmake 配置生成的模型服务列表

# 获取脚本目录和安装目录
script_dir =  os.path.dirname(__file__)
if script_dir.find("picasso_install_gpu_x86_64") >= 0:
    INSTALL_DIR = script_dir
else:
    INSTALL_DIR = "./" # "@INSTALL_DIR@"

# 模型转换工具
CONVERT_TOOL = "./bin/nvModeDecode" # "@CMAKE_BINARY_DIR@/bin/nvModeDecode"

class ModelInfo:
    def __init__(self, engineID, modelCfgFile, srcModelFile, trtModelFile, mModelFile, batchSize, precision, deviceID, suffix):
        self.engineID = engineID
        self.modelCfgFile = modelCfgFile    # 模型配置文件名
        self.srcModelFile = srcModelFile    # 原始文件名
        self.trtModelFile = trtModelFile    # 单元测试使用的 trt 模型文件名
        self.mModelFile = mModelFile        # 安装使用 .m 后缀的文件名 
        self.batchSize = batchSize          # 批大小
        self.precision = precision          # 模型精度
        self.deviceID = deviceID            # 设备
        self.suffix = suffix                # 模型安装命令后缀（特殊的需要:comdet jdwgdet safe_wear reid_yolo）

# 保存engine_id -> ModelInfo 映射，从模型配置文件自动加载，自定义模型（LPR）除外
ModelInfos = {}

def loadJsonDir(file_dir):
    """[summary]  遍历模型配置文件, 获取指定参数添加至 ModelInfos 字典中, 供其它操作使用

    Args:
        file_dir ([string]): [模型配置文件所在路径]
    """
    Model_Infos = {}

    for root, dirs, files in os.walk(file_dir):  
        for file in files:
            file_path = os.path.join(file_dir, file)
            if file_path.endswith(".json"):
                with open(file_path, "r", encoding="utf_8") as fp:
                    info = json.load(fp)

                    engine_id = info.get("engine_id", "")
                    model_cfg_file = engine_id + ".json"
                    src_model_file = info.get("src_model_file", "")
                    trt_model_file = info.get("trt_model_file", "")
                    m_model_file = info.get("m_model_file", "")
                    max_batch_size = info.get("max_batch_size", 1)
                    precision = info.get("precision", 0)
                    deviceID = info.get("infer_device", "GPU:0").split(":")[-1]
                    suffix = info.get("suffix", "")
    
                    model_info = ModelInfo(engine_id, model_cfg_file, src_model_file, trt_model_file, m_model_file, 
                                            max_batch_size, precision, deviceID, suffix)
                    Model_Infos[engine_id] = model_info

    print("ModelInfos support engines: {}".format(Model_Infos.keys()))
    return Model_Infos

def updateModelFile(file_dir, model_list):
    """[summary]  遍历模型配置文件, model_list以外的模型配置文件均删除

    Args:
        file_dir ([string]): [模型配置文件所在路径]
    """
    Model_Infos = {}

    for root, dirs, files in os.walk(file_dir):  
        for file in files:
            file_path = os.path.join(file_dir, file)
            file_name = file.split('.')[0]
            if file_name in model_list and file_path.endswith(".json"):
                continue
            else:
                os.remove(file_path)

def showGpu(simlpe=True):
    #初始化
    nvmlInit()
    #获取GPU个数
    device_num = nvmlDeviceGetCount()
    #GPU是否可用
    device_available = {}
    device_id_available = []

    for i in range(device_num):
        handle = nvmlDeviceGetHandleByIndex(i)
        info = nvmlDeviceGetMemoryInfo(handle)
        if isinstance(nvmlDeviceGetName(handle),bytes):
            gpu_name = nvmlDeviceGetName(handle).decode('utf-8')
        else:
            gpu_name = nvmlDeviceGetName(handle).encode('utf-8').decode('utf-8')
        # 查看型号、显存、温度、电源
        if simlpe:
            total_mem = (info.total//1048576)/1024
            free_mem = (info.free//1048576)/1024
            used_mem = (info.used//1048576)/1024
            mem_rate = info.used/info.total
            template = nvmlDeviceGetTemperature(handle,0)
            print("[ GPU{}: {}  \
                    total memory: {}G  \
                    free memory: {}G  \
                    used memory: {}G  \
                    memory rate: {}%  \
                    template: {} C]".format(i, gpu_name,total_mem,free_mem,used_mem,mem_rate,template))

        #记录GPU及其占用率
        device_available[i] = info.used/info.total
    #按照负载情况排序,负载越轻的越靠前
    device_available = sorted(device_available.items(), key=lambda x: x[1])
    device_available = dict(device_available)
    for i in range(device_num):
        if(device_available[i] <= 0.75):
            device_id_available.append(i)
    #关闭管理工具
    nvmlShutdown()
    return device_id_available

class ModelFileManager:
    # 源模型的本地路径
    localOriginalModelDir = os.path.join(ROOT_CODE_DIR, "example", "model")

    # 源模型转换为m模型的本地保存路径
    mModelDir = os.path.join(INSTALL_DIR, "example", "model", "m")

    # TensorRT模型缓存路径
    trtModelCacheDir = os.path.join("/data", "model_cache")

    # 远程模型下载地址
    remoteModelUrl = ""

    def download(self, modelinfo, localfile):
        """
            将模型下载到本地
        @param modelinfo: 模型信息
        @param localfile: 本地文件
        @return: bool 成功 true, 失败返回 false
        """
        pass


    def localOriginalModel(self, modelinfo):
        """
            获取 onnx 模型本地保存路径
        @param modelinfo: 模型信息
        @return:
        """
        return os.path.join(self.localOriginalModelDir, modelinfo.srcModelFile)

    def localCachemModel(self, modelinfo, modeltype):
        """
            获取 m 模型本地保存路径
        @param modelinfo: 模型信息
        @param modeltype: 模型类型
        @return:
        """
        if not os.path.exists(self.mModelDir):
            print("m model dir don't exist")
            os.makedirs(self.mModelDir)
        if (modeltype == ".onnx"):
            return os.path.join(self.mModelDir, modelinfo.srcModelFile)
        elif (modeltype == ".m"):
            return os.path.join(self.mModelDir, modelinfo.mModelFile)

    def localCacheTrtModel(self, modelinfo, batchSize, srcmodelmd5=""):
        """
            获取 trt 模型本地保存路径
        @param modelinfo: 模型信息
        @param batchSize: 批大小
        @param srcmodelmd5: 原始模型的md5, 支持自动检测原始文件的变换
        @return:
        """
        if not os.path.exists(self.trtModelCacheDir):
            os.makedirs(self.trtModelCacheDir)
        filename = modelinfo.trtModelFile
        if len(srcmodelmd5) > 0:
            filename = srcmodelmd5 + "_" + filename
        return os.path.join(self.trtModelCacheDir, filename)

    def convert2Trt(self, modelinfo, batchSize=-1):
        """
            调用自定义模型转换工具 nvModeDecode 将原始模型转换为 tensorRT 模型
        """
        try:
            batchSize = batchSize if batchSize > 0 else modelinfo.batchSize
            srcmodel = self.localOriginalModel(modelinfo)
            filemd5 = get_file_md5(srcmodel)
            dstmodel = self.localCacheTrtModel(modelinfo, batchSize, filemd5)
            suffix = modelinfo.suffix

            if os.path.exists(dstmodel):
                print("[{}] has already exist".format(dstmodel))
                return 0
            else:
                if srcmodel.endswith(".onnx"):  # onnx to trt
                    command = "{} -t 0 -m {} -b {} -e {} {}".format(CONVERT_TOOL, srcmodel, batchSize, dstmodel, suffix)
                elif srcmodel.endswith(".caffemodel"):  # caffe to trt
                    command = "{} -t 1 -m {} -b {} -e {} {}".format(CONVERT_TOOL, srcmodel, batchSize, dstmodel, suffix)
                elif srcmodel.endswith(".xml"):  # lpr.xml
                    return
                else: # other model now can't be converted
                    print("[{}] can't be converted with convert tool".format(srcmodel))

                print("Running ", command)
                retcode = subprocess.call(command, shell=True)
                return retcode
        except OSError as e:
            return "Execution failed: ", e

    def mModelInstall(self, ModelInfo, modelfile, deviceID, batchSize=-1):
        """
            调用自定义模型转换工具 nvModeDecode 转换模型，默认替换模型文件，即保持文件名不变
            
        """
        try:
            batchSize = batchSize if batchSize > 0 else ModelInfo.batchSize

            model_type = ModelInfo.srcModelFile.split(".")[-1]
            precision = 0
            #precision = ModelInfo.precision
            # deviceID = ModelInfo.deviceID
            suffix = ModelInfo.suffix
            #获取可用GPU设备
            device_id_available = showGpu(False)
            if deviceID not in device_id_available:
                deviceID = device_id_available[0] #使用负载最轻的设备进行转换

            if model_type == "onnx":  # install m model, src model is .onnx
                command = "{} -t 0 -m {} -b {} -p {} -gpu {} {}".format(CONVERT_TOOL, modelfile, batchSize, precision, deviceID, suffix)
            elif model_type == "caffemodel":  # install m model, src model is .caffemodel
                command = "{} -t 1 -m {} -b {} -p {} -gpu {} {}".format(CONVERT_TOOL, modelfile, batchSize, precision, deviceID, suffix)
            elif model_type == "xml":  # lpr.xml
                return
            else: # other model now can't be converted
                print("[{}] can't be intalled with convert tool".format(modelfile))

            print("Running ", command)
            retcode = subprocess.call(command, shell=True)
            return retcode
        except OSError as e:
            return "Execution failed: ", e


class ConfigFileHelper:
    server_model_map = {
        "ENABLE_FACE": ["FaceDete", "FaceFeat", "FaceAttr"],
        "ENABLE_LITE_FACE": ["LiteFaceDete", "FaceFeat", "FaceAttr"],
        "ENABLE_FACE_INFRARED": ["FaceDete", "FaceInfraredFeat", "FaceAttr"],
        "ENABLE_LITE_FACE_INFRARED": ["LiteFaceDete", "FaceInfraredFeat", "FaceAttr"],
        "ENABLE_PERSON": ["PersonDete", "PersonFeat", "PersonAttr"],
        "ENABLE_VEHICLE": ["VehicleDete", "VehicleFeat", "VehicleAttr"],
        "ENABLE_VEHICLE_PLATE": ["VehicleDete", "PlateDete", "PlateReco"],
        "ENABLE_RIDER": ["ReIDYoloDete", "RiderAttr"],
        "ENABLE_DRIVER": ["PersonDete", "DriverAttr"],
        "ENABLE_VEHICLE_DISTANCE": ["VehicleDete", "DistanceReco"],
        "ENABLE_LANE_MARK": ["LaneMarkUser"],
        "ENABLE_SEM_SEG": ["SemSegUser"],
        "ENABLE_PORN": ["PornClas"],
        "ENABLE_COMMON": ["CommonDete"],
        "ENABLE_LPR": ["VehicleDete", "LprXml", "LprAlign", "LprReg"],
        "ENABLE_MUCK_TRUCK": ["MuckTruckDete", "MuckTruckClas"],
        "ENABLE_MUCK_TRUCK_PLATE": ["MuckTruckDete", "PlateDete", "PlateReco"],
        "ENABLE_SAFETY_WEAR": ["PersonDete", "SafetyWearDete"],
        "ENABLE_SAFETY_WEAR_ATTR": ["PersonDete", "SafetyWearAttr"],
        "ENABLE_SMOKE_CALL": ["PersonDete", "SmokeCallDete"],
        "ENABLE_SMOKE_CALL_ATTR" : ["PersonDete", "SmokeCallAttr"],
        "ENABLE_ANIMAL": ["CommonDete"],
        "ENABLE_DOSING": ["DosingClas"],
        "ENABLE_GRID_SLAG": ["GridSlagClas"],
        "ENABLE_IMAGE_QUALITY": ["ImageQualityClas"],
        "ENABLE_STREET_VIOLATE": ["StreetViolateDete"],
        "ENABLE_SMOKE_FIRE": ["SmokeFireDete"],
        "ENABLE_SIPHON": ["SiphonClas"],
        "ENABLE_ENGINE_VEHICLE": ["EngVehicleDete"],
        "ENABLE_BCP_MUD": ["BCPMudSegm"],
        "ENABLE_SED_MUD": ["SedMudClas"],
        "ENABLE_TUBE_MUD": ["TubeMudClas"],
        "ENABLE_COARSE_GRID": ["CoarseGridSegm"],
        "ENABLE_CHAN_OCCU": ["ChanOccuUser"],
        "ENABLE_METER": ["MeterDete", "MeterReco"],
        "ENABLE_PONDING": ["PondingUser"],
        "ENABLE_WATER_LEVEL": ["WaterLevelUser"],
        "ENABLE_DRIVER_SHELTER": ["DriverShelterClas"],
        "ENABLE_NON_VEHICLE": ["NonVehicleDete"],
        "ENABLE_SPECIAL_VEHICLE": ["SpecialVehicleDete"],
        "ENABLE_SWITCH": ["SwitchClas"],
        "ENABLE_SHIP": ["ShipDete"],
        "ENABLE_FLOATAGE": ["FloatageUser"],
        "ENABLE_BREAKER": ["BreakerUser"],
        "ENABLE_ANTIEPIDEMIC_VIOLATE": ["AntiepidemicViolateDete"],
        "ENABLE_ARRESTER_METER": ["ArresterMeterUser"],
        # "ENABLE_TEXT_DETE": ["TextDeteUser"],
        "ENABLE_OCR":["TextDeteUser","TextReco"],
        "ENABLE_IDENTIFICATION":["TextDeteUser","TextReco"],
        "ENABLE_DRIVING_LICENSE":["TextDeteUser","TextReco"],
        "ENABLE_NUMBER":["NumberReco"],
        "ENABLE_ACTION":["ActionReco"],
        "ENABLE_MOUSE":["MouseDete"],
        "ENABLE_YABAN": ["YaBanClas"],
        "ENABLE_ROTATE_HANDLE": ["RotateHandleUser"],
        "ENABLE_CAT_DOG": ["CatDogDete"],
        "ENABLE_INDICATOR" : ["IndicatorLightClas"],
        "ENABLE_PT_FEATURE_EXTRACT" : ["FeatureExtract"],
        "ENABLE_PROTECTIVE_SUIT": ["PersonDete", "ProtectiveSuitAttr"],
        "ENABLE_PLATE_POLLUTE" : ["VehicleDete","PlatePolluteClas"],
        "ENABLE_HUXIQI_COLOR_ABNORMAL" : ["HuxiqiColorAbnormalUser"],
        "ENABLE_HUXIQI_RATIO" : ["HuxiqiRatioUser"],
        "ENABLE_HUXIQI_OIL" : ["HuxiqiOilUser"],
        "ENABLE_THROW_OBJECT" : ["ThrowObjectUser"],
        "ENABLE_HUXIQI_BREAK" : ["HuxiqiBreakClas"],
        "ENABLE_LOESS_UNCOVERED" : ["LoessUncoveredUser"],
        "ENABLE_PERSON_SLEEP_DETECT" : ["PersonSleepDete"],
        "ENABLE_HUOTI_FACE": ["FaceDete", "HuotiClas", "FaceFeat", "FaceAttr"],
        "ENABLE_SCREEN_DETE" : ["ScreenDete"],
        "ENABLE_LOSE_LEGACY" : ["PersonDete", "LoseLegacyReco"],
        "ENABLE_STEEL_DEFECT" : ["SteelDefectUser"],
        "ENABLE_DRINK_WATER" : ["PersonDete","DrinkWaterDete"],
        "ENABLE_DRINK_WATER_CLAS" : ["PersonDete","DrinkWaterAttr"],
        "ENABLE_WATER_STAIN" : ["WaterStainDete"],
        "ENABLE_FIRE_EXTINGUISHER_DETECT" : ["FireExtinguisherDete"],
        "ENABLE_HEAD" : ["HeadDete"],
        "ENABLE_COMPUTER_ROOM_DETE" : ["ComputerRoomDete"],
        "ENABLE_UAV_PERSON_VEHICLE_DETE" : ["UAVPersonVehicleDete"],
        "ENABLE_TRANS_STATION_PATROL" : ["TransStationPatrolDete"],
        "ENABLE_PEOPLE_POSE_DETECT" : ["PeoplePoseDete"],
        "ENABLE_SAFETY_WEAR_ELECTRIC": ["PersonDete", "SafetyWearElectricDete"],
        "ENABLE_RGB_IR_PERSON" : ["RGBIRPersonDete"],
        "ENABLE_HELMET" : ["PersonDete","HelmetDete"],
        "ENABLE_SAFETY_BELT" : ["SafetyBeltDete"],
        "ENABLE_CARTON_DETE" : ["CartonDete"],
        "ENABLE_FALL_DOWN" : ["PersonDete", "FallDownClas"],
        "ENABLE_SALIENCY" : ["SaliencyUser"],
        "ENABLE_CHINA_MOBILE_ASSET_TAG" : ["AssetTagUser", "AssetTagReco"],
        "ENABLE_CARRY_ITEMS" : ["PersonDete","CarryItemsDete"],
        "ENABLE_CABLE_MESSY" : ["CableMessyDete"],
        "ENABLE_GROUND_SANITATION" : ["GroundSanitationDete"],
        "ENABLE_INDICATOR_DETECT" : ["IndicatorDete"],
        "ENABLE_BLIND_PLATE_LOSS_DETECT" : ["BlindPlateLossDete"],
        "ENABLE_SMOKE_FIRE_ENHANCEMENT" : ["SmokeFireEnhancementDete"],
        "ENABLE_TINY_PERSON_DETE" : ["TinyPersonDete"],
        "ENABLE_CHEF_WHITE_DETE" : ["PersonDete", "ChefWhiteDete"],
        "ENABLE_CLOSE_INDICATOR_DETECT" : ["CloseIndicatorDete"],
        "ENABLE_PERSON_CLIMB_DETECT" : ["PersonClimbDete"],
        "ENABLE_FLOOR_COLLAPSE_DETECT" : ["FloorCollapseDete"]
    }

    def __init__(self, cfgFile=""):
        if os.path.exists(cfgFile):
            os.remove(cfgFile)  # 初始化时先移除之前的配置文件

    def addServerList(self, fp, server_macro):
        server_list = ConfigFileHelper.serverMacroToServerList(server_macro)
        servers = ";".join([server for server in sorted(server_list)])
        fp.write("[server]\n")
        fp.write("server_list = {}\n".format(servers))
        fp.write("\n")

        fp.write("[server_all]\n")
        fp.write("server_list_all = {}\n".format(servers))
        fp.write("\n")

    def addDevice(self, fp):
        fp.write("[device]\n")
        fp.write("dv_type = 1;\n")
        fp.write("\n")

    def addLicence(self, fp):
        fp.write("[licence]\n")
        fp.write("serial_num = ")

    def addVideo(self, fp):
        fp.write("[video]\n" + "repeat_switch = 0\n")
        fp.write("task_per_thread = 10\n")
        fp.write("max_concurrency = 50\n")
        fp.write("\n")

    def addCloudServerLicence(self, fp):
        fp.write("[cloud_server_licence]\n")
        fp.write("server_url = \n")
        fp.write("licence_id = ")

    def createConfig(self, server_macro, cfgFile):
        """
            创建配置文件config.ini
        @param serverlist: 服务列表
        @param cfgFile: 输出配置文件的名字
        @return:
        """
        with open(cfgFile, 'w') as fp:
            self.addServerList(fp, server_macro)
            self.addDevice(fp)
            self.addVideo(fp)
            if "ENABLE_CLOUD_SERVER" in server_macro:
                self.addCloudServerLicence(fp)
            else:
                self.addLicence(fp)
        fp.close()

    def modifyModelCfg(self, modelid, srcModelCfgFile, dstModelCfgFile):
        """
            创建新的配置文件
        @param modellist: 模型列表
        @param srcModelCfgFile: 输入配置文件的名字
        @param dstModelCfgFile: 输出配置文件的名字
        @return:
        """

    @staticmethod
    def serverMacroToServerList(server_macro):
        server_list = set()
        for server in server_macro:
            if server.startswith("ENABLE_"):
                server_new = server.replace("ENABLE_", "").lower() + "_server"
                server_list |= set(server_new.split("|"))  # string 转 list 再转 set
        return server_list

    @staticmethod
    def serverMacroToModelList(server_macro):
        model_list = set()
        for server in server_macro:
            if server in ConfigFileHelper.server_model_map:
                model_list |= set(ConfigFileHelper.server_model_map[server])
        return model_list


def covert(modellist, dstdir, batch_size=-1):
    """[summary] 模型转换, 由源模型转换为Trt模型
            代替原来的 create_nv_model.sh, runc of ctest 使用
    Args:
        modellist ([string]): [模型列表]
        dstdir ([string]): [目标路径]
        batch_size (int, optional): [批处理大小]. Defaults to -1.
    """
    m = ModelFileManager()

    if not os.path.exists(dstdir):
        print("trt model dir don't exist")
        os.makedirs(dstdir)

    for modelid in modellist:
        modelinfo = ModelInfos[modelid]
        batchSize = batch_size if batch_size > 0 else modelinfo.batchSize

        srcmodel = m.localOriginalModel(modelinfo)
        dstmodel = os.path.join(dstdir, modelinfo.trtModelFile)

        if(os.path.exists(dstmodel)):
            # 存在则返回避免重复转换
            print("[{}] already exist: [{}]".format(modelid, dstmodel))
            continue

        if not os.path.exists(srcmodel):
            success = m.download(modelinfo, srcmodel)

        if os.path.exists(srcmodel):
            filemd5 = get_file_md5(srcmodel)
            localtrtfile = m.localCacheTrtModel(modelinfo, batchSize, filemd5)
            # print("local trt cache file is [{}]".format(localtrtfile))
            if not os.path.exists(localtrtfile):
                # cannot find in cache, then call convert tool
                m.convert2Trt(modelinfo, batchSize)

            if modelinfo.engineID == "LprXml":
                shutil.copy(srcmodel, dstmodel) # lpr_server需要的cascade.xml文件拷贝至tensorrt文件夹下, 并重命名
            else:
                shutil.copy(localtrtfile, dstmodel) # 将传出来的 trt 模型拷贝到指定的目录
            
        else:
            print("Model file not exist: ", srcmodel)    

def mModelInstall(modellist, dstdir, batch_size=-1):
    """[summary]  将安装目录 model 下的模型转换为本地设备使用的引擎模型，保持文件名不变
       代替原来的 model_install.sh, 安装脚本使用

    Args:
        modellist ([type]): [description]
        dstdir ([type]): [description]
        batch_size (int, optional): [description]. Defaults to -1.
    """
    m = ModelFileManager()

    #获取GPU个数及是否可用
    device_id_available = showGpu(True)
    useful_device_num = len(device_id_available)
    #创建线程池
    pool = threadpool.ThreadPool(useful_device_num)
    #获取所有模型信息
    model_info = []

    modeldir = os.path.join(INSTALL_DIR, "model")   # 安装目录下的 model 文件夹
    # print("model dir is {}".format(modeldir))
    idx = 0
    for modelid in modellist:
        mmodelinfo = ModelInfos[modelid]
        batchSize = batch_size if batch_size > 0 else mmodelinfo.batchSize
        srcmodel = os.path.join(modeldir, mmodelinfo.mModelFile)
        # print(srcmodel)
        if not os.path.exists(srcmodel):
            success = m.download(mmodelinfo, srcmodel)

        if os.path.exists(srcmodel):
            # call install tool    
            # m.mModelInstall(mmodelinfo, srcmodel, batchSize) #早期同步写法
            #将m.mModelInstall函数所需的参数列表保存为list
            device_idx= idx % useful_device_num
            device_id = device_id_available[device_idx]
            idx += 1
            tmp_info = [mmodelinfo, srcmodel, device_id, -1]
            model_info.append((tmp_info,None))
        else:
            print("Model file not exist: ", srcmodel)
    
    requests = threadpool.makeRequests(m.mModelInstall, model_info) # 创建任务 
    [pool.putRequest(req) for req in requests] # 加入任务
    pool.wait()

def transform(modellist, dstdir):
    m = ModelFileManager()

    for modelid in modellist:
        model_infos = []
        if modelid in ModelInfos:
            model_infos.append(ModelInfos[modelid])
        elif modelid == "LprXml":
            model_infos.append(ModelInfos["LprXml"])
        elif modelid == "LprAlign":
            model_infos.append(ModelInfos["LprAlign"])
        elif modelid == "LprReg":
            model_infos.append(ModelInfos["LprReg"])
        
        for ml in model_infos:
            # 原始模型本地是否存在
            if os.path.exists(m.localOriginalModel(ml)):
                # m模型路径下是否存在原始模型
                mModelName = os.path.join(m.mModelDir, ml.srcModelFile)
                if not os.path.exists(m.localCachemModel(ml, ".onnx")):
                    os.system('cp %s %s' % (m.localOriginalModel(ml), mModelName))
                    print(mModelName)                
                # transform model
                if os.path.exists(m.localCachemModel(ml, ".onnx")):
                    os.rename('%s' % (m.localCachemModel(ml, ".onnx")), '%s' % (m.localCachemModel(ml, ".m")))

if __name__ == '__main__':
    # 参数解析: 
    ap = argparse.ArgumentParser()

    ap.add_argument("-o", "--operation", default="create", choices=['convert', 'transform', 'install', 'gencfg', 'update_model_file'], 
        help="operation to do, convert for trt model convert, transform for trt model transform, ...")
    ap.add_argument("-c", "--cfgfile", default="", help="generated cfg file")
    ap.add_argument("-m", "--modellist", default="", help=": seperated model ids")
    ap.add_argument("-s", "--serverlist", default="", help=": seperated server ids")
    ap.add_argument("-t", "--modelcfglist", default="", help=": seperated server ids")
    ap.add_argument("-d", "--outputdir", default="", help="dir to save the converted models")
    ap.add_argument("-e", "--compiledir", default="", help="dir to save the compile project")
    
    args = vars(ap.parse_args())

    strmodelcfglist = args["modelcfglist"] if len(args["modelcfglist"]) > 0 else ""
    modelcfglist = strmodelcfglist.split(":") if len(strmodelcfglist) > 0 else ""
    
    strserverlist = args["serverlist"] if len(args["serverlist"]) > 0 else SERVER_LIST
    server_macro = strserverlist.split(":")

    strmodellist = args["modellist"]
    if strmodellist != "":
        modellist = strmodellist.split(":")
    elif len(server_macro) > 0:
        modellist = ConfigFileHelper.serverMacroToModelList(server_macro)
    dstdir = args["outputdir"]

    ModelInfos_user_define = {
        "LprXml": ModelInfo("LprXml", "LPRUser.json", "cascade.xml", "lpr_xml_v1.0.0.xml", "lpr_xml_v1.0.0.m", 4, 0, 0, ""),
        "LprAlign": ModelInfo("LprAlign", "LPRUser.json", "HorizonalFinemapping.caffemodel", "lpr_align_v1.0.0.trt7", "lpr_align_v1.0.0.m", 4, 0, 0, ""),
        "LprReg": ModelInfo("LprReg", "LPRUser.json", "SegmenationFree-Inception.caffemodel", "lpr_reg_v1.0.0.trt7", "lpr_reg_v1.0.0.m", 4, 0, 0, ""),
        "Npx": ModelInfo("LPR_recognition", "", "", "", "lpr_xml_v1.0.0.m:lpr_align_v1.0.0.m:lpr_reg_v1.0.0.m", 4, 0, 0, "")
    }

    if args["operation"] in ["convert", "transform"]:
        # 通过参数获取CMAKE_BINARY_DIR路径，并进一步获取模型配置文件路径
        model_cfg_path = args["compiledir"] + "/example/model/configs"
        m_model_cfg_path = args["compiledir"] + "/example/model/m_configs"
        print("unit test model config path: {}".format(model_cfg_path))
        # 根据modellist遍历模型配置文件, 不需要的模型文件删除, 获得ModelInfos
        ModelInfos_from_dir = loadJsonDir(model_cfg_path)
        ModelInfos = dict(ModelInfos_from_dir, **ModelInfos_user_define) # 合并两个字典至ModelInfos中
        # print(ModelInfos.keys())

        if args["operation"] in ["convert"]: # 模型转换, 由源模型转换为Trt模型
            print("convert models: [{}], [{}]".format(strserverlist, strmodellist))
            covert(modellist, dstdir)
        elif args["operation"] in ["transform"]: # 将原始模型移动至 model 文件夹下并重命名为m模型
            print("convert servers: [{}]".format(strserverlist))
            transform(modellist, dstdir)
    elif args["operation"] in ["install"]: # 执行本地安装操作，安装m模型，转换为 trt 模型保持文件名不变
        model_cfg_path = "./model/configs"
        print("install package model config path: {}".format(model_cfg_path))
        start = time.perf_counter()
        # 根据modellist遍历模型配置文件，不需要的模型文件删除, 获得ModelInfos
        ModelInfos_from_dir = loadJsonDir(model_cfg_path)
        ModelInfos = dict(ModelInfos_from_dir, **ModelInfos_user_define) # 合并两个字典至ModelInfos中
        # print(ModelInfos.keys())

        mModelInstall(modellist, dstdir)
        end = time.perf_counter()
        print("models have been installed! use time: {} miuntes".format((end-start)/60))
    elif args["operation"] == "gencfg":
        cfgfile = args["cfgfile"]

        # 1. 打印消息
        print("-- create cfgfile[{}] with: [{}]".format(cfgfile, strserverlist))

        if not os.path.exists(dstdir):
            print("cfg dir don't exist, create it [{}]".format(dstdir))
            os.makedirs(dstdir)

        cfgfile = os.path.join(dstdir, cfgfile)

        # 2. 参数检查
        if len(cfgfile) == 0:
            print("-- Usage: model_helper.py -o gencfg -c picasso.cfg")
            exit(-1)
        else:
            # 3. 执行命令
            # 生成配置文件config.ini
            c = ConfigFileHelper(cfgfile)
            c.createConfig(server_macro, cfgfile)
            print("-- config file has been generated")
    elif args["operation"] == "update_model_file":
        model_cfg_path = "./model/configs"
        updateModelFile(model_cfg_path, modellist)
    else:
        print("不支持的操作类型:", args["operation"])
 