# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import logging
import unittest

from aas_compliance_tool.state_manager import ComplianceToolStateManager, Status
from basyx.aas.examples.data._helper import DataChecker


class ComplianceToolStateManagerTest(unittest.TestCase):
    def test_state(self) -> None:
        manager = ComplianceToolStateManager()
        manager.add_step('test')
        self.assertEqual(Status.NOT_EXECUTED, manager.status)
        manager.set_step_status(Status.SUCCESS)
        self.assertEqual(Status.SUCCESS, manager.status)
        manager.set_step_status(Status.FAILED)
        self.assertEqual(Status.FAILED, manager.status)

    def test_logs(self) -> None:
        manager = ComplianceToolStateManager()
        manager.add_step('test')
        manager.add_log_record(logging.LogRecord('x', logging.INFO, '', 0, 'test_msg', (), None))
        self.assertEqual(0, len(manager.get_error_logs_from_step(0)))
        manager.add_log_record(logging.LogRecord('x', logging.ERROR, '', 0, 'test_msg_2', (), None))
        self.assertEqual(1, len(manager.get_error_logs_from_step(0)))

        manager.add_step('test 2')
        checker = DataChecker(raise_immediately=False)
        checker.check(2 == 2, 'Assertion test')

        manager.add_log_records_from_data_checker(checker)
        self.assertEqual(0, len(manager.get_error_logs_from_step(1)))
        self.assertEqual('SUCCESS:      test 2', manager.format_step(1, 1))
        self.assertEqual('SUCCESS:      test 2', manager.format_step(1, 1))
        self.assertIn('INFO:  Assertion test ()', manager.format_step(1, 2))

        checker.check(2 == 1, 'Assertion test 2')
        manager.add_log_records_from_data_checker(checker)
        self.assertEqual(1, len(manager.get_error_logs_from_step(1)))
        self.assertEqual('FAILED:       test 2', manager.format_step(1))
        self.assertIn('ERROR: Assertion test 2 ()', manager.format_step(1, 1))
        self.assertIn('INFO:  Assertion test ()', manager.format_step(1, 2))
