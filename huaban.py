#!/usr/bin/env python
# -*- coding: utf8 -*-
import sys

__version__ = "5.0.1"
__author__ = "kwell"
__doc__ = "https://blog.saintic.com/blog/204.html"

import logging
import os
from multiprocessing import Pool as ProcessPool
from multiprocessing.dummy import Pool as ThreadPool
from random import choice
from time import sleep

import requests

# 花瓣网域名，目前应该设置为huaban.com，可使用http或https协议。
BASE_URL = 'https://huaban.com'
# 设置下载短暂停止时间，单位：秒
SLEEP_TIME = 1

now_dir = os.path.dirname(os.path.realpath(sys.argv[0]))

logging.basicConfig(level=logging.INFO,
                    format='[ %(levelname)s ] %(asctime)s %(filename)s:%(threadName)s:%(process)d:%(lineno)d %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename='huaban.log',
                    filemode='a')

debug = True
request = requests.Session()
request.verify = True
request.headers.update({'X-Request': 'JSON', 'X-Requested-With': 'XMLHttpRequest', 'Referer': BASE_URL,
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.181 Safari/537.36'})
user_agent_list = [
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; …) Gecko/20100101 Firefox/61.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.62 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.101 Safari/537.36",
    "Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0)",
    "Mozilla/5.0 (Macintosh; U; PPC Mac OS X 10.5; en-US; rv:1.9.2.15) Gecko/20110303 Firefox/3.6.15",
]


def printcolor(msg, color=None):
    if color == "green":
        print('\033[92m{}\033[0m'.format(str(msg)))
    elif color == "blue":
        print('\033[94m{}\033[0m'.format(str(msg)))
    elif color == "yellow":
        print('\033[93m{}\033[0m'.format(str(msg)))
    elif color == "red":
        print('\033[91m{}\033[0m'.format(str(msg)))
    else:
        print(str(msg))


def makedir(d):
    if not os.path.exists(d):
        os.makedirs(d)
    if os.path.exists(d):
        return True
    else:
        return False


def _post_login(email, password):
    """登录函数"""
    res = dict(success=False)
    url = BASE_URL + "/auth/"
    try:
        resp = request.post(url, data=dict(email=email, password=password),
                            headers={'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}).json()
    except Exception as e:
        logging.error(e, exc_info=True)
    else:
        if "user" in resp:
            # 登录成功
            res.update(success=True, data=resp["user"])
        else:
            res.update(resp)
    return res


def _download_img(pin, retry=True):
    """ 下载单个原图
    @param pin dict: pin的数据，要求： {'pin_id': xx, 'suffix': u'png|jpg|jpeg...', 'key': u'xxx-xx', 'board_id': xx}
    @param retry bool: 是否失败重试
    """
    if pin and isinstance(pin, dict) and "pin_id" in pin and "suffix" in pin and "key" in pin and "board_id" in pin:
        imgurl = "http://hbimg.b0.upaiyun.com/{}".format(pin["key"])
        imgdir = pin['board_id']
        imgname = os.path.join(now_dir + '/'+'boards/' + imgdir, '{}.{}'.format(pin["pin_id"], pin["suffix"]))
        if os.path.isfile(imgname):
            if debug:
                printcolor("Skip downloaded images: %s" % imgname)
            return
        try:
            makedir(now_dir + '/boards/' + imgdir)
            req = request.get(imgurl)
            with open(imgname, 'wb') as fp:
                fp.write(req.content)
        except Exception as e:
            logging.warn(e, exc_info=True)
            if retry is True:
                _download_img(pin, False)
            else:
                printcolor("Failed download for {}".format(imgurl), "yellow")
        else:
            if debug:
                printcolor("Successful download for {}, save as {}".format(pin["pin_id"], imgname), "blue")


def _crawl_board(board_id):
    """ 获取画板下所有pin """
    if not board_id:
        return
    limit = 100
    board_url = BASE_URL + '/boards/{}/'.format(board_id)
    try:
        # get first pin data
        r = request.get(board_url).json()
    except requests.ConnectionError:
        request.headers.update({"User-Agent": choice(user_agent_list)})
        r = request.get(board_url).json()
    except Exception as e:
        printcolor("Crawl first page error, board_id: {}".format(board_id), "yellow")
        logging.error(e, exc_info=True)
    else:
        if "board" in r:
            board_data = r["board"]
        else:
            printcolor(r.get("msg"))
            return
        pin_number = board_data["pin_count"]
        retry = 2 * pin_number / limit
        board_pins = board_data["pins"]
        printcolor("Current board <{}> pins number is {}, first pins number is {}".format(board_id, pin_number,
                                                                                          len(board_pins)), 'red')
        if len(board_pins) < pin_number:
            last_pin = board_pins[-1]['pin_id']
            while 1 <= retry:
                # get ajax pin data
                board_next_url = BASE_URL + "/boards/{}/?max={}&limit={}&wfl=1".format(board_id, last_pin, limit)
                try:
                    board_next_data = request.get(board_next_url).json()["board"]
                except Exception as e:
                    logging.error(e, exc_info=True)
                    continue
                else:
                    board_pins += board_next_data["pins"]
                    printcolor("ajax load board with pin_id {}, get pins number is {}, merged".format(last_pin, len(
                        board_next_data["pins"])), "blue")
                    if len(board_next_data["pins"]) == 0:
                        break
                    last_pin = board_next_data["pins"][-1]["pin_id"]
                retry -= 1
        # map(lambda pin: dict(pin_id=pin['pin_id'], suffix=pin['file']['type'].split('/')[-1], key=pin['file']['key'], board_id=board_id), board_pins)
        board_pins = [dict(pin_id=pin['pin_id'], suffix=pin['file'].get('type', "").split('/')[-1] or "png",
                           key=pin['file']['key'], board_id=board_id) for pin in board_pins]
        pool = ThreadPool()
        pool.map(_download_img, board_pins)
        pool.close()
        pool.join()
        printcolor("Current board {}, download over".format(board_id), "green")
        sleep(SLEEP_TIME)


def _crawl_user(user_id):
    """ 查询user的画板 """
    if not user_id:
        return
    user_url = BASE_URL + "/{}".format(user_id)
    limit = 5
    try:
        # get first board data
        r = request.get(user_url).json()
    except requests.ConnectionError:
        request.headers.update({"User-Agent": choice(user_agent_list)})
        r = request.get(user_url).json()
    except Exception as e:
        printcolor("Crawl first page error, user_id: {}".format(user_id), "yellow")
        logging.error(e, exc_info=True)
    else:
        if "user" in r:
            user_data = r["user"]
        else:
            printcolor(r.get("msg"))
            return
        board_number = int(user_data['board_count'])
        retry = 2 * board_number / limit
        board_ids = user_data['boards']
        printcolor("Current user <{}> boards number is {}, first boards number is {}".format(user_id, board_number,
                                                                                             len(board_ids)), 'red')
        if len(board_ids) < board_number:
            last_board = user_data['boards'][-1]['board_id']
            while 1 <= retry:
                # get ajax pin data
                user_next_url = BASE_URL + "/{}?jhhft3as&max={}&limit={}&wfl=1".format(user_id, last_board, limit)
                try:
                    user_next_data = request.get(user_next_url).json()["user"]
                except Exception as e:
                    logging.error(e, exc_info=True)
                    continue
                else:
                    board_ids += user_next_data["boards"]
                    printcolor("ajax load user with board_id {}, get boards number is {}, merged".format(last_board,
                                                                                                         len(
                                                                                                             user_next_data[
                                                                                                                 "boards"])),
                               "blue")
                    if len(user_next_data["boards"]) == 0:
                        break
                    last_board = user_next_data["boards"][-1]["board_id"]
                retry -= 1
        board_ids = list(map(str, [board['board_id'] for board in board_ids]))
        pool = ProcessPool()  # 创建进程池
        pool.map(_crawl_board, board_ids)  # board_ids：要处理的数据列表； _crawl_board：处理列表中数据的函数
        pool.close()  # 关闭进程池，不再接受新的进程
        pool.join()  # 主进程阻塞等待子进程的退出
        printcolor("Current user {}, download over".format(user_id), "green")


def main():
    act = input("抓取画板请选输入1，抓取用户请输入2 \n请选择: ")

    if act == '1':
        action = "getBoard"
        board_id = input("请输入要抓取的画板编号: ")
    elif act == '2':
        action = "getUser"
        user_id = input("请输入要抓取的用户编号: ")
    else:
        action = ''
        board_id = ''
        user_id = ''

    login = input("是否登录? 登录选择1，不登录选择2\n请选择: ")
    if login == '1':
        user = input("请输入huaban网帐号: ")
        password = input("请输入huaban网密码: ")
    else:
        user = ''
        password = ''

    version = ''

    if version:
        printcolor("https://github.com/staugur/grab_huaban_board, v{}".format(__version__))
        return
    # 用户登录
    if user and password:
        auth = _post_login(user, password)
        if not auth["success"]:
            printcolor(auth["msg"], "yellow")
            return
    else:
        printcolor("您未设置账号密码，将处于未登录状态，抓取的图片可能有限；设置账号密码后，图片抓取率大部分可达100%！")
    # 主要动作-功能

    if action == "getBoard":
        # 抓取单画板
        if not board_id:
            printcolor("请设置board_id参数", "yellow")
            return
        makedir(now_dir + "/boards/")
        os.chdir(now_dir + "/boards/")
        _crawl_board(board_id)
    elif action == "getUser":
        # 抓取单用户
        if not user_id:
            printcolor("请设置user_id参数", "yellow")
            return
        makedir(now_dir + '/' + user_id)
        os.chdir(now_dir + '/' + user_id)
        _crawl_user(user_id)
    else:
        print("something wrong")


if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser()
    # parser.add_argument("-a", "--action", default="getBoard", help="脚本动作 -> 1. getBoard: 抓取单画板(默认); 2. getUser: 抓取单用户")
    # parser.add_argument("-u", "--user", help="花瓣网账号-手机/邮箱")
    # parser.add_argument("-p", "--password", help="花瓣网账号对应密码")
    # parser.add_argument("-v", "--version", help="查看版本号", action='store_true')
    # parser.add_argument("--board_id", help="花瓣网单个画板id, action=getBoard时使用")
    # parser.add_argument("--user_id", help="花瓣网单个用户id, action=getUser时使用")
    main()

    os.system('open .')
