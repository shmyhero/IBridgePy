import sys
import logging
import datetime
import os
import glob
import urllib2

def string_fetch(string, first, last):
    try:
        if first == '':
            start = 0
        else:
            start = string.index(first) + len(first)
        if last == '':
            end = len(string)
        else:
            end = string.index(last, start)
        return string[start:end]
    except ValueError:
        return ''

class Logger:

    log_file = None
    logger_names = []

    def __init__(self, name, log_path, console=True):
        self.console = console
        self.logger = logging.getLogger(name)
        if log_path:
            self.log_path = log_path
            self.logger.setLevel(logging.INFO)
            self.init_handler(name)
        else:
            self.log_path = None

    def init_handler(self, name):
        file_path = '%s/%s.log'%(self.log_path, datetime.date.today())
        if Logger.log_file != file_path:
            Logger.log_file = file_path
            Logger.logger_names = []
        if name not in Logger.logger_names:
            fh = logging.FileHandler(file_path)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            Logger.log_file = file_path
            Logger.logger_names.append(name)

    def output_console(self, customized_console):
        if customized_console is None:
            return self.console
        else:
            return customized_console

    def info(self, content, console = None):
        if self.output_console(console):
            sys.stdout.write('%s\n'%content)
        if self.log_path:
            self.logger.info(content)

    def error(self, content, console = None):
        if self.output_console(console):
            sys.stderr.write('%s\n'%content)
        if self.log_path:
            self.logger.error(content)

    def warning(self, content, console = None):
        if self.output_console(console):
            sys.stderr.write('%s\n'%content)
        if self.log_path:
            self.logger.warning(content)

    def exception(self, content, console = None):
        if self.output_console(console):
            sys.stderr.write('%s\n'%content)
        if self.log_path:
            self.logger.exception(content)


class IOHelper(object):

    @staticmethod
    def ensure_dir_exists(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    @staticmethod
    def ensure_parent_dir_exists(path):
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)

    @staticmethod
    def read_file_to_string(file_path):
        f = open(file_path, 'r')
        content = f.read()
        f.close()
        return content

    @staticmethod
    def write_to_file(file_path, content):
        f = open(file_path, 'w')
        f.write(content)
        f.close()

    @staticmethod
    def get_sub_dir_names(path):
        if os.path.exists(path):
            file_names = os.listdir(path)
            for file_name in file_names:
                file_path = os.path.join(path, file_name)
                if os.path.isdir(file_path):
                    yield file_name

    @staticmethod
    def get_sub_files(path, ext = None):
        sub_path = '*.' + ext if ext else '*'
        str_path = os.path.join(path, sub_path)
        return glob.glob(str_path)


class HttpHelper:

    def __init__(self):
        pass

    @staticmethod
    def http_get(url, headers=None):
        if headers:
            f = urllib2.urlopen(urllib2.Request(url=url, headers=headers))
        else:
            f = urllib2.urlopen(url)
        s = f.read()
        return s
