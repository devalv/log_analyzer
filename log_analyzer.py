#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# TODO: update readme
# TODO: verbose comments and docstrings
# TODO: translate comments to English
# TODO: update tests

import argparse
import os
import io
import json
import sys
import logging
import time
import re
import datetime

# import gzip
# import collections


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

    @staticmethod
    def str_to_date(date_str: str, date_fmt: str):
        try:
            converted = datetime.datetime.strptime(date_str, date_fmt).date()
        except (TypeError, ValueError) as conversion_error:
            raise ValueError(conversion_error)
        return converted


@singleton_decorator
class Config(Utils):
    """
    Параметры работы:
        report_size: количество url с наибольшим суммарным временем обработки для сохранены в отчете
        max_mismatch_percent: % при котором структура обрабатываемого файла считается корректной
        log_dir: каталог с обрабатываемыми логами
        log_name_pattern: регулярное выражение по которому будут искаться файлы с логами в каталоге log_dir
        log_name_date_pattern: формат даты для поиска в log_name_pattern
        report_dir: каталог для сохранятения итоговый отчет
        date_fmt: внутренний формат даты для сравнения
        min_log_date: минимальная дата лога Nginx для поиска

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
        self.date_fmt = "%Y%m%d"
        self.min_log_date = "19700101"
        self.log_dir = "log"
        self.log_name_pattern = r"nginx-access-ui\.log-[\d]{8}"
        self.log_name_date_pattern = r"[\d]{8}"
        self.report_dir = "reports"
        self.log_level = "INFO"
        # empty strings for proper config_template output
        self.logfile_path = ""
        self.ts_f_path = ""

        if config_file:
            self.load(config_file)

    @property
    def date_fmt(self):
        return self.__date_fmt

    @date_fmt.setter
    def date_fmt(self, fmt: str):
        assert (isinstance(fmt, str))
        self.__date_fmt = fmt

    @property
    def min_log_date(self):
        return self.__min_log_date

    @min_log_date.setter
    def min_log_date(self, date: str):
        assert (isinstance(date, str))
        self.__min_log_date = date

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
    def log_name_pattern(self):
        return self.__log_name_pattern

    @log_name_pattern.setter
    def log_name_pattern(self, pattern: str):
        assert (isinstance(pattern, str))
        self.__log_name_pattern = pattern

    @property
    def log_name_date_pattern(self):
        return self.__log_name_date_pattern

    @log_name_date_pattern.setter
    def log_name_date_pattern(self, pattern: str):
        assert (isinstance(pattern, str))
        self.__log_name_date_pattern = pattern

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
        # TODO: при экспорте конфигурации экспортируется число
        return self.__log_level

    @log_level.setter
    def log_level(self, level: str):
        assert (isinstance(level, str))

        # TODO: полное перечисление типов или Enum
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


class Analyzer(Utils):

    def __init__(self, config: Config, log: Logging):
        """
        log: собственный логгер для вывода сообщений
        """
        # TODO: ref

        self.log = log
        self.date_fmt = config.date_fmt

        self.log_dir = self.check_file_path(config.log_dir)
        self.log_name_pattern = config.log_name_pattern
        self.log_name_date_pattern = config.log_name_date_pattern

        self.min_log_date = self.str_to_date(config.min_log_date, config.date_fmt)  # noqa

        log.debug('Analyzer initialization complete.')

    @property
    def nginx_log_name_re(self):
        return re.compile(self.log_name_pattern)

    # @property
    # def web_server_log_pattern(self):
    #     # TODO: update
    #     # TODO: rename
    #     return (r''
    #             r'^\S+\s\S+\s{2}\S+\s\[.*?\]\s'
    #             r'\"\S+\s(\S+)\s\S+\"\s'
    #             r'\S+\s\S+\s.+?\s\".+?\"\s\S+\s\S+\s\S+\s'
    #             r'(\S+)')

    # @property
    # def web_server_LOG_SEARCH(self):
    #     # TODO: update
    #     # TODO: rename
    #     return re.compile(self.web_server_log_pattern)
    #
    # @property
    # def web_server_LOG_SEARCH(self):
    #      return re.compile(self.web_server_log_pattern)

    @property
    def log_date_re(self):
        return re.compile(self.log_name_date_pattern)

    @property
    def web_server_log_gen(self):
        """ Generator through web server logs """

        return ((file for file in file_list if self.nginx_log_name_re.match(file)) for __, __, file_list in  # noqa
                os.walk(self.log_dir))

    @property
    def latest_log(self):
        """ Find the newest log in the self.log_dir """

        max_log_date, max_log_f_name = self.min_log_date, None

        for log_file in next(self.web_server_log_gen):
            log_date = self.str_to_date(self.log_date_re.search(log_file).group(),
                                        self.date_fmt)

            if log_date >= max_log_date:
                max_log_date, max_log_f_name = log_date, log_file

        if max_log_f_name:
            self.log.info('Latest Nginx log file: {}'.format(max_log_f_name))
            return max_log_f_name

        raise FileExistsError('Web server log file not found.')
    #
    # def read_log_gen(self, log_f_name):
    #     """ Line by line read the log file """
    #
    #     log_type = gzip.open if log_f_name.endswith(".gz") else open
    #
    #     with log_type(log_f_name, 'rt') as log:
    #         for line in log:
    #             if line:
    #                 yield line
    #
    # def parse_line(self, log_line):
    #     """ Find the line in the log url and time """
    #
    #     grp = self.web_server_LOG_SEARCH.match(log_line)
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
    # def save_report(self, report, file_path):
    #     """ Save the sample report file from reports/report.html """
    #     # TODO: update
    #     with io.open(self.check_file_path('reports/report.html'), mode='r', encoding='utf-8') as f:  # noqa
    #         file_data = f.read()
    #     file_data = file_data.replace('$table_json', json.dumps(report))
    #     with io.open(file_path, mode='w', encoding='utf-8') as f:
    #         f.write(file_data)
    #
    # def median(self, numbers_list):
    #     """ Consider a median """
    #     # TODO: update
    #     numbers_list = sorted(numbers_list)
    #     return numbers_list[int(len(numbers_list) / 2)]
    #
    # def make_report(self, log_stat, total_count, total_time, limit=100):
    #     """ Make report with stats
    #         count - how many times does the url, the absolute value, occur
    #         count_percentage - how many times does a url occur as a percentage of the total number of requests  # noqa
    #         time_sum - total for this URL request_time, absolute value
    #         time_percent - total for this URL request_time, in percent relative to the total request_time all queries  # noqa
    #         time_avg - average request_time for a given URL
    #         time_max - request_time maximum for the given URL
    #         time_med - request_time median for the given URL
    #     """
    #     # TODO: update
    #     # TODO: описать возвращаемые и входящие типы
    #     report_data = []
    #     for url, times in iter(log_stat.items()):
    #         count = len(times)
    #         count_percentage = count / float(total_count / 100)
    #         time_sum = sum(times)
    #         time_percent = time_sum / float(total_time / 100)
    #         time_avg = time_sum / count
    #         time_max = max(times)
    #         time_med = self.median(times)
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

    def run(self):
        """Обработчик для вызова"""
        self.latest_log


