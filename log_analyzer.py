#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: update readme
# TODO: translate comments to English
# TODO: update tests

import argparse
import os
import io
import json
import sys
import logging

# import re
# import collections
# import datetime
# import gzip
# import time

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '  # noqa
#                     '$status $body_bytes_sent "$http_referer" '  # noqa
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '  # noqa
#                     '$request_time';  # noqa

# log_search_pattern = re.compile('nginx-access-ui\.log-[0-9]{4}[0-9]{2}[0-9]{2}')  # noqa
# log_date = re.compile('[0-9]{4}[0-9]{2}[0-9]{2}')
#
# web_server_LOG_SEARCH_PATTERNS = (r''
#                                   r'^\S+\s\S+\s{2}\S+\s\[.*?\]\s'
#                                   r'\"\S+\s(\S+)\s\S+\"\s'
#                                   r'\S+\s\S+\s.+?\s\".+?\"\s\S+\s\S+\s\S+\s'
#                                   r'(\S+)')
#
# web_server_LOG_SEARCH = re.compile(web_server_LOG_SEARCH_PATTERNS)


def singleton_decorator(cls):
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


class Utils:
    """Абстрактный класс с универсальными утилитами"""

    def public_attrs(self) -> dict:
        """Словарь только публичных атрибутов класса"""

        result_dict = dict()

        for attr in dir(self):
            if attr.startswith('_'):
                continue
            if hasattr(self.__class__, attr) and callable(getattr(self.__class__, attr)):  # noqa
                continue
            attr_value = getattr(self.__class__, attr) if hasattr(self.__class__, attr) else self.__getattribute__(attr)  # noqa
            if isinstance(attr_value, property):
                attr_value = attr_value.fget(self)
            result_dict[attr] = attr_value
        return result_dict

    def update(self, config_dict: dict):
        """Задает значения публичных атрибутов класса"""

        for attr in config_dict:
            if attr.startswith('_'):
                continue
            if hasattr(self.__class__, attr) and callable(getattr(self.__class__, attr)):  # noqa
                continue
            self.__setattr__(attr.lower(), config_dict[attr])

    @staticmethod
    def check_file_path(file_path) -> os.path:
        """Raises FileExistsError if file_path not exists."""

        if not os.path.exists(file_path):
            file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_path)  # noqa

        if not os.path.exists(file_path):
            raise FileExistsError('File {} not exists.'.format(file_path))

        return file_path

    @staticmethod
    def check_extension(file_name: str, extension: str):
        """
        Raises AssertionError if extension of file_name mismatch extension.
        file_name example: 'config.json'
        extension example: '.json'
        """

        __, file_ext = os.path.splitext(file_name)
        assert file_ext == extension


