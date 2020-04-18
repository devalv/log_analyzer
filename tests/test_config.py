"""Тесты класса Config."""
import io
import json
import os
import unittest
import uuid


from log_analyzer import Config


class TestConfig(unittest.TestCase):
    """Намеренное разделение load и create_template."""

    def setUp(self) -> None:
        self._template_name = str(uuid.uuid4())[:4] + '.json'

    def tearDown(self) -> None:
        os.remove(self._template_name)

    def test_1_init_with_template(self):
        """Тест требует, чтобы ранее не было инстанса конфига."""
        json_data = {'max_mismatch_count': -1, 'max_mismatch_percent': -1}

        with io.open(self._template_name, mode="w", encoding="utf-8") as json_file:  # noqa
            json.dump(json_data, json_file, sort_keys=True, indent=2, ensure_ascii=False)  # noqa
        cfg = Config(self._template_name)
        self.assertEqual(1, cfg.max_mismatch_count)
        self.assertEqual(1, cfg.max_mismatch_percent)
        self.assertTrue(True)

    def test_create_template(self):
        cls = Config()
        cls.create_template(self._template_name)
        self.assertTrue(os.path.exists(self._template_name))

        with open(self._template_name) as config_file:
            config_dict = json.load(config_file)

        self.assertIsInstance(config_dict, dict)
        self.assertIn('LOG_DIR', config_dict)
        self.assertTrue(True)

    def test_load_template(self):
        cls = Config()
        cls.create_template(self._template_name)
        self.assertTrue(os.path.exists(self._template_name))

        with open(self._template_name) as config_file:
            file_data = config_file.read()

        file_data = file_data.replace('$table_json', '$edited_tag')

        with open(self._template_name, 'w') as config_file:
            config_file.write(file_data)

        cls.load(self._template_name)
        self.assertEqual('$edited_tag', cls.template_replace_tag)
        self.assertTrue(True)
