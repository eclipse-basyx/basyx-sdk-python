# Copyright (c) 2024 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import datetime
import hashlib
import os
import subprocess
import sys
import unittest
import io

import tempfile
from basyx.aas import model
from basyx.aas.adapter import aasx
from basyx.aas.adapter.json import read_aas_json_file
from basyx.aas.adapter.xml import read_aas_xml_file
from basyx.aas.examples.data import create_example
from basyx.aas.examples.data._helper import AASDataChecker


def _run_compliance_tool(*compliance_tool_args, **kwargs) -> subprocess.CompletedProcess:
    """
    This function runs the compliance tool using subprocess.run()
    and sets the stdout and stderr parameters of subprocess.run() to PIPE.
    Positional arguments are passed to the compliance tool, while keyword arguments are passed to subprocess.run().
    """
    env = os.environ.copy()
    parent_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'aas_compliance_tool'
    )
    env["PYTHONPATH"] = parent_dir + os.pathsep + env.get("PYTHONPATH", "")
    compliance_tool_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'aas_compliance_tool',
        'cli.py'
    )
    return subprocess.run([sys.executable, compliance_tool_path] + list(compliance_tool_args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, env=env, **kwargs)


class ComplianceToolTest(unittest.TestCase):
    def test_parse_args(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        # test schema check
        output = _run_compliance_tool("s")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: the following arguments are required: file_1', str(output.stderr))

        output = _run_compliance_tool("s", os.path.join(test_file_path, "test_demo_full_example.json"))
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        # test deserialisation check
        output = _run_compliance_tool("d")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: the following arguments are required: file_1', str(output.stderr))

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example.json"))
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example.json"), "--aasx")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        # test example check
        output = _run_compliance_tool("e")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: the following arguments are required: file_1', str(output.stderr))

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"))
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--aasx")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        # test file check
        output = _run_compliance_tool("f")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: the following arguments are required: file_1', str(output.stderr))

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.json"))
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.json"), "--aasx")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.json"), "--json")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: f or files requires two file path', str(output.stderr))

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.json"),
                                      os.path.join(test_file_path, "test_demo_full_example.json"))
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: one of the arguments --json --xml is required', str(output.stderr))

        # test verbose
        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--json", "-v")
        self.assertEqual(0, output.returncode)
        self.assertNotIn('ERROR', str(output.stderr))
        self.assertNotIn('INFO', str(output.stdout))

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--json", "-v",
                                      "-v")
        self.assertEqual(0, output.returncode)
        self.assertNotIn('ERROR', str(output.stderr))
        self.assertIn('INFO', str(output.stdout))

        # test quite
        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--json", "-q")
        self.assertEqual(0, output.returncode)
        self.assertEqual("b''", str(output.stdout))

        # test logfile
        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--json", "-l")
        self.assertNotEqual(0, output.returncode)
        self.assertIn('error: argument -l/--logfile: expected one argument', str(output.stderr))

        # todo: add test for correct logfile

    def test_json_create_example(self) -> None:
        file, filename = tempfile.mkstemp(suffix=".json")
        os.close(file)
        output = _run_compliance_tool("c", filename, "--json")

        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Create example data', str(output.stdout))
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Write data to file', str(output.stdout))

        with open(filename, "r", encoding='utf-8-sig') as f:
            json_object_store = read_aas_json_file(f, failsafe=False)
            data = create_example()
            checker = AASDataChecker(raise_immediately=True)
            checker.check_object_store(json_object_store, data)
        os.unlink(filename)

    def test_json_deserialization(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example.json"), "--json")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file and check if it is deserializable', str(output.stdout))

    def test_json_example(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.json"), "--json")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file and check if it is deserializable', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data is equal to example data', str(output.stdout))

    def test_json_file(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.json"),
                                      os.path.join(test_file_path, "test_demo_full_example.json"), "--json")

        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open first file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Open second file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data in files are equal', str(output.stdout))

    def test_xml_create_example(self) -> None:
        file, filename = tempfile.mkstemp(suffix=".xml")
        os.close(file)
        output = _run_compliance_tool("c", filename, "--xml")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Create example data', str(output.stdout))
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Write data to file', str(output.stdout))

        with open(filename, "rb") as f:
            xml_object_store = read_aas_xml_file(f, failsafe=False)
            data = create_example()
            checker = AASDataChecker(raise_immediately=True)
            checker.check_object_store(xml_object_store, data)
        os.unlink(filename)

    def test_xml_deseralization(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example.xml"), "--xml")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file and check if it is deserializable', str(output.stdout))

    def test_xml_example(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example.xml"), "--xml")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file and check if it is deserializable', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data is equal to example data', str(output.stdout))

    def test_xml_file(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example.xml"),
                                      os.path.join(test_file_path, "test_demo_full_example.xml"), "--xml")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open first file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Open second file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data in files are equal', str(output.stdout))

    def test_aasx_create_example(self) -> None:
        file, filename = tempfile.mkstemp(suffix=".aasx")
        os.close(file)
        output = _run_compliance_tool("c", filename, "--xml", "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Create example data', str(output.stdout))
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Write data to file', str(output.stdout))

        # Read AASX file
        new_data: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        new_files = aasx.DictSupplementaryFileContainer()
        with aasx.AASXReader(filename) as reader:
            reader.read_into(new_data, new_files)
            new_cp = reader.get_core_properties()

        # Check AAS objects
        assert (isinstance(new_cp.created, datetime.datetime))
        self.assertIsInstance(new_cp.created, datetime.datetime)
        self.assertAlmostEqual(new_cp.created, datetime.datetime(2020, 1, 1, 0, 0, 0),
                               delta=datetime.timedelta(milliseconds=20))
        self.assertEqual(new_cp.creator, "Eclipse BaSyx Python Testing Framework")
        self.assertEqual(new_cp.description, "Test_Description")
        self.assertEqual(new_cp.lastModifiedBy, "Eclipse BaSyx Python Testing Framework Compliance Tool")
        assert (isinstance(new_cp.modified, datetime.datetime))
        self.assertAlmostEqual(new_cp.modified, datetime.datetime(2020, 1, 1, 0, 0, 1),
                               delta=datetime.timedelta(milliseconds=20))
        self.assertEqual(new_cp.revision, "1.0")
        self.assertEqual(new_cp.version, "2.0.1")
        self.assertEqual(new_cp.title, "Test Title")

        # Check files
        self.assertEqual(new_files.get_content_type("/TestFile.pdf"), "application/pdf")
        file_content = io.BytesIO()
        new_files.write_file("/TestFile.pdf", file_content)
        self.assertEqual(hashlib.sha1(file_content.getvalue()).hexdigest(),
                         "78450a66f59d74c073bf6858db340090ea72a8b1")

        os.unlink(filename)

    def test_aasx_deseralization_xml(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example_xml.aasx"), "--xml",
                                      "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))

    def test_aasx_example_xml(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example_xml.aasx"), "--xml",
                                      "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data is equal to example data', str(output.stdout))

    def test_aasx_deseralization_json(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("d", os.path.join(test_file_path, "test_demo_full_example_json.aasx"), "--json",
                                      "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))

    def test_aasx_example_json(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("e", os.path.join(test_file_path, "test_demo_full_example_json.aasx"), "--json",
                                      "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data is equal to example data', str(output.stdout))

    def test_aasx_file(self) -> None:
        test_file_path = os.path.join(os.path.dirname(__file__), 'files')

        output = _run_compliance_tool("f", os.path.join(test_file_path, "test_demo_full_example_xml.aasx"),
                                      os.path.join(test_file_path, "test_demo_full_example_xml.aasx"), "--xml",
                                      "--aasx")
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Open first file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Open second file', str(output.stdout))
        self.assertIn('SUCCESS:      Read file', str(output.stdout))
        self.assertIn('SUCCESS:      Check if data in files are equal', str(output.stdout))

    def test_logfile(self) -> None:
        file, filename = tempfile.mkstemp(suffix=".json")
        file2, filename2 = tempfile.mkstemp(suffix=".log")
        os.close(file)
        os.close(file2)
        output = _run_compliance_tool("c", filename, "--json", "-v", "-v", "-l", filename2)
        self.assertEqual(0, output.returncode)
        self.assertIn('SUCCESS:      Create example data', str(output.stdout))
        self.assertIn('SUCCESS:      Open file', str(output.stdout))
        self.assertIn('SUCCESS:      Write data to file', str(output.stdout))

        with open(filename2, "r", encoding='utf-8-sig') as f:
            data = f.read()
            self.assertIn('SUCCESS:      Create example data', data)
            self.assertIn('SUCCESS:      Open file', data)
            self.assertIn('SUCCESS:      Write data to file', data)
        os.unlink(filename)
        os.unlink(filename2)
