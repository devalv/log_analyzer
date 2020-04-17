#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Simple nginx log analyzer."""

__author__ = 'Aleksey Devyatkin <devyatkin.av@ya.ru>'

# TODO: update readme
# TODO: протестировать на 3.6.9, 3.6.4, 3.5.3
# TODO: update tests

# TODO: скобки к одному формату
# TODO: актуализировать все сообщения в debug
# TODO: комментарии привести к 1му языку
# TODO: verbose comments and docstrings

# TODO: разбить Analyzer
# TODO: возможность сохранить результаты проверяется после выполнения большего кода программы.


import argparse
import collections
import datetime
import gzip
import io
import json
import logging
import os
import re
import sys
import time


def singleton_decorator(cls):
    """Декоратор превращающий декорируемый класс в синглтон"""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


def log_property_decorator(func):
    """Декоратор вызывается перед работой property.setter
       т.к. это property, 0левым аргументом ожидается инстанс класса.
       В качестве логгера ожидается root_logger
    """

    def wrapper(*args, **kwargs):
        # Намеренное обращение по константе, т.к. нужен конкретный логгер.
        instance_logger = getattr(args[0], 'root_logger') if len(args) > 0 else None  # noqa
        result = func(*args, **kwargs)

        if instance_logger:
            instance_logger.debug('{}: {}'.format(func.__name__, result))

        return result

    return wrapper


class Utils:
    """Абстрактный класс с универсальными утилитами"""

    @property
    def _ts_time(self):
        return round(time.time(), 0)

    @property
    def _ts_time_str(self):
        return str(self._ts_time)

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
    def check_exists(file_path) -> os.path:
        """Raises FileNotFoundError if file_path not exists."""

        if not os.path.exists(file_path):
            file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_path)  # noqa

        if not os.path.exists(file_path):
            raise FileNotFoundError('File {} not exists.'.format(file_path))

        return file_path

    @staticmethod
    def check_not_exists(file_path):
        """Raises FileNotFoundError if file_path not exists."""
        if os.path.exists(file_path):
            raise FileExistsError('File {} already exists.'.format(file_path))
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

    @staticmethod
    def date_to_str(date: datetime.date, date_fmt: str):
        try:
            converted = datetime.datetime.strftime(date, date_fmt)
        except (TypeError, ValueError) as conversion_error:
            raise ValueError(conversion_error)
        return converted

    @staticmethod
    def read_file_gen(file_name: str):
        """ Line by line read the log file """

        assert (isinstance(file_name, str))
        file_context = gzip.open if file_name.endswith(".gz") else open
        with file_context(file_name, 'rt') as f:
            for line in f:
                if line:
                    yield line

    def save_text_file(self, file_path: str, txt_data):
        """Намеренно не проверяется существование пути."""
        self.check_not_exists(file_path)
        with io.open(file_path, mode='w', encoding='utf-8') as output_f:
            output_f.write(txt_data)

    def save_json_file(self, file_path: str, json_data):
        """Намеренно не проверяется существование пути."""
        self.check_not_exists(file_path)
        with io.open(file_path, mode="w", encoding="utf-8") as json_file:  # noqa
            json.dump(json_data, json_file, sort_keys=True, indent=2, ensure_ascii=False)  # noqa


