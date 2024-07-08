import powerdns

from logging import Logger
from unittest import TestCase


class TestLogger(TestCase):

    def test_logger_creation(self):
        self.assertIsInstance(powerdns.basic_logger("test", 2, 1), Logger)
