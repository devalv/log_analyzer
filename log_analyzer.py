#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# TODO: составить список доработок

# log_format ui_short '$remote_addr $remote_user $http_x_real_ip [$time_local] "$request" '
#                     '$status $body_bytes_sent "$http_referer" '
#                     '"$http_user_agent" "$http_x_forwarded_for" "$http_X_REQUEST_ID" "$http_X_RB_USER" '
#                     '$request_time';
import logging
import os
import re
import collections
import sys
import json
import datetime
import gzip
import time
import io


logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)

config = {
    "REPORT_SIZE": 1000,
    "REPORT_DIR": "./reports",
    "LOG_DIR": "./log"
}

log_search_pattern = re.compile('nginx-access-ui\.log-[0-9]{4}[0-9]{2}[0-9]{2}')
log_date = re.compile('[0-9]{4}[0-9]{2}[0-9]{2}')

web_server_LOG_SEARCH_PATTERNS = (r''
                                  r'^\S+\s\S+\s{2}\S+\s\[.*?\]\s'
                                  r'\"\S+\s(\S+)\s\S+\"\s'
                                  r'\S+\s\S+\s.+?\s\".+?\"\s\S+\s\S+\s\S+\s'
                                  r'(\S+)')
web_server_LOG_SEARCH = re.compile(web_server_LOG_SEARCH_PATTERNS)


def load_config(config_file):
    """ We try to read parameters of a config from a file.
        If everything is good - we return an updated config."""

    config_file = make_backup_path(config_file)
    if not os.path.exists(config_file):
        logging.error('Config file ' + config_file + ' not exists. Exit')
        sys.exit(1)

    logging.info('Config file exists. Check file extension')
    __, file_ext = os.path.splitext(config_file)
    if file_ext != '.json':
        logging.error('Config file must have ".json" extension')
        sys.exit(1)

    with io.open(config_file, mode="r", encoding="utf-8") as json_config:
        user_config = json.load(json_config)
    logging.info('Config file parsed. If LOGFILE_PATH variable is set - begin write log to file')
    config.update(user_config)
    return config


def make_backup_path(file_path):
    """If you can not find the file on the path passed
     - we imagine that it lies in the directory with the script"""

    if not os.path.exists(file_path):
        file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), file_path)
    return file_path


def make_web_server_logs_list(log_dir):
    """ Make a list of web server logs """

    web_server_logs_list = []
    for __, __, filelist in os.walk(log_dir):
        for file in filelist:
            if log_search_pattern.match(file):
                web_server_logs_list.append(file)
    return web_server_logs_list


def find_max_log_date(web_server_logs_list):
    """Find max log date in list"""

    max_log_date = datetime.datetime.strptime(log_date.search(web_server_logs_list[0]).group(), '%Y%m%d').date()
    max_log_f_name = web_server_logs_list[0]
    for web_server_log_file in web_server_logs_list:
        local_log_date = datetime.datetime.strptime(log_date.search(web_server_log_file).group(), '%Y%m%d').date()
        if local_log_date > max_log_date:
            max_log_date = local_log_date
            max_log_f_name = web_server_log_file
    return max_log_f_name


def find_log(log_dir):
    """ Find the newest log in the list """

    max_log_f_name = None
    web_server_logs_list = make_web_server_logs_list(log_dir)
    if len(web_server_logs_list) > 0:
        max_log_f_name = find_max_log_date(web_server_logs_list)
        logging.info('Found web_server log-files: ' + ', '.join(web_server_logs_list))
    else:
        logging.info('web_server log-file not found')

    return max_log_f_name


def read_log(log_f_name):
    """ Line by line read the log file """
    # TODO: Такое использование менеджера контекста кажется сомнительным

    if log_f_name.endswith(".gz"):
        log_type = gzip.open
    else:
        log_type = open

    with log_type(log_f_name, 'rt') as log:
        for line in log:
            if line:
                yield line


def parse_line(log_line):
    """ Find the line in the log url and time """

    grp = web_server_LOG_SEARCH.match(log_line)
    if grp:
        col_names = ('request_url', 'request_time')
        parsed_line = (dict(zip(col_names, grp.groups())))
        if parsed_line['request_time'] != '-':
            parsed_line['request_time'] = float(parsed_line['request_time'])
        else:
            parsed_line['request_time'] = 0
        return parsed_line
    return None


def add_file_logging(logfile,
                     log_format='[%(asctime)s] %(levelname).1s %(message)s',
                     log_date_format="%Y.%m.%d %H:%M:%S"):
    """ Duplicate the log of the script in the file """

    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(log_format, datefmt=log_date_format)
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)


