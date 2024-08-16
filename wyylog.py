import logging
import os
import time


class LogManager:
    def __init__(self, log_file1, log_file2,logList):
        self.log_file1 = log_file1
        #self.log_file2 = log_file2
        self.logList=logList
        # 创建日志目录
        log_dir = os.path.dirname("logs")
        if not os.path.exists("logs"):
            os.makedirs("logs")

        # 配置日志记录器
        self.logger1 = self._configure_logger("logs/"+self.log_file1)
        #self.logger2 = self._configure_logger("logs/"+self.log_file2)

    def _configure_logger(self, log_file):
        # 设置日志格式
        log_format = "%(asctime)s - %(levelname)s - %(message)s"
        date_format = "%Y-%m-%d %H:%M:%S"

        # 创建日志记录器
        logger = logging.getLogger(log_file)
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))
        logger.addHandler(file_handler)
        return logger

    def write_to_log_file(self, log_message, log_level="info"):
        """
        将日志信息写入到两个日志文件中。

        参数:
        log_message (str): 要记录的日志信息
        log_level (str): 日志级别,可选值为"debug", "info", "warning", "error", "critical"

        返回:
        None
        """
        if log_level == "debug":
            self.logger1.debug(log_message)
            #self.logger2.debug(log_message)
            self.logList.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + "- DEBUG -" + log_message)
            self.logList.scrollToBottom()
        elif log_level == "info":
            self.logger1.info(log_message)
            #self.logger2.info(log_message)
            self.logList.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " - INFO - " + log_message)
        elif log_level == "warning":
            self.logger1.warning(log_message)
           # self.logger2.warning(log_message)
            self.logList.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " - WARNING - " + log_message)
        elif log_level == "error":
            self.logger1.error(log_message)
            #self.logger2.error(log_message)
            self.logList.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " - ERROR - " + log_message)
        elif log_level == "critical":
            self.logger1.critical(log_message)
           # self.logger2.critical(log_message)
            self.logList.addItem(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + " - CRITICAL - " + log_message)
        else:
            raise ValueError("Invalid log level: {}".format(log_level))

    def clear_log_file(self, log_file):
        """
        清空指定的日志文件。

        参数:
        log_file (str): 要清空的日志文件路径

        返回:
        None
        """
        with open(log_file, "w", encoding="utf-8") as f:
            f.truncate()
