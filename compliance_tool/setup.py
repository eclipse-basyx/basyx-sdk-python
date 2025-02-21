#!/usr/bin/env python3
# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT

import setuptools

with open("README.md", "r", encoding='utf-8') as fh:
    long_description = fh.read()

setuptools.setup(
    name="aas_compliance_tool",
    version="1.0.0",
    author="The AAS Compliance Tool authors",
    description="AAS compliance checker based on the Eclipse BaSyx Python SDK",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/rwth-iat/aas-compliance-tool",
    packages=setuptools.find_packages(exclude=["test", "test.*"]),
    zip_safe=False,
    package_data={
        "aas_compliance_tool": ["py.typed", "schemas/aasJSONSchema.json", "schemas/aasXMLSchema.xsd"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 5 - Production/Stable",
    ],
    entry_points={
        'console_scripts': [
            "aas-compliance-check = aas_compliance_tool:main"
        ]
    },
    python_requires='>=3.8',
    install_requires=[
        'pyecma376-2>=0.2.4',
        'basyx-python-sdk>=1.0.0',
    ]
)