def goodbye(ts_f_path):
    """ Save the timestamp to a file and exit """

    logging.info('Program completed successfully. TS-file:' + str(ts_f_path))
    with io.open(ts_f_path, mode='w', encoding='utf-8') as ts_file:
        ts_time = str(round(time.time(), 0))
        ts_file.write(ts_time.encode().decode())
    sys.exit(0)


def parse_args():
    """ We look for in arguments a path to the file with a config """

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json', type=str, nargs='+',
                        help='Path to configuration file in JSON format, ex: /var/log/config.json')
    return parser.parse_args()


def save_report(report, file_path):
    """ Save the sample report file from reports/report.html """

    with io.open(make_backup_path('reports/report.html'), mode='r', encoding='utf-8') as f:
        file_data = f.read()
    file_data = file_data.replace('$table_json', json.dumps(report))
    with io.open(file_path, mode='w', encoding='utf-8') as f:
        f.write(file_data)


def median(numbers_list):
    """ Consider a median """

    numbers_list = sorted(numbers_list)
    return numbers_list[int(len(numbers_list) / 2)]


def make_report(log_stat, total_count, total_time, limit=100):
    """ Make report with stats
        count - how many times does the url, the absolute value, occur
        count_perc - how many times does a url occur as a percentage of the total number of requests
        time_sum - total for this URL request_time, absolute value
        time_perc - total for this URL request_time, in percent relative to the total request_time all queries
        time_avg - average request_time for a given URL
        time_max - request_time maximum for the given URL
        time_med - request_time median for the given URL
    """

    report_data = []
    for url, times in log_stat.items():
        count = len(times)
        count_perc = count / float(total_count / 100)
        time_sum = sum(times)
        time_perc = time_sum / float(total_time / 100)
        time_avg = time_sum / count
        time_max = max(times)
        time_med = median(times)

        report_data.append({"count": count,
                            "time_avg": round(time_avg, 3),
                            "time_max": round(time_max, 3),
                            "time_sum": round(time_sum, 3),
                            "url": url,
                            "time_med": round(time_med, 3),
                            "time_perc": round(time_perc, 3),
                            "count_perc": round(count_perc, 3)
                            })

    report_data.sort(key=lambda x: x['time_sum'], reverse=True)

    return report_data[:limit]


def main():
    try:
        args = parse_args()
        user_config = load_config(args.config)

        if user_config.get('LOGFILE_PATH'):
            add_file_logging(make_backup_path(user_config['LOGFILE_PATH']))

        last_log_name = find_log(make_backup_path(user_config['LOG_DIR']))

        if last_log_name:
            report_date_format = datetime.datetime.strptime(log_date.search(last_log_name).group(), '%Y%m%d').strftime(
                '%Y.%m.%d')
            report_file_name = os.path.join(
                make_backup_path(user_config.get('REPORT_DIR')),
                'report-' + report_date_format + '.html')
            logging.info('Check ' + report_file_name + ' for exist')

            if os.path.exists(report_file_name):
                logging.info('Report file already exists. Exit')
                goodbye(user_config.get('TS_F_PATH', 'log_analyzer.ts'))

            logging.info('report file not found. Begin to parse')
            logging.info('Will parse ' + last_log_name)
            total_count = mismatch_count = total_matched_count = total_time = 0
            log_stat = collections.defaultdict(list)
            last_log_name = os.path.join(make_backup_path(user_config.get('LOG_DIR')), last_log_name)

            for line in read_log(last_log_name):
                parsed_line = parse_line(line)
                total_count += 1
                if parsed_line:
                    total_matched_count += 1
                    total_time += parsed_line['request_time']
                    log_stat[parsed_line['request_url']].append(parsed_line['request_time'])
                else:
                    mismatch_count += 1

                if (mismatch_count > 10) and (
                        (mismatch_count * 100) / total_count > user_config.get('MAX_MISMATCH_PERC', 10)):
                    logging.error('Mismatch count exceeded. Check web_server log format type')
                    sys.exit(1)

            if total_matched_count > 0 and total_time > 0:
                log_report = make_report(log_stat, total_matched_count, total_time, user_config.get('REPORT_SIZE'))
                save_report(log_report, report_file_name)
                logging.info("Log parsed successfully")

    except Exception as E:
        logging.exception(E, exc_info=True)
    else:
        goodbye(user_config.get('TS_F_PATH', 'log_analyzer.ts'))


if __name__ == '__main__':
    main()