@singleton_decorator
class Config(Utils):
    """
    Параметры работы:
        report_size: количество url с наибольшим суммарным временем обработки для сохранены в отчете
        max_mismatch_percent: % при котором структура обрабатываемого файла считается корректной
        log_dir: каталог с обрабатываемыми логами
        report_dir: каталог для сохранятения итоговый отчет

    Параметры логгирования работы:
        log_level: уровень логгирования
        logfile_format: формат лога выполнения
        logfile_date_format: формат даты для лога выполнения
        logfile_path: файл для записи лога выполнения (если не указан - только на stdout)
        ts_f_path: файл в который будет сохранено время завершения работы (аналогично stat -c %Y log_analyzer.ts)  # noqa

    Служебные параметры:
        __extension: допустимое расширение/формат конфигурационного файла
    """

    def __init__(self, config_file: str = None):
        """Если config_file не передан - нет попытки прочитать файл."""

        self.__extension = '.json'
        self.report_size = 100
        self.max_mismatch_percent = 10
        self.logfile_format = "[%(asctime)s] %(levelname).1s %(message)s"
        self.logfile_date_format = "%Y.%m.%d %H:%M:%S"
        self.log_dir = "log"
        self.report_dir = "reports"
        self.log_level = "INFO"
        # empty strings for proper config_template output
        self.logfile_path = ""
        self.ts_f_path = ""

        if config_file:
            self.load(config_file)

    @property
    def report_size(self):
        return self.__report_size

    @report_size.setter
    def report_size(self, size: int):
        assert (isinstance(size, int))
        if size < 1:
            size = 1
        self.__report_size = size

    @property
    def report_dir(self):
        return self.__report_dir

    @report_dir.setter
    def report_dir(self, directory: str):
        assert (isinstance(directory, str))
        self.check_file_path(directory)
        self.__report_dir = directory

    @property
    def log_dir(self):
        return self.__log_dir

    @log_dir.setter
    def log_dir(self, directory: str):
        assert (isinstance(directory, str))
        self.check_file_path(directory)
        self.__log_dir = directory

    @property
    def logfile_format(self):
        return self.__logfile_format

    @logfile_format.setter
    def logfile_format(self, log_format: str):
        assert (isinstance(log_format, str))
        self.__logfile_format = log_format

    @property
    def logfile_date_format(self):
        return self.__logfile_date_format

    @logfile_date_format.setter
    def logfile_date_format(self, date_format: str):
        assert (isinstance(date_format, str))
        self.__logfile_date_format = date_format

    @property
    def max_mismatch_percent(self):
        return self.__max_mismatch_percent

    @max_mismatch_percent.setter
    def max_mismatch_percent(self, percent: int):
        assert (isinstance(percent, int))
        if percent < 1:
            percent = 1
        elif percent > 100:
            percent = 100
        self.__max_mismatch_percent = percent

    @property
    def ts_f_path(self):
        return self.__ts_f_path

    @ts_f_path.setter
    def ts_f_path(self, file_path: str):
        assert (isinstance(file_path, str))
        file_path_directory = os.path.dirname(file_path)
        self.check_file_path(file_path_directory)
        self.__ts_f_path = file_path

    @property
    def log_level(self):
        return self.__log_level

    @log_level.setter
    def log_level(self, level: str):
        assert (isinstance(level, str))
        # TODO: заменить на Enum с полным  перечислением
        if level.upper() == 'INFO':
            level = logging.INFO
        elif level.upper() == 'DEBUG':
            level = logging.DEBUG
        self.__log_level = level

    @property
    def logfile_path(self):
        return self.__logfile_path

    @logfile_path.setter
    def logfile_path(self, file_path: str):
        assert (isinstance(file_path, str))
        file_path_directory = os.path.dirname(file_path)
        self.check_file_path(file_path_directory)
        self.__logfile_path = file_path

    def load(self, config_file):
        """Читаем параметры из конфигурационного файла и записываем в атрибуты класса."""  # noqa

        config_file = self.check_file_path(config_file)
        self.check_extension(config_file, self.__extension)

        with io.open(config_file, mode="r", encoding="utf-8") as json_config:
            file_config = json.load(json_config)

        self.update(file_config)

    @classmethod
    def create_template(cls, file_path):
        """Создаем конфигурационный файл по атрибутам класса."""

        # For extra verbosity keys should be in upper register
        attrs = {k.upper(): v for k, v in cls().public_attrs().items()}

        with io.open(file_path, mode="w", encoding="utf-8") as json_config_template:  # noqa
            json.dump(attrs, json_config_template, sort_keys=True, indent=2, ensure_ascii=False)  # noqa


@singleton_decorator
class Logging:
    """Logger configuration"""

    def __init__(self,
                 logfile_date_format: str,
                 logfile_format: str,
                 log_level=logging.INFO,
                 logfile_path: str = None,
                 **kwargs):

        logger = logging.getLogger('log_analyzer')

        formatter = logging.Formatter(fmt=logfile_format, datefmt=logfile_date_format)  # noqa
        handler = logging.FileHandler(logfile_path) if logfile_path else logging.StreamHandler(stream=sys.stdout) # noqa
        handler.setFormatter(formatter)
        handler.setLevel(log_level)

        logger.addHandler(handler)
        logger.setLevel(log_level)

        logger.debug('Log init complete.')
        self.logger = logger

    def debug(self, message: str):
        assert (isinstance(message, str))
        self.logger.debug(message)

    def info(self, message: str):
        assert (isinstance(message, str))
        self.logger.info(message)

    def warning(self, message: str):
        assert (isinstance(message, str))
        self.logger.warning(message)

    def error(self, message: str):
        assert (isinstance(message, str))
        self.logger.error(message)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json', type=str,
                        help='Path to configuration file, ex: /var/log/config.json')  # noqa
    parser.add_argument('--template', default=False, type=bool,
                        help='Create config template')
    return parser.parse_args()


