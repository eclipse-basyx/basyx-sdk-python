# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module defines a :class:`~.ComplianceToolStateManager` to store :class:`LogRecords <logging.LogRecord>`
for single steps in a compliance check of the compliance tool
"""
import logging
import enum
import pprint
from typing import List, Dict
from basyx.aas.examples.data._helper import DataChecker


@enum.unique
class Status(enum.IntEnum):
    """
    Possible Status States:

    :cvar SUCCESS:
    :cvar SUCCESS_WITH_WARNINGS:
    :cvar FAILED:
    :cvar NOT_EXECUTED:
    """
    SUCCESS = 0
    SUCCESS_WITH_WARNINGS = 1
    FAILED = 2
    NOT_EXECUTED = 3


class Step:
    """
    A step represents a single test stage in a test protocol of a :class:`~.ComplianceToolStateManager`

    :ivar name: Name of the step
    :ivar status: Status of the step from type Status
    :ivar log_list: List of :class:`LogRecords <logging.LogRecord>` which belong to this step
    """
    def __init__(self, name: str, status: Status, log_list: List[logging.LogRecord]):
        self.name = name
        self.status = status
        self.log_list = log_list


class ComplianceToolStateManager(logging.Handler):
    """
    A ComplianceToolStateManager is used to create a report of a compliance check, divided into single
    :class:`Steps <.Step>` with status and log. The manager provides methods to:

        - Add a new step
        - Set the step status
        - Set the step status from log
        - Add logs to a step by hand
        - Add logs to a step from a data checker
        - Be used as a :class:`logging.Handler` which adds logs to the current step

    Example of a ComplianceTest for a schema check:

        * Step 1: `Open file`
        * Step 2: `Read file and check if it is conform to the json syntax`
        * Step 3: `Validate file against official json schema`

    :ivar steps: List of :class:`Steps <.Step>`
    """
    def __init__(self):
        """
        steps: List of steps. Each step consist of a step name, a step status and LogRecords belong to to this step.
               The step name have to be unique in the list.
        """
        super().__init__()
        self.steps: List[Step] = []
        self.setLevel(logging.INFO)

    @property
    def status(self) -> Status:
        """
        Determine the status of all steps in following way:
        1. If there is at least one step with status = NOT_EXECUTED than NOT_EXECUTED will be returned
        2. If there is at least one step with status = FAILED than FAILED will be returned
        3. Else status SUCCESS will be returned

        :return: status of the manager
        """
        status: Status = Status.SUCCESS
        for step in self.steps:
            if status < step.status:
                status = step.status
        return status

    def add_step(self, name: str) -> None:
        """
        Adding a new :class:`~.Step` to the manager with a given name, status = NOT_EXECUTED and an empty list of
        records

        :param name: Name of the :class:`~.Step`
        """
        self.steps.append(Step(name, Status.NOT_EXECUTED, []))

    def add_log_record(self, record: logging.LogRecord) -> None:
        """
        Adds a :class:`~logging.LogRecord` to the log list of the actual :class:`~.Step`

        :param record: :class:`~logging.LogRecord` which should be added to the current :class:`~.Step`
        """
        self.steps[-1].log_list.append(record)

    def set_step_status(self, status: Status) -> None:
        """
        Sets the status of the current step

        :param status: status which should be set
        """
        self.steps[-1].status = status

    def set_step_status_from_log(self) -> None:
        """
        Sets the status of the current step based on the log entries
        """
        self.steps[-1].status = Status.FAILED if len(self.steps[-1].log_list) > 0 else Status.SUCCESS

    def add_log_records_from_data_checker(self, data_checker: DataChecker) -> None:
        """
        Sets the status of the current :class:`~.Step` and convert the checks to
        :class:`LogRecords <logging.LogRecord>` and adds these to the current :class:`~.Step`

        :class:`~.Step`: FAILED if the :class:`~basyx.aas.examples.data._helper.DataChecker` consist at least one failed
        check otherwise SUCCESS

        :param data_checker: :class:`~basyx.aas.examples.data._helper.DataChecker` which checks should be added to the
            current :class:`~.Step`
        """
        self.steps[-1].status = Status.SUCCESS if not any(True for _ in data_checker.failed_checks) else Status.FAILED
        for check in data_checker.checks:
            self.steps[-1].log_list.append(logging.LogRecord(name=__name__,
                                                             level=logging.INFO if check.result else logging.ERROR,
                                                             pathname='',
                                                             lineno=0,
                                                             msg="{} ({})".format(
                                                                 check.expectation,
                                                                 ", ".join("{}={}".format(
                                                                     k, pprint.pformat(
                                                                         v, depth=2, width=2 ** 14, compact=True))
                                                                           for k, v in check.data.items())),
                                                             args=(),
                                                             exc_info=None))

    def get_error_logs_from_step(self, index: int) -> List[logging.LogRecord]:
        """
        Returns a list of :class:`LogRecords <logging.LogRecord>` of a step where the log level
        is :data:`~logging.ERROR` or :data:`~logging.WARNING`

        :param index: Step index in the Step list of the manager
        :return: List of LogRecords with log level :data:`~logging.ERROR` or :data:`~logging.WARNING`
        """
        return [x for x in self.steps[index].log_list if x.levelno >= logging.WARNING]

    def format_step(self, index: int, verbose_level: int = 0) -> str:
        """
        Creates a string for the step containing the status, the step name and
        the :class:`LogRecords <logging.LogRecord>` if wanted

        :param index:  Step index in the step list of the manager
        :param verbose_level: Decision which kind of LogRecords should be in the string

                                - 0: No LogRecords
                                - 1: Only LogRecords with log level >= :data:`~logging.WARNING`
                                - 2: All LogRecords

        :return: formatted string of the step
        """
        STEP_STATUS: Dict[Status, str] = {
            Status.SUCCESS: '{:14}'.format('SUCCESS:'),
            Status.SUCCESS_WITH_WARNINGS: '{:14}'.format('WARNINGS:'),
            Status.FAILED: '{:14}'.format('FAILED:'),
            Status.NOT_EXECUTED: '{:14}'.format('NOT_EXECUTED:'),
            }
        if self.steps[index].status not in STEP_STATUS:
            raise NotImplementedError
        string = STEP_STATUS[self.steps[index].status]

        string += self.steps[index].name
        if verbose_level > 0:
            for log in self.steps[index].log_list:
                if log.levelno < logging.WARNING:
                    if verbose_level == 1:
                        continue
                string += '\n'+' - {:6} {}'.format(log.levelname + ':', log.getMessage())
        return string

    def format_state_manager(self, verbose_level: int = 0) -> str:
        """
        Creates a report with all executed steps: Containing the status, the step name and
        the :class:`LogRecords <logging.LogRecord>` if wanted

        :param verbose_level: Decision which kind of LogRecords should be in the string

                                - 0: No LogRecords
                                - 1: Only LogRecords with log level >= :data:`~logging.WARNING`
                                - 2: All LogRecords

        :return: formatted report
        """
        string = 'Compliance Test executed:\n'
        string += "\n".join(self.format_step(x, verbose_level) for x in range(len(self.steps)))
        return string

    def emit(self, record: logging.LogRecord):
        """
        :class:`~logging.Handler` function for adding :class:`LogRecords <logging.LogRecord>` from a ``logger``
        to the current :class:`~.Step`

        :param record: :class:`~logging.LogRecord` which should be added
        """
        self.steps[-1].log_list.append(record)
