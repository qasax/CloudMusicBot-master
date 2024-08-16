import base64
import codecs
import os
import random
import re
import string
import sys
from typing import Callable, Any
import requests
import json
from dingLog import DingLog
from Crypto.Cipher import AES
import wyylog


class Bot:
    def __init__(self, context, dinglog,runlog):
        self.userInfoUrl = "https://music.163.com/api/nuser/account/get"
        self.taskDataUrl = "https://interface.music.163.com/api/music/partner/daily/task/get"
        self.session = requests.session()
        self.dinglog = dinglog
        self.context = context
        self.mylog = runlog
    def run(self) -> bool:
        try:
            self.__loadCookie()
            self.__getUserName()
            complete, taskData = self.__getUserTask()
            if not complete:
                self.__sign(taskData)
        except RuntimeError:
            return False
        return True

    def __loadCookie(self):
        flag = False
        for key in ["MUSIC_U", "__csrf"]:
            cookie = self.context.getUserData("Cookie_" + key)
            if cookie:
                self.session.cookies.set(key, cookie)
            else:
                self.dinglog.info(f"未填写cookie「{key}」")
                self.mylog.write_to_log_file(f"未填写cookie「{key}」", "error")
                flag = True
        if flag:
            raise RuntimeError

    def __getUserName(self):
        profile = self.session.get(url=self.userInfoUrl).json()["profile"]
        if profile:
            self.dinglog.info(f'用户名: {profile["nickname"]}')
            self.mylog.write_to_log_file(f'用户名: {profile["nickname"]}', "info")
        else:
            self.dinglog.info("未能获取用户信息,请重新设置Cookie")
            self.mylog.write_to_log_file("未能获取用户信息,请重新设置Cookie", "error")
            raise RuntimeError

    def __getUserTask(self) -> [bool, json]:
        taskData = self.session.get(url=self.taskDataUrl).json()["data"]
        count = taskData["count"]
        completedCount = taskData["completedCount"]
        todayTask = f"[{completedCount}/{count}]"
        complete = count == completedCount
        self.dinglog.info(f'今日任务：{"已完成" if complete else "未完成"}{todayTask}')
        self.mylog.write_to_log_file(f'今日任务：{"已完成" if complete else "未完成"}{todayTask}', "info")
        return complete, taskData

    def __sign(self, taskData):
        self.dinglog.info("开始评分...")
        self.mylog.write_to_log_file("开始评分...", "info")
        signer = Signer(self.session, taskData["id"], self.dinglog,self.mylog)
        for task in taskData["works"]:
            work = task["work"]
            if task["completed"]:
                self.dinglog.info(f'{work["name"]}「{work["authorName"]}」已有评分：{int(task["score"])}分')
                self.mylog.write_to_log_file(f'{work["name"]}「{work["authorName"]}」已有评分：{int(task["score"])}分', "info")
            else:
                signer.sign(work)


def addTo16(data: str):
    while len(data) % 16 != 0:
        data += '\0'
    return str.encode(data)


class Signer:
    def __init__(self, session: requests.Session, taskID, log,runlog):
        self.signUrl = "https://interface.music.163.com/weapi/music/partner/work/evaluate?csrf_token="

        self.randomStr = "".join(random.choice(
            string.ascii_letters + string.digits) for _ in range(16))  # 随机生成长度为16的字符串
        self.pubKey = "010001"  # buU9L(["流泪", "强"])的值
        # buU9L(Rg4k.md)的值
        self.modulus = "00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee341f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7"
        self.iv = "0102030405060708"  # 偏移量
        self.aesKey = '0CoJUm6Qyw8W8jud'  # buU9L(["爱心", "女孩", "惊恐", "大笑"])的值

        self.pattern = re.compile('.*[a-zA-Z].*')
        self.session = session
        self.taskID = taskID
        self.dinglog = log
        self.mylog=runlog

    def __getScoreAndTag(self, work) -> [str, str]:
        star = "3"
        if self.pattern.match(work["name"] + work["authorName"]):
            star = "4"
        return star, star + "-A-1"

    def __getAesEncrypt(self, data: str, key: str):
        bs = AES.block_size
        pad2: Callable[[Any], Any] = lambda s: s + (bs - len(s) % bs) * chr(bs - len(s) % bs)
        encryptor = AES.new(addTo16(key), AES.MODE_CBC, addTo16(self.iv))
        encrypt_aes = encryptor.encrypt(str.encode(pad2(data)))
        encrypt_text = str(base64.encodebytes(encrypt_aes), encoding='utf-8')
        return encrypt_text

    def __getParams(self, data) -> str:
        return self.__getAesEncrypt(self.__getAesEncrypt(str(data), self.aesKey), self.randomStr)

    def __getEncSecKey(self) -> str:
        text = self.randomStr[::-1]
        rs = int(codecs.encode(text.encode('utf-8'), 'hex_codec'), 16) ** int(self.pubKey, 16) % int(self.modulus, 16)
        return format(rs, 'x').zfill(256)

    def sign(self, work):
        try:
            csrf = str(self.session.cookies["__csrf"])
            score, tag = self.__getScoreAndTag(work)
            data = {
                "params": self.__getParams({
                    "taskId": self.taskID,
                    "workId": work['id'],
                    "score": score,
                    "tags": tag,
                    "customTags": "%5B%5D",
                    "comment": "",
                    "syncYunCircle": "true",
                    "csrf_token": csrf
                }).replace("\n", ""),
                "encSecKey": self.__getEncSecKey()
            }
            response = self.session.post(url=f'{self.signUrl}={csrf}', data=data).json()
            if response["code"] == 200:
                self.dinglog.info(f'{work["name"]}「{work["authorName"]}」评分完成：{score}分')
                self.mylog.write_to_log_file(f'{work["name"]}「{work["authorName"]}」评分完成：{score}分', "info")
        except Exception as e:
            self.dinglog.info(f'歌曲「{work["name"]}」评分异常：{str(e)}')
            self.mylog.write_to_log_file(f'歌曲「{work["name"]}」评分异常：{str(e)}', "info")
            raise RuntimeError


# 以下是本地使用时的代码
class Context:
    def __init__(self):
        # 需要在同一文件夹下建一个json文件,写入"Cookie_MUSIC_U","Cookie___csrf","BOT_URL"(供钉钉机器人使用,选填)
        #script_path = os.path.dirname(__file__)  # 获取当前.py文件的执行目录（打包为exe后激活 158,159两行代码，注释掉160,161行代码）
        #self.settings_file = os.path.join(script_path, "setting.json") #读取json配置
        #script_path = os.path.abspath(sys.executable) #获取exe文件的执行目录，根据该目录查询settings.json（原生运行时激活160,161 两行代码，注释掉158,159行代码）
        #self.settings_file = os.path.join(os.path.dirname(script_path), "setting.json")
        with open("setting.json", "r", encoding="utf-8") as file:
            self.dic = json.loads(file.read())

    def getUserData(self, key):
        return self.dic[key]
