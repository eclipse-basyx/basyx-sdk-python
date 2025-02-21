# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import os
import unittest

from aas_compliance_tool import compliance_check_json as compliance_tool
from aas_compliance_tool.state_manager import ComplianceToolStateManager, Status


class ComplianceToolJsonTest(unittest.TestCase):
    def test_check_schema(self) -> None:
        manager = ComplianceToolStateManager()
        script_dir = os.path.dirname(__file__)
        file_path_1 = os.path.join(script_dir, 'files/test_not_found.json')
        compliance_tool.check_schema(file_path_1, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.FAILED, manager.steps[0].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[1].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[2].status)
        self.assertIn("No such file or directory", manager.format_step(0, verbose_level=1))

        manager.steps = []
        file_path_2 = os.path.join(script_dir, 'files/test_not_deserializable.json')
        compliance_tool.check_schema(file_path_2, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.FAILED, manager.steps[1].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[2].status)
        self.assertIn("Expecting ',' delimiter: line 4 column 2 (char 54)", manager.format_step(1, verbose_level=1))

        manager.steps = []
        file_path_3 = os.path.join(script_dir, 'files/test_empty.json')
        compliance_tool.check_schema(file_path_3, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)

        manager.steps = []
        file_path_4 = os.path.join(script_dir, 'files/test_demo_full_example.json')
        compliance_tool.check_schema(file_path_4, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)

        manager.steps = []
        file_path_5 = os.path.join(script_dir, 'files/test_demo_full_example_wrong_attribute.json')
        compliance_tool.check_schema(file_path_5, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)

    def test_check_deserialization(self) -> None:
        manager = ComplianceToolStateManager()
        script_dir = os.path.dirname(__file__)

        file_path_1 = os.path.join(script_dir, 'files/test_not_found.json')
        compliance_tool.check_deserialization(file_path_1, manager)
        self.assertEqual(2, len(manager.steps))
        self.assertEqual(Status.FAILED, manager.steps[0].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[1].status)
        self.assertIn("No such file or directory", manager.format_step(0, verbose_level=1))

        manager.steps = []
        file_path_2 = os.path.join(script_dir, 'files/test_not_deserializable_aas.json')
        compliance_tool.check_deserialization(file_path_2, manager)
        self.assertEqual(2, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.FAILED, manager.steps[1].status)
        self.assertIn('Found JSON object with modelType="Test", which is not a known AAS class',
                      manager.format_step(1, verbose_level=1))

        manager.steps = []
        file_path_3 = os.path.join(script_dir, 'files/test_deserializable_aas_warning.json')
        compliance_tool.check_deserialization(file_path_3, manager)
        self.assertEqual(2, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.FAILED, manager.steps[1].status)
        self.assertIn("Ignoring 'revision' attribute of AdministrativeInformation object due to missing 'version'",
                      manager.format_step(1, verbose_level=1))

        manager.steps = []
        file_path_4 = os.path.join(script_dir, 'files/test_empty.json')
        compliance_tool.check_deserialization(file_path_4, manager)
        self.assertEqual(2, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)

        manager.steps = []
        file_path_4 = os.path.join(script_dir, 'files/test_empty.json')
        compliance_tool.check_deserialization(file_path_4, manager)
        self.assertEqual(2, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)

    def test_check_aas_example(self) -> None:
        manager = ComplianceToolStateManager()
        script_dir = os.path.dirname(__file__)

        file_path_2 = os.path.join(script_dir, 'files/test_demo_full_example.json')
        compliance_tool.check_aas_example(file_path_2, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)

        manager.steps = []
        file_path_1 = os.path.join(script_dir, 'files/test_not_deserializable_aas.json')
        compliance_tool.check_aas_example(file_path_1, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.FAILED, manager.steps[1].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[2].status)
        self.assertIn('Found JSON object with modelType="Test", which is not a known AAS class',
                      manager.format_step(1, verbose_level=1))

        manager.steps = []
        file_path_3 = os.path.join(script_dir, 'files/test_demo_full_example_wrong_attribute.json')
        compliance_tool.check_aas_example(file_path_3, manager)
        self.assertEqual(3, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.FAILED, manager.steps[2].status)
        self.assertEqual('FAILED:       Check if data is equal to example data\n - ERROR: Attribute id_short of '
                         'AssetAdministrationShell[https://acplt.org/Test_AssetAdministrationShell] must be == '
                         'TestAssetAdministrationShell (value=\'TestAssetAdministrationShell123\')',
                         manager.format_step(2, verbose_level=1))

    def test_check_json_files_equivalence(self) -> None:
        manager = ComplianceToolStateManager()
        script_dir = os.path.dirname(__file__)

        file_path_1 = os.path.join(script_dir, 'files/test_not_deserializable_aas.json')
        file_path_2 = os.path.join(script_dir, 'files/test_empty.json')
        compliance_tool.check_json_files_equivalence(file_path_1, file_path_2, manager)
        self.assertEqual(5, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.FAILED, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)
        self.assertEqual(Status.SUCCESS, manager.steps[3].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[4].status)

        manager.steps = []
        compliance_tool.check_json_files_equivalence(file_path_2, file_path_1, manager)
        self.assertEqual(5, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)
        self.assertEqual(Status.FAILED, manager.steps[3].status)
        self.assertEqual(Status.NOT_EXECUTED, manager.steps[4].status)

        manager.steps = []
        file_path_3 = os.path.join(script_dir, 'files/test_demo_full_example.json')
        file_path_4 = os.path.join(script_dir, 'files/test_demo_full_example.json')
        compliance_tool.check_json_files_equivalence(file_path_3, file_path_4, manager)
        self.assertEqual(5, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)
        self.assertEqual(Status.SUCCESS, manager.steps[3].status)
        self.assertEqual(Status.SUCCESS, manager.steps[4].status)

        manager.steps = []
        file_path_3 = os.path.join(script_dir, 'files/test_demo_full_example.json')
        file_path_4 = os.path.join(script_dir, 'files/test_demo_full_example_wrong_attribute.json')
        compliance_tool.check_json_files_equivalence(file_path_3, file_path_4, manager)
        self.assertEqual(5, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)
        self.assertEqual(Status.SUCCESS, manager.steps[3].status)
        self.assertEqual(Status.FAILED, manager.steps[4].status)
        self.assertEqual('FAILED:       Check if data in files are equal\n - ERROR: Attribute id_short of '
                         'AssetAdministrationShell[https://acplt.org/Test_AssetAdministrationShell] must be == '
                         'TestAssetAdministrationShell123 (value=\'TestAssetAdministrationShell\')',
                         manager.format_step(4, verbose_level=1))

        manager.steps = []
        compliance_tool.check_json_files_equivalence(file_path_4, file_path_3, manager)
        self.assertEqual(5, len(manager.steps))
        self.assertEqual(Status.SUCCESS, manager.steps[0].status)
        self.assertEqual(Status.SUCCESS, manager.steps[1].status)
        self.assertEqual(Status.SUCCESS, manager.steps[2].status)
        self.assertEqual(Status.SUCCESS, manager.steps[3].status)
        self.assertEqual(Status.FAILED, manager.steps[4].status)
        self.assertEqual('FAILED:       Check if data in files are equal\n - ERROR: Attribute id_short of '
                         'AssetAdministrationShell[https://acplt.org/Test_AssetAdministrationShell] must be == '
                         'TestAssetAdministrationShell (value=\'TestAssetAdministrationShell123\')',
                         manager.format_step(4, verbose_level=1))
