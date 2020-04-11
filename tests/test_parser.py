import unittest
from log_analyzer import *


class TestMain(unittest.TestCase):
    """Simple tests"""

    def test_find_max_log_date(self):
        """ Check that max log date works fine """

        log_dates_list = [
            'nginx-access-ui.log-20170630.gz',
            'nginx-access-ui.log-20170131.gz',
            'nginx-access-ui.log-20170228.gz',
            'nginx-access-ui.log-20170430.gz',

        ]

        max_log_date = find_max_log_date(log_dates_list)
        self.assertEqual('nginx-access-ui.log-20170630.gz', max_log_date)

    def test_read_config(self):
        """ Try to read config from file """

        try:
            load_config(config_file="config.json")
        except:
            self.fail("fail to read config")

    def test_save_report(self):
        """Try to write report file"""

        try:
            report_data = [
                {'count': 2767,
                 'time_avg': 62.995,
                 'time_max': 9843.569,
                 'time_sum': 174306.352,
                 'url': '/api/v2/internal/html5/phantomjs/queue/?wait=1m',
                 'time_med': 60.073,
                 'time_perc': 9.043,
                 'count_perc': 0.106}
            ]

            report_file_name = 'report-2017.99.99.html'

            save_report(report_data, report_file_name)
        except:
            self.fail("fail to save report")

    def test_parsing_check(self):
        """Check that log prases right"""

        right_example_line = """1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" 0.390"""
        wrong_example_line = """1.196.116.32 -  - [29/Jun/2017:03:50:22 +0300] "GET /api/v2/banner/25019354 HTTP/1.1" 200 927 "-" "Lynx/2.8.8dev.9 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/2.10.5" "-" "1498697422-2190034393-4708-9752759" "dc7161be3" """

        self.assertEqual(2, len(parse_line(right_example_line)))
        self.assertEqual(None, parse_line(wrong_example_line))