# TODO: Analyzer class
# TODO: не обработано
# def make_web_server_logs_list(log_dir):
#     """ Make a list of web server logs """
#
#     web_server_logs_list = []
#     for __, __, filelist in os.walk(log_dir):
#         for file in filelist:
#             if log_search_pattern.match(file):
#                 web_server_logs_list.append(file)
#     return web_server_logs_list
#
#
# def find_max_log_date(web_server_logs_list):
#     """Find max log date in list"""
#
#     max_log_date = datetime.datetime.strptime(log_date.search(web_server_logs_list[0]).group(), '%Y%m%d').date()  # noqa
#     max_log_f_name = web_server_logs_list[0]
#     for web_server_log_file in web_server_logs_list:
#         local_log_date = datetime.datetime.strptime(log_date.search(web_server_log_file).group(), '%Y%m%d').date()  # noqa
#         if local_log_date > max_log_date:
#             max_log_date = local_log_date
#             max_log_f_name = web_server_log_file
#     return max_log_f_name
#
#
# def find_log(log_dir):
#     """ Find the newest log in the list """
#
#     max_log_f_name = None
#     web_server_logs_list = make_web_server_logs_list(log_dir)
#     if len(web_server_logs_list) > 0:
#         max_log_f_name = find_max_log_date(web_server_logs_list)
#         logging.info('Found web_server log-files: ' + ', '.join(web_server_logs_list))  # noqa
#     else:
#         logging.info('web_server log-file not found')
#
#     return max_log_f_name
#
#
# def read_log(log_f_name):
#     """ Line by line read the log file """
#     # TODO: Такое использование менеджера контекста кажется сомнительным
#
#     if log_f_name.endswith(".gz"):
#         log_type = gzip.open
#     else:
#         log_type = open
#
#     with log_type(log_f_name, 'rt') as log:
#         for line in log:
#             if line:
#                 yield line
#
#
# def parse_line(log_line):
#     """ Find the line in the log url and time """
#
#     grp = web_server_LOG_SEARCH.match(log_line)
#     if grp:
#         col_names = ('request_url', 'request_time')
#         parsed_line = (dict(zip(col_names, grp.groups())))
#         if parsed_line['request_time'] != '-':
#             parsed_line['request_time'] = float(parsed_line['request_time'])
#         else:
#             parsed_line['request_time'] = 0
#         return parsed_line
#     return None
#
#
# def add_file_logging(logfile,
#                      log_format='[%(asctime)s] %(levelname).1s %(message)s',
#                      log_date_format="%Y.%m.%d %H:%M:%S"):
#     """ Duplicate the log of the script in the file """
#
#     file_handler = logging.FileHandler(logfile)
#     file_handler.setLevel(logging.INFO)
#     formatter = logging.Formatter(log_format, datefmt=log_date_format)
#     file_handler.setFormatter(formatter)
#     logging.getLogger().addHandler(file_handler)
#
#
# def goodbye(ts_f_path):
#     """ Save the timestamp to a file and exit """
#
#     logging.info('Program completed successfully. TS-file:' + str(ts_f_path))
#     with io.open(ts_f_path, mode='w', encoding='utf-8') as ts_file:
#         ts_time = str(round(time.time(), 0))
#         ts_file.write(ts_time.encode().decode())
#     sys.exit(0)
#
#
# def save_report(report, file_path):
#     """ Save the sample report file from reports/report.html """
#
#     with io.open(make_backup_path('reports/report.html'), mode='r', encoding='utf-8') as f:  # noqa
#         file_data = f.read()
#     file_data = file_data.replace('$table_json', json.dumps(report))
#     with io.open(file_path, mode='w', encoding='utf-8') as f:
#         f.write(file_data)
#
#
# def median(numbers_list):
#     """ Consider a median """
#
#     numbers_list = sorted(numbers_list)
#     return numbers_list[int(len(numbers_list) / 2)]
#
#
# def make_report(log_stat, total_count, total_time, limit=100):
#     """ Make report with stats
#         count - how many times does the url, the absolute value, occur
#         count_percentage - how many times does a url occur as a percentage of the total number of requests  # noqa
#         time_sum - total for this URL request_time, absolute value
#         time_percent - total for this URL request_time, in percent relative to the total request_time all queries  # noqa
#         time_avg - average request_time for a given URL
#         time_max - request_time maximum for the given URL
#         time_med - request_time median for the given URL
#     """
#     # TODO: описать возвращаемые и входящие типы
#     report_data = []
#     for url, times in iter(log_stat.items()):
#         count = len(times)
#         count_percentage = count / float(total_count / 100)
#         time_sum = sum(times)
#         time_percent = time_sum / float(total_time / 100)
#         time_avg = time_sum / count
#         time_max = max(times)
#         time_med = median(times)
#
#         report_data.append({"count": count,
#                             "time_avg": round(time_avg, 3),
#                             "time_max": round(time_max, 3),
#                             "time_sum": round(time_sum, 3),
#                             "url": url,
#                             "time_med": round(time_med, 3),
#                             "time_percent": round(time_percent, 3),
#                             "count_percentage": round(count_percentage, 3)
#                             })
#
#     report_data.sort(key=lambda x: x['time_sum'], reverse=True)
#
#     return report_data[:limit]
#


