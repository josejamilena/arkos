import os
import sys

from arkos.config import Config
from arkos.storage import Storage
from arkos.utilities import new_logger
from arkos.connections import ConnectionsManager


class LoggingControl:
    def __init__(self, default):
        self.active_logger = default
    
    def info(self, msg):
        self.active_logger.info(msg)
    
    def warn(self, msg):
        self.active_logger.warn(msg)
    
    def error(self, msg):
        self.active_logger.error(msg)
    
    def debug(self, msg):
        self.active_logger.debug(msg)


class StorageControl:
    def __init__(self):
        self.apps = Storage(["applications"])
        self.sites = Storage(["sites"])
        self.certs = Storage(["certificates", "authorities"])
        self.dbs = Storage(["databases", "users", "managers"])
        self.points = Storage(["points"])
        self.updates = Storage(["updates"])
        self.policies = Storage(["policies"])
        self.files = Storage(["shares"])
        self.signals = Storage(["listeners"])


config = Config()
if os.path.exists(os.path.join(sys.path[0], "settings.json")):
    config.load(os.path.join(sys.path[0], "settings.json"))
elif os.path.exists("/etc/arkos/settings.json"):
    config.load("/etc/arkos/settings.json")
storage = StorageControl()
logger = LoggingControl(new_logger(20, debug=True))
conns = ConnectionsManager(config)