@singleton_decorator
class Config(Utils):
    """
    Параметры работы:
        report_size: количество url с наибольшим суммарным временем обработки для сохранены в отчете

        max_mismatch_percent: % при котором структура обрабатываемого файла считается корректной
        max_mismatch_count: количество промахов при котором структура считается корректной
        percent: % при котором и max_mismatch_count - связаны по принципу AND

        log_dir: каталог с обрабатываемыми логами
        log_name_pattern: регулярное выражение по которому будут искаться файлы с логами в каталоге log_dir
        log_name_date_pattern: формат даты для поиска в log_name_pattern
        report_dir: каталог для сохранятения итоговый отчет
        report_template_path: шаблон для генерации отчета
        template_replace_tag: тэг в шаблоне для замены
        date_fmt: внутренний формат даты для сравнения
        min_log_date: минимальная дата лога Nginx для поиска
        web_server_log_pattern: паттерн для разбора строк в логе Nginx

    Параметры логгирования работы:
        log_level: уровень логгирования
        logfile_format: формат лога выполнения
        logfile_date_format: формат даты для лога выполнения
        logfile_path: файл для записи лога выполнения (если не указан - только на stdout)
        ts_f_path: файл в который будет сохранено время завершения работы (аналогично stat -c %Y log_analyzer.ts)

    Служебные параметры:
        __extension: допустимое расширение/формат конфигурационного файла
    """

    def __init__(self, config_file: str = None):
        """Если config_file не передан - нет попытки прочитать файл."""

        self.__extension = ".json"
        self.report_size = 100
        self.max_mismatch_percent = 10
        self.max_mismatch_count = 10
        self.logfile_format = "[%(asctime)s] %(levelname).1s %(message)s"
        self.logfile_date_format = "%Y.%m.%d %H:%M:%S"
        self.date_fmt = "%Y%m%d"
        self.min_log_date = "19700101"
        self.log_dir = "log"
        self.log_name_pattern = r"nginx-access-ui\.log-[\d]{8}"
        self.log_name_date_pattern = r"[\d]{8}"
        self.report_dir = "reports"
        self.log_level = "INFO"
        self.report_template_path = "reports/report.html"
        self.template_replace_tag = "$table_json"
        self.web_server_log_pattern = r'^\S+\s\S+\s{2}\S+\s\[.*?\]\s\"\S+\s(\S+)\s\S+\"\s\S+\s\S+\s.+?\s\".+?\"\s\S+\s\S+\s\S+\s(\S+)'  # noqa

        # empty strings for proper config_template output
        self.logfile_path = ""
        self.ts_f_path = ""

        if config_file:
            self.load(config_file)

    @property
    def template_replace_tag(self):
        return self.__template_replace_tag

    @template_replace_tag.setter
    def template_replace_tag(self, tag: str):
        assert (isinstance(tag, str))
        self.__template_replace_tag = tag

    @property
    def report_template_path(self):
        return self.__report_template_path

    @report_template_path.setter
    def report_template_path(self, file_path: str):
        assert (isinstance(file_path, str))
        self.check_exists(file_path)
        self.__report_template_path = file_path

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
        self.check_exists(directory)
        self.__report_dir = directory

    @property
    def log_dir(self):
        return self.__log_dir

    @log_dir.setter
    def log_dir(self, directory: str):
        assert (isinstance(directory, str))
        self.check_exists(directory)
        self.__log_dir = directory

    @property
    def log_name_pattern(self):
        return self.__log_name_pattern

    @log_name_pattern.setter
    def log_name_pattern(self, pattern: str):
        assert (isinstance(pattern, str))
        self.__log_name_pattern = pattern

    @property
    def web_server_log_pattern(self):
        return self.__web_server_log_pattern

    @web_server_log_pattern.setter
    def web_server_log_pattern(self, pattern: str):
        assert (isinstance(pattern, str))
        self.__web_server_log_pattern = pattern

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
        self.check_exists(file_path_directory)
        self.__ts_f_path = file_path

    @property
    def log_level(self):
        return self.__log_level

    @log_level.setter
    def log_level(self, level: str):
        assert (isinstance(level, str))

        _logging_levels = {
            'CRITICAL': logging.CRITICAL,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'INFO': logging.INFO,
            'DEBUG': logging.DEBUG
        }

        level = _logging_levels.get(level.upper(), logging.ERROR)
        self.__log_level = logging.getLevelName(level)

    @property
    def logfile_path(self):
        return self.__logfile_path

    @logfile_path.setter
    def logfile_path(self, file_path: str):
        assert (isinstance(file_path, str))
        file_path_directory = os.path.dirname(file_path)
        self.check_exists(file_path_directory)
        self.__logfile_path = file_path

    def load(self, config_file):
        """Читаем параметры из конфигурационного файла и записываем в атрибуты класса."""  # noqa

        config_file = self.check_exists(config_file)
        self.check_extension(config_file, self.__extension)

        with io.open(config_file, mode="r", encoding="utf-8") as json_config:
            file_config = json.load(json_config)

        self.update(file_config)

    @classmethod
    def create_template(cls, file_path):
        """Создаем конфигурационный файл по атрибутам класса."""

        # For extra verbosity keys should be in upper register
        attrs = {k.upper(): v for k, v in cls().public_attrs().items()}
        cls.save_json_file(file_path, json_data=attrs)


@singleton_decorator
class Logging(Utils):
    """Logger configuration"""

    def __init__(self,
                 logfile_date_format: str,
                 logfile_format: str,
                 log_level=logging.INFO,
                 logfile_path: str = None,
                 **kwargs):

        self.root_logger = logging.getLogger('log_analyzer')
        self.root_logger.propagate = False

        self.file_handler = None
        self.stream_handler = logging.StreamHandler(stream=sys.stdout)

        self.logfile_format = logfile_format
        self.logfile_date_format = logfile_date_format
        self.logfile_path = logfile_path
        self.log_level = log_level
        self.apply()

    def update(self, config: dict):
        super().update(config)
        self.apply()

    def apply(self):
        """Применение конфигурации логгера."""

        formatter = logging.Formatter(fmt=self.logfile_format, datefmt=self.logfile_date_format)  # noqa
        if self.logfile_path:
            self.file_handler = logging.FileHandler(self.logfile_path)
            self.root_logger.removeHandler(self.stream_handler)

        handler = self.file_handler if self.logfile_path else self.stream_handler
        handler.setFormatter(formatter)
        handler.setLevel(self.log_level)

        self.root_logger.addHandler(handler)
        self.root_logger.setLevel(self.log_level)

        self.debug('Log configuration applied.')

    def debug(self, message: str):
        assert (isinstance(message, str))
        self.root_logger.debug(message)

    def info(self, message: str):
        assert (isinstance(message, str))
        self.root_logger.info(message)

    def warning(self, message: str):
        assert (isinstance(message, str))
        self.root_logger.warning(message)

    def error(self, message: str):
        assert (isinstance(message, str))
        self.root_logger.error(message)

    def critical(self, message: str):
        assert (isinstance(message, str))
        self.root_logger.critical(message)


