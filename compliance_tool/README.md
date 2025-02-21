# AAS Compliance Tool
An AAS compliance checker based on the [Eclipse BaSyx Python SDK](https://github.com/eclipse-basyx/basyx-python-sdk) for testing XML and JSON files.
Following functionalities are supported:

* create an xml or json file compliant to the official schema containing example Asset Administration Shell elements
* create an aasx file with xml or json files compliant to the official schema containing example Asset Administration 
Shell elements
* check if a given xml or json file is compliant to the official schema
* check if a given xml, json or aasx file is readable even if it is not compliant to the official schema
* check if the data in a given xml, json or aasx file is the same as the example data
* check if two given xml, json or aasx files contain the same Asset Administration Shell elements in any order 

Invoking should work with either `python -m aas_compliance_tool.cli` or (when installed correctly and PATH is set 
correctly) with `aas-compliance-check` on the command line.

For further usage information consider the `aas_compliance_tool`-package or invoke with 
`python -m aas_compliance_tool.cli --help` respectively `aas-compliance-check --help`.
