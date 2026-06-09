"""单例日志系统：控制台 INFO + 文件 DEBUG"""

import logging
import os
from datetime import datetime


class Logger:
    _instance: logging.Logger | None = None

    def __new__(cls) -> logging.Logger:
        if cls._instance is None:
            cls._instance = cls._create_logger()
        return cls._instance

    @classmethod
    def _create_logger(cls) -> logging.Logger:
        logger = logging.getLogger("ParseApp")
        logger.setLevel(logging.DEBUG)

        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "log")
        os.makedirs(log_dir, exist_ok=True)

        log_file = os.path.join(
            log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log"
        )

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger
