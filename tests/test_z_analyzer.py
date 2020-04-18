"""Тесты класса Analyzer."""
import os
import unittest
import uuid

from log_analyzer import Analyzer, Config, Logging


class TestAnalyzer(unittest.TestCase):
    """Из-за сигнлтонов запускается последним."""

    @classmethod
    def setUpClass(cls) -> None:
        temp_uuid = str(uuid.uuid4())[:4]
        cls._ts_file = temp_uuid + '.ts'
        cls._temp_log = temp_uuid + '.log'
        config_dict = {'ts_f_path': cls._ts_file,
                       'log_dir': 'tests/mock_data/log',
                       'report_dir': 'tests/mock_data/reports',
                       'report_template_path': 'tests/mock_data/reports/report.html',
                       "log_level": "debug",
                       "logfile_path": cls._temp_log
                       }

        cls._config = Config()
        cls._config.update(config_dict)

        log = Logging('%H:%M:%S', '%(message)s')
        log.update(cls._config.public_attrs())
        cls._logger = log

    @classmethod
    def tearDownClass(cls) -> None:
        os.remove(cls._ts_file)
        os.remove(cls._temp_log)

    def setUp(self) -> None:
        self._instance_class_being_tested = Analyzer(self._config, self._logger)

    def test_stop(self):
        self._instance_class_being_tested.stop()
        self.assertTrue(True)

    def test_start(self):
        report_file_name = self._instance_class_being_tested.start()
        self.assertIsInstance(report_file_name, str)
        os.remove(report_file_name)


if __name__ == '__main__':
    unittest.main()
