"""Тесты класса Logging."""
import logging
import os
import unittest
import uuid

from log_analyzer import Logging


class TestLogging(unittest.TestCase):
    """Тесты логгера."""

    @property
    def last_log_line(self):
        with open(self._temp_log, 'r') as log_file:
            lines = log_file.readlines()
        return lines[-1]

    @classmethod
    def setUpClass(cls):
        cls._temp_log = str(uuid.uuid4())[:4] + '.log'
        cls._instance_class_being_tested = Logging('%Y.%m.%d %H:%M:%S', '[%(asctime)s] %(levelname).1s %(message)s',
                                                   log_level=logging.DEBUG,
                                                   logfile_path=cls._temp_log)

    @classmethod
    def tearDownClass(cls) -> None:
        os.remove(cls._temp_log)

    def test_debug_message(self):
        message = 'debug'
        self._instance_class_being_tested.debug(message)
        self.assertIn(message, self.last_log_line)

    def test_info_message(self):
        message = 'info'
        self._instance_class_being_tested.info('info')
        self.assertIn(message, self.last_log_line)

    def test_error_message(self):
        message = 'error'
        self._instance_class_being_tested.error('error')
        self.assertIn(message, self.last_log_line)

    def test_warning_message(self):
        message = 'warning'
        self._instance_class_being_tested.warning('warning')
        self.assertIn(message, self.last_log_line)

    def test_critical_message(self):
        message = 'critical'
        self._instance_class_being_tested.critical('critical')
        self.assertIn(message, self.last_log_line)

    def test_apply(self):
        self._instance_class_being_tested.apply()
        self.assertIn('Log configuration applied.', self.last_log_line)

    def test_update(self):
        message = 'TEST message'
        logging_config = {'logfile_date_format': '%Y-%m-%d',
                          'logfile_format': '[%(asctime)s] %(levelname)s %(message)s'}
        self._instance_class_being_tested.update(logging_config)
        self._instance_class_being_tested.info(message)
        self.assertIn(message, self.last_log_line)


if __name__ == '__main__':
    unittest.main()
