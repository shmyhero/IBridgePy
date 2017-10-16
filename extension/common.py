import os.path
import datetime
import ConfigParser
from utils import IOHelper


class PathMgr(object):

    def __init__(self):
        pass

    @staticmethod
    def get_project_path():
        path_dir = os.path.dirname(os.path.abspath(__file__))
        return path_dir[:path_dir.rindex(os.path.sep)]

    @staticmethod
    def get_extension_path():
        return os.path.join(PathMgr.get_project_path(), 'extension')

    @staticmethod
    def get_config_path():
        extension_path = PathMgr.get_extension_path()
        return os.path.join(extension_path, 'config.conf')

    @staticmethod
    def get_log_path(sub_path = None):
        project_path = PathMgr.get_project_path()
        if sub_path:
            log_path = os.path.join(project_path, "logs", sub_path)
        else:
            log_path = os.path.join(project_path, "logs")
        IOHelper.ensure_dir_exists(log_path)
        return log_path


class ConfigMgr(dict):
    conf_dict = None

    @staticmethod
    def read_config():
        conf = ConfigParser.RawConfigParser()
        conf.read(PathMgr.get_config_path())
        return conf

    @staticmethod
    def get_config():
        if ConfigMgr.conf_dict is None:
            dic = {}
            conf = ConfigMgr.read_config()
            for section in conf.sections():
                section_dic = {}
                for option in conf.options(section):
                    section_dic[option] = conf.get(section, option)
                dic[section] = section_dic
            ConfigMgr.conf_dict = dic
        return ConfigMgr.conf_dict

    @staticmethod
    def get_db_config():
        return ConfigMgr.get_config()['db']

    @staticmethod
    def get_mail_config():
        return ConfigMgr.get_config()['mail']


