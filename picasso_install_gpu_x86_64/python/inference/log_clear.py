#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
 * Copyright (c) 2019 ZNV.Co.Ltd
 * All rights reserved.
 *
 * @file: log_clear.py
 * @brief: 
 * @version 1.0
 * @date 2021/6/29
"""

import threading
import os
import time

__all__ = ['LogClear']


def clear_useless_log(_path):
    while True:
        if not os.path.exists(_path):
            raise RuntimeError(f'path not exist: {_path}')
        print(' Remove Useless Log Files! ')
        log_files = os.listdir(_path)
        for lg in log_files:
            f = os.path.join(_path, lg)
            if os.path.islink(f) or not os.path.exists(f):
                continue
            mtime = time.localtime(os.path.getmtime(f))
            now_time = time.localtime(time.time())
            if abs(now_time.tm_mday - mtime.tm_mday) > 3:
                try:
                    os.remove(f)
                except Exception as e:
                    print(f'remove {f} error: {e}')
        time.sleep(60 * 60 * 24)


class LogClear:
    def __call__(self, log_path='log'):
        self.log_path = log_path
        folder = os.path.join(os.getcwd(), self.log_path)
        try:
            clear_th = threading.Thread(target=clear_useless_log, args=(folder,))
            clear_th.setDaemon(False)
            clear_th.start()
        except Exception as e:
            print(f'Log Clear Error: {e}')


if __name__ == '__main__':
    # mtime = time.localtime(os.path.getmtime('D:/ftp_dowload/result/results/2007_000129.png'))
    log_clear = LogClear()
    log_clear('D:/ftp_dowload/result/result_59')