def main():
    args = parse_args()
    if args.template:
        log = Logging(None, None)
        Config().create_template(args.config)
        log.info('Template configuration file {} created. Exit.'.format(args.config))  # noqa
        return

    user_config = Config(args.config)
    log = Logging(**user_config.public_attrs())
    log.debug('Initialization completed.')

    try:
        pass
    except AssertionError as error_msg:
        log.error(str(error_msg))
        sys.exit(1)
    else:
        pass
        # TODO: log time
        # goodbye(user_config.get('TS_F_PATH', 'log_analyzer.ts'))

# try:
#     last_log_name = find_log(make_backup_path(user_config['LOG_DIR']))
#
#     if last_log_name:
#         report_date_format = datetime.datetime.strptime(log_date.search(last_log_name).group(), '%Y%m%d').strftime(  # noqa
#             '%Y.%m.%d')
#         report_file_name = os.path.join(
#             make_backup_path(user_config.get('REPORT_DIR')),
#             'report-' + report_date_format + '.html')
#         logging.info('Check ' + report_file_name + ' for exist')
#
#         if os.path.exists(report_file_name):
#             logging.info('Report file already exists. Exit')
#             goodbye(user_config.get('TS_F_PATH', 'log_analyzer.ts'))
#
#         logging.info('report file not found. Begin to parse')
#         logging.info('Will parse ' + last_log_name)
#         total_count = mismatch_count = total_matched_count = total_time = 0
#         log_stat = collections.defaultdict(list)
#         last_log_name = os.path.join(make_backup_path(user_config.get('LOG_DIR')), last_log_name)  # noqa
#
#         for line in read_log(last_log_name):
#             parsed_line = parse_line(line)
#             total_count += 1
#             if parsed_line:
#                 total_matched_count += 1
#                 total_time += parsed_line['request_time']
#                 log_stat[parsed_line['request_url']].append(parsed_line['request_time'])
#             else:
#                 mismatch_count += 1
#
#             if (mismatch_count > 10) and (
#                     (mismatch_count * 100) / total_count > user_config.get('MAX_MISMATCH_PERC', 10)):  # noqa
#                 logging.error('Mismatch count exceeded. Check web_server log format type')  # noqa
#                 sys.exit(1)
#
#         if total_matched_count > 0 and total_time > 0:
#             log_report = make_report(log_stat, total_matched_count, total_time, user_config.get('REPORT_SIZE'))  # noqa
#             save_report(log_report, report_file_name)
#             logging.info("Log parsed successfully")
#
# except Exception as E:
#     logging.exception(E, exc_info=True)
# else:
#


if __name__ == '__main__':
    main()
