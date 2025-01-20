# Copyright (c) 2024 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

"""
Command line script which is a compliance tool for creating and checking json and xml files in compliance with
"Details of the Asset Administration Shell" specification of Plattform Industrie 4.0. It uses the create_example() from
examples.data.__init__.py
"""
import argparse
import datetime

import logging

import pyecma376_2

from basyx.aas.adapter import aasx
from basyx.aas.adapter.xml import write_aas_xml_file
from aas_compliance_tool import compliance_check_xml as compliance_tool_xml, \
    compliance_check_json as compliance_tool_json, \
    compliance_check_aasx as compliance_tool_aasx
from basyx.aas.adapter.json import write_aas_json_file
from basyx.aas.examples.data import create_example, create_example_aas_binding, TEST_PDF_FILE
from aas_compliance_tool.state_manager import ComplianceToolStateManager, Status


def parse_cli_arguments() -> argparse.ArgumentParser:
    """
    This function returns the argument-parser for the cli
    """
    parser = argparse.ArgumentParser(
        prog='compliance_tool',
        description='Compliance tool for creating and checking json and xml files in compliance with "Details of the '
                    'Asset Administration Shell" specification of Plattform Industrie 4.0. \n\n'
                    'This tool has five features: \n'
                    '1. create a xml or json file or an AASX file using xml or json files with example aas elements\n'
                    '2. check if a given xml or json file is compliant with the official json or xml aas schema and '
                    'is deserializable\n'
                    '3. check if the data in a given xml, json or aasx file is the same as the example data\n'
                    '4. check if two given xml, json or aasx files contain the same aas elements in any order\n\n'
                    'As a first argument, the feature must be specified (create, schema, deserialization, example, '
                    'files) or in short (c, s, d, e or f).\n'
                    'Depending the chosen feature, different additional arguments must be specified:\n'
                    'create or c:          path to the file which shall be created (file_1)\n'
                    'deseriable or d:      file to be checked (file_1)\n'
                    'example or e:         file to be checked (file_1)\n'
                    'file_compare or f:    files to compare (file_1, file_2)\n,'
                    'In any case, it must be specified whether the (given or created) files are json (--json) or '
                    'xml (--xml).\n'
                    'All features except "schema" support reading/writing AASX packages instead of plain XML or JSON '
                    'files via the --aasx option.\n\n'
                    'Additionally, the tool offers some extra features for more convenient usage:\n\n'
                    'a. Different levels of verbosity:\n'
                    '   Default output is just the status for each step performed. With -v or --verbose, additional '
                    'information in case of status = FAILED will be provided. With one more -v or --verbose, additional'
                    ' information even in case of status = SUCCESS or WARNINGS will be provided.\n'
                    'b. Suppressing output on success:\n'
                    '   With -q or --quite no output will be generated if the status = SUCCESS.\n'
                    'c. Save log additionally in a logfile:\n'
                    '   With -l or --logfile, a path to the file where the logfiles shall be created can be specified.',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('action', choices=['create', 'c', 'schema', 's', 'deserialization', 'd', 'example', 'e',
                                           'files', 'f'],
                        help='c or create: creates a file with example data\n'
                             'd or deserialization: checks if a given file is compliance with the official schema and '
                             'is deserializable\n'
                             'e or example: checks if a given file contains the example aas elements\n'
                             'f or file_compare: checks if two given files contain the same aas elements in any order')
    parser.add_argument('file_1', help="path to file 1")
    parser.add_argument('file_2', nargs='?', default=None, help="path to file 2: is required if action f or files is "
                                                                "chosen")
    parser.add_argument('-v', '--verbose', help="Print detailed information for each check. Multiple -v options "
                                                "increase the verbosity. 1: Detailed error information, 2: Additional "
                                                "detailed success information", action='count', default=0)
    parser.add_argument('-q', '--quite', help="no information output if successful", action='store_true')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--json', help="Use AAS json format when checking or creating files", action='store_true')
    group.add_argument('--xml', help="Use AAS xml format when checking or creating files", action='store_true')
    parser.add_argument('-l', '--logfile', help="Log file to be created in addition to output to stdout", default=None)
    parser.add_argument('--aasx', help="Create or read AASX files", action='store_true')
    parser.add_argument('--dont-check-extensions', help="Don't compare Extensions", action='store_false')
    return parser


def main():
    parser = parse_cli_arguments()
    args = parser.parse_args()

    # Todo try to find out in which format the file is if not --json or --xml

    manager = ComplianceToolStateManager()
    logger = logging.getLogger(__name__)
    logger.propagate = False
    logger.addHandler(manager)

    data_checker_kwargs = {
        'check_extensions': args.dont_check_extensions
    }

    if args.action == 'create' or args.action == 'c':
        manager.add_step('Create example data')
        if args.aasx:
            data = create_example_aas_binding()
        else:
            data = create_example()
        manager.set_step_status(Status.SUCCESS)
        try:
            manager.add_step('Open file')
            if args.aasx:
                with aasx.AASXWriter(args.file_1) as writer:
                    manager.set_step_status(Status.SUCCESS)
                    manager.add_step('Write data to file')

                    files = aasx.DictSupplementaryFileContainer()
                    with open(TEST_PDF_FILE, 'rb') as f:
                        files.add_file("/TestFile.pdf", f, "application/pdf")

                    # Create OPC/AASX core properties
                    cp = pyecma376_2.OPCCoreProperties()
                    cp.created = datetime.datetime(2020, 1, 1, 0, 0, 0)
                    cp.creator = "Eclipse BaSyx Python Testing Framework"
                    cp.description = "Test_Description"
                    cp.lastModifiedBy = "Eclipse BaSyx Python Testing Framework Compliance Tool"
                    cp.modified = datetime.datetime(2020, 1, 1, 0, 0, 1)
                    cp.revision = "1.0"
                    cp.version = "2.0.1"
                    cp.title = "Test Title"

                    writer.write_aas_objects("/aasx/data.json" if args.json else "/aasx/data.xml",
                                             [obj.id for obj in data], data, files,
                                             write_json=args.json)
                    writer.write_core_properties(cp)
                manager.set_step_status(Status.SUCCESS)
            elif args.json:
                with open(args.file_1, 'w', encoding='utf-8-sig') as file:
                    manager.set_step_status(Status.SUCCESS)
                    manager.add_step('Write data to file')
                    write_aas_json_file(file=file, data=data, indent=4)
                    manager.set_step_status(Status.SUCCESS)
            elif args.xml:
                with open(args.file_1, 'wb') as file:
                    manager.set_step_status(Status.SUCCESS)
                    manager.add_step('Write data to file')
                    write_aas_xml_file(file=file, data=data, pretty_print=True)
                    manager.set_step_status(Status.SUCCESS)
        except IOError as error:
            logger.error(error)
            manager.set_step_status(Status.FAILED)
    elif args.action == 'deserialization' or args.action == 'd':
        if args.aasx:
            compliance_tool_aasx.check_deserialization(args.file_1, manager)
        elif args.json:
            compliance_tool_json.check_deserialization(args.file_1, manager)
        elif args.xml:
            compliance_tool_xml.check_deserialization(args.file_1, manager)
    elif args.action == 'example' or args.action == 'e':
        if args.aasx:
            compliance_tool_aasx.check_aas_example(args.file_1, manager, **data_checker_kwargs)
        elif args.json:
            compliance_tool_json.check_aas_example(args.file_1, manager, **data_checker_kwargs)
        elif args.xml:
            compliance_tool_xml.check_aas_example(args.file_1, manager, **data_checker_kwargs)
    elif args.action == 'files' or args.action == 'f':
        if args.file_2:
            if args.aasx:
                compliance_tool_aasx.check_aasx_files_equivalence(args.file_1, args.file_2, manager,
                                                                  **data_checker_kwargs)
            elif args.json:
                compliance_tool_json.check_json_files_equivalence(args.file_1, args.file_2, manager,
                                                                  **data_checker_kwargs)
            elif args.xml:
                compliance_tool_xml.check_xml_files_equivalence(args.file_1, args.file_2, manager,
                                                                **data_checker_kwargs)
        else:
            parser.error("f or files requires two file path.")
            exit()

    if manager.status is Status.SUCCESS and args.quite:
        exit()

    print(manager.format_state_manager(args.verbose))

    if args.logfile:
        try:
            with open(args.logfile, 'w', encoding='utf-8-sig') as file:
                file.write(manager.format_state_manager(args.verbose))
        except IOError as error:
            print('Could not open logfile: \n{}'.format(error))


if __name__ == "__main__":
    main()
