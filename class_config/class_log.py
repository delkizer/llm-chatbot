import os
import sys
from class_config.class_env import Config
from loguru import logger


class ConfigLogger:
    LOG_FORMAT = "[{time}] [{level}] [PID: {process}] - {message}"

    def __init__(self, log_name='app_log', backupCount=365):
        self.config = Config()
        self.log_name = log_name
        self.backupCount = backupCount
        self.setup_log_listener()

    def setup_log_listener(self):
        log_dir = self.config.log_path
        log_file = os.path.join(log_dir, self.log_name)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        logger.remove()
        logger.add(sys.stderr, format=self.LOG_FORMAT)
        logger.add(
            log_file,
            rotation="00:00",
            retention=f"{self.backupCount} days",
            format=self.LOG_FORMAT,
            enqueue=True
        )

    @staticmethod
    def get_logger(name):
        return logger.bind(name=name)