def main():
    # TODO: logging.exception(E, exc_info=True)
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
        Analyzer(config=user_config, log=log).run()
        #
        #
        #
        # if last_log_name:
        #     report_date_format = datetime.datetime.strptime(log_date.search(last_log_name).group(), '%Y%m%d').strftime(  # noqa
        #         '%Y.%m.%d')
        #     report_file_name = os.path.join(
        #         make_backup_path(user_config.get('REPORT_DIR')),
        #         'report-' + report_date_format + '.html')
        #     logging.info('Check ' + report_file_name + ' for exist')
        #
        #     if os.path.exists(report_file_name):
        #         logging.info('Report file already exists. Exit')
        #         goodbye(user_config.get('TS_F_PATH', 'log_analyzer.ts'))
        #
        #     logging.info('report file not found. Begin to parse')
        #     logging.info('Will parse ' + last_log_name)
        #     total_count = mismatch_count = total_matched_count = total_time = 0
        #     log_stat = collections.defaultdict(list)
        #     last_log_name = os.path.join(make_backup_path(user_config.get('LOG_DIR')), last_log_name)  # noqa
        #
        #     for line in read_log(last_log_name):
        #         parsed_line = parse_line(line)
        #         total_count += 1
        #         if parsed_line:
        #             total_matched_count += 1
        #             total_time += parsed_line['request_time']
        #             log_stat[parsed_line['request_url']].append(parsed_line['request_time'])
        #         else:
        #             mismatch_count += 1
        #
        #         if (mismatch_count > 10) and (
        #                 (mismatch_count * 100) / total_count > user_config.get('MAX_MISMATCH_PERC', 10)):  # noqa
        #             logging.error('Mismatch count exceeded. Check web_server log format type')  # noqa
        #             sys.exit(1)
        #
        #     if total_matched_count > 0 and total_time > 0:
        #         log_report = make_report(log_stat, total_matched_count, total_time, user_config.get('REPORT_SIZE'))  # noqa
        #         save_report(log_report, report_file_name)
        #         logging.info("Log parsed successfully")

    except AssertionError as error_msg:
        log.error(str(error_msg))
        sys.exit(1)
    else:
        # TODO: method
        if user_config.ts_f_path:
            logging.info('Program completed successfully. TS-file:' + str(user_config.ts_f_path))
            with io.open(user_config.ts_f_path, mode='w', encoding='utf-8') as ts_file:
                ts_time = str(round(time.time(), 0))
                ts_file.write(ts_time.encode().decode())
        sys.exit(0)


if __name__ == '__main__':
    main()