class Analyzer(Utils):

    def __init__(self, config: Config, log: Logging):
        """
        log: собственный логгер для вывода сообщений
        TODO: description
        """

        self.__max_log_date = None
        self.root_logger = log

        self.date_fmt = config.date_fmt
        self.log_dir = config.log_dir
        self.nginx_log_name_re = config.log_name_pattern
        self.web_server_re = config.web_server_log_pattern
        self.log_name_date_re = config.log_name_date_pattern

        self.report_dir = config.report_dir
        self.max_mismatch_count = config.max_mismatch_count
        self.max_mismatch_percent = config.max_mismatch_percent
        self.report_size = config.report_size
        self.template_path = config.report_template_path
        self.replace_tag = config.template_replace_tag
        self.ts_f_path = config.ts_f_path
        self.min_log_date = self.str_to_date(config.min_log_date, config.date_fmt)  # noqa

        log.debug('Analyzer initialization complete.')

    @property
    def max_mismatch_count(self):
        return self.__max_mismatch_count

    @max_mismatch_count.setter
    @log_property_decorator
    def max_mismatch_count(self, count: int):
        assert isinstance(count, int)
        self.__max_mismatch_count = count

    @property
    def max_log_date(self):
        return self.__max_log_date

    @max_log_date.setter
    @log_property_decorator
    def max_log_date(self, log_date: datetime.date):
        assert (isinstance(log_date, datetime.date))
        self.__max_log_date = log_date

    @property
    def report_file_name(self):
        max_log_date = self.date_to_str(self.max_log_date, self.date_fmt)
        file_name = os.path.join(self.report_dir, 'report-{}.html'.format(max_log_date))
        self.check_not_exists(file_name)
        return file_name

    @property
    def nginx_log_name_re(self):
        return self.__nginx_log_name_re

    @nginx_log_name_re.setter
    @log_property_decorator
    def nginx_log_name_re(self, pattern: str):
        assert (isinstance(pattern, str))
        compiled_re = re.compile(pattern)
        self.__nginx_log_name_re = compiled_re

    @property
    def web_server_re(self):
        return self.__web_server_re

    @web_server_re.setter
    @log_property_decorator
    def web_server_re(self, pattern: str):
        assert (isinstance(pattern, str))
        compiled_re = re.compile(pattern)
        self.__web_server_re = compiled_re

    @property
    def log_name_date_re(self):
        return self.__log_name_date_re

    @log_name_date_re.setter
    @log_property_decorator
    def log_name_date_re(self, pattern: str):
        assert (isinstance(pattern, str))
        compiled_re = re.compile(pattern)
        self.__log_name_date_re = re.compile(compiled_re)

    @property
    def web_server_log_gen(self):
        """ Generator through web server logs """

        for __, __, file_list in os.walk(self.log_dir):
            for file in file_list:
                if self.nginx_log_name_re.match(file):
                    yield file

    @property
    def latest_log(self):
        """ Find the newest log in the self.log_dir """

        max_log_date, max_log_f_name = self.min_log_date, None

        for log_file in self.web_server_log_gen:
            log_date = self.str_to_date(self.log_name_date_re.search(log_file).group(),
                                        self.date_fmt)

            if log_date >= max_log_date:
                max_log_date = log_date
                max_log_f_name = os.path.join(self.log_dir, log_file)

        if max_log_f_name:
            self.max_log_date = max_log_date
            self.root_logger.debug('Latest Nginx log file: {}'.format(max_log_f_name))
            self.root_logger.debug('Max log date: {}'.format(max_log_date))
            return max_log_f_name

        raise FileExistsError('Web server log file not found.')

    def parse_line(self, log_line):
        """ Find the line in the log url and time """

        grp = self.web_server_re.match(log_line)
        if not grp:
            return

        col_names = ('request_url', 'request_time')
        parsed_line = (dict(zip(col_names, grp.groups())))
        if parsed_line['request_time'] == '-':
            parsed_line['request_time'] = 0
        parsed_line['request_time'] = float(parsed_line['request_time'])

        return parsed_line

    @staticmethod
    def median(numbers_list):
        """ Consider a median """

        numbers_list = sorted(numbers_list)
        return numbers_list[int(len(numbers_list) / 2)]

    def make_report(self, log_stat, total_count, total_time, limit=100):
        """ Make report with stats
            count - how many times does the url, the absolute value, occur
            count_percentage - how many times does a url occur as a percentage of the total number of requests  # noqa
            time_sum - total for this URL request_time, absolute value
            time_percent - total for this URL request_time, in percent relative to the total request_time all queries  # noqa
            time_avg - average request_time for a given URL
            time_max - request_time maximum for the given URL
            time_med - request_time median for the given URL

        """

        report_data = []
        for url, times in iter(log_stat.items()):
            count = len(times)
            count_percentage = count / float(total_count / 100)
            time_sum = sum(times)
            time_percent = time_sum / float(total_time / 100)
            time_avg = time_sum / count
            time_max = max(times)
            time_med = self.median(times)

            report_data.append({"count": count,
                                "time_avg": round(time_avg, 3),
                                "time_max": round(time_max, 3),
                                "time_sum": round(time_sum, 3),
                                "url": url,
                                "time_med": round(time_med, 3),
                                "time_percent": round(time_percent, 3),
                                "count_percentage": round(count_percentage, 3)
                                })

        report_data.sort(key=lambda x: x['time_sum'], reverse=True)

        return report_data[:limit]

    def insert_to_template(self, report_data: dict):
        """ Подставляет обработанные данные к шаблон """
        with io.open(self.template_path, mode='r', encoding='utf-8') as f:
            file_data = f.read()
            file_data = file_data.replace(self.replace_tag, json.dumps(report_data))
        return file_data

    def save_report(self, report_data, file_path: str):
        """Save the sample report file from reports/report.html"""

        pasted_data = self.insert_to_template(report_data)
        self.save_text_file(file_path, pasted_data)

    def start(self):
        """Обработчик для вызова"""

        self.root_logger.info('Analyzer begin to work. Unix time: {}'.format(self._ts_time))

        total_count = mismatch_count = total_matched_count = total_time = 0
        log_stat = collections.defaultdict(list)

        latest_log = self.latest_log
        report_file_name = self.report_file_name

        self.root_logger.debug('Latest log: {}'.format(latest_log))
        self.root_logger.debug('Report file name: {}'.format(report_file_name))

        for line in self.read_file_gen(latest_log):
            parsed_line = self.parse_line(line)
            total_count += 1

            if parsed_line:
                total_matched_count += 1
                total_time += parsed_line['request_time']
                log_stat[parsed_line['request_url']].append(parsed_line['request_time'])
            else:
                mismatch_count += 1

            mismatch_percent = (mismatch_count * 100) / total_count
            if (mismatch_count > self.max_mismatch_count) and (mismatch_percent > self.max_mismatch_percent):
                raise AssertionError('Mismatch exceeded. Check log format type')

        if total_matched_count == 0 or total_time == 0:
            raise AssertionError('No match during parser work. Something goes wrong.')

        log_report = self.make_report(log_stat, total_matched_count, total_time, self.report_size)  # noqa
        self.save_report(log_report, report_file_name)
        logging.info("Log parsed successfully")

    def stop(self):
        """Фиксирует время успешного завершения работы Analyzer."""

        ts_time = self._ts_time_str
        self.root_logger.info('Analyzer completed successfully. Unix time: {}'.format(ts_time))

        if self.ts_f_path:
            self.root_logger.info('TS file: {}'.format(self.ts_f_path))
            self.save_text_file(self.ts_f_path, ts_time)

    def run(self):
        """Запускает и останавливает Analyzer."""
        self.start()
        self.stop()


def parse_args():
    """Парсер входныъ аргументов.

       config: путь к конфигурационному файлу
       template: параметр для генерации конфигурационного файла

    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json', type=str,
                        help='Path to configuration file, ex: config.json')
    parser.add_argument('--template', default=False, type=bool,
                        help='Create config template')
    return parser.parse_args()


def main():
    """Инициализация, запуск и верхнеуровневая обработка исключений."""
    args = parse_args()
    log = Logging('%Y.%m.%d %H:%M:%S', '[%(asctime)s] %(levelname).1s %(message)s')

    if args.template:
        # TODO: test case
        Config().create_template(args.config)
        log.info('Configuration file template created.')
        sys.exit(0)

    user_config = Config(args.config)
    log.update(user_config.public_attrs())

    try:
        analyzer = Analyzer(config=user_config, log=log)
        analyzer.run()
    except (AssertionError, FileExistsError) as error_msg:
        log.critical(str(error_msg))
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
