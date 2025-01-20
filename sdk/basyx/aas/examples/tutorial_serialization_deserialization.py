#!/usr/bin/env python3
# This work is licensed under a Creative Commons CCZero 1.0 Universal License.
# See http://creativecommons.org/publicdomain/zero/1.0/ for more information.
"""
Tutorial for the serialization and deserialization of Asset Administration Shells, Submodels and Assets into/from JSON
and XML files.
"""

import json

from basyx.aas import model
import basyx.aas.adapter.xml
import basyx.aas.adapter.json

# 'Details of the Asset Administration Shell' specifies multiple official serialization formats for AAS data. In this
# tutorial, we show how the Eclipse BaSyx Python library can be used to serialize AAS objects into JSON or XML and to
# create JSON/XML files, according to the standardized format. It is also demonstrated how these files can be parsed to
# restore the AAS objects as Python objects.
#
# Step-by-Step Guide:
# Step 1: creating Submodel and Asset Administration Shell objects
# Step 2: serializing single objects to JSON
# Step 3: parsing single objects or custom data structures from JSON
# Step 4: writing multiple identifiable objects to a (standard-compliant) JSON/XML file
# Step 5: reading the serialized aas objects from JSON/XML files


####################################################################
# Step 1: Creating Submodel and Asset Administration Shell Objects #
####################################################################

# For more details, take a look at `tutorial_create_simple_aas.py`

submodel = model.Submodel(
    id_='https://acplt.org/Simple_Submodel',
    submodel_element={
        model.Property(
            id_short='ExampleProperty',
            value_type=basyx.aas.model.datatypes.String,
            value='exampleValue',
            semantic_id=model.ExternalReference((model.Key(
                    type_=model.KeyTypes.GLOBAL_REFERENCE,
                    value='http://acplt.org/Properties/SimpleProperty'
                ),)
            )
        )}
)
aashell = model.AssetAdministrationShell(
    id_='https://acplt.org/Simple_AAS',
    asset_information=model.AssetInformation(global_asset_id="test"),
    submodel={model.ModelReference.from_referable(submodel)}
)


##############################################
# Step 2: Serializing Single Objects to JSON #
##############################################

# Before serializing the data, we should make sure, it's up-to-date. This is irrelevant for the static AAS objects in
# this tutorial, but may be important when dealing with dynamic data.
aashell.update()

# `AASToJsonEncoder` from the `aas.adapter.json` module is a custom JSONEncoder class for serializing
# Asset Administration Shell data into the official JSON format according to
# 'Details of the Asset Administration Shell', chapter 5.5, using Python's built-in JSON library. When provided to the
# the `json.dump()` and `json.dumps()` methods, these methods are enabled to correctly handle AAS objects within the
# dumped data structure.
aashell_json_string = json.dumps(aashell, cls=basyx.aas.adapter.json.AASToJsonEncoder)

property_json_string = json.dumps(submodel.submodel_element.get_object_by_attribute("id_short", 'ExampleProperty'),
                                  cls=basyx.aas.adapter.json.AASToJsonEncoder)

# Using this technique, we can also serialize Python dict and list data structures with nested AAS objects:
json_string = json.dumps({'the_submodel': submodel,
                          'the_aas': aashell
                          },
                         cls=basyx.aas.adapter.json.AASToJsonEncoder)


######################################################################
# Step 3: Parsing Single Objects or Custom Data Structures from JSON #
######################################################################

# JSON deserialization works in a similar way to JSON serialization: The `aas.adapter.json` module provides a
# JSONDecoder class, called `AASFromJSONDecoder` which can be passed to `json.load()` or `json.loads()` to ensure that
# AAS objects contained in the JSON data are transformed into their BaSyx Python SDK object representation instead of
# simple Python dicts:
submodel_and_aas = json.loads(json_string, cls=basyx.aas.adapter.json.AASFromJsonDecoder)

# Alternatively, one can use the `StrictAASFromJsonDecoder` which works in just the same way, but enforces the format
# specification more strictly. While `AASFromJSONDecoder` will tolerate some semantic errors by simple skipping the
# broken object and issuing a log message, `StrictAASFromJsonDecoder` will raise an Exception in these cases.


#########################################################################################
# Step 4: Writing Multiple Identifiable Objects to a (Standard-compliant) JSON/XML File #
#########################################################################################

# step 4.1: creating an ObjectStore containing the objects to be serialized
# For more information, take a look into `tutorial_storage.py`
obj_store: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
obj_store.add(submodel)
obj_store.add(aashell)

# step 4.2: Again, make sure that the data is up-to-date
submodel.update()
aashell.update()

# step 4.3: writing the contents of the ObjectStore to a JSON file
basyx.aas.adapter.json.write_aas_json_file('data.json', obj_store)

# We can pass the additional keyword argument `indent=4` to `write_aas_json_file()` to format the JSON file in a more
# human-readable (but much more space-consuming) manner.

# step 4.4: writing the contents of the ObjectStore to an XML file
basyx.aas.adapter.xml.write_aas_xml_file('data.xml', obj_store)


##################################################################
# Step 5: Reading the Serialized AAS Objects From JSON/XML Files #
##################################################################

# step 5.1: reading contents of the JSON file as an ObjectStore
json_file_data = basyx.aas.adapter.json.read_aas_json_file('data.json')

# By passing the `failsafe=False` argument to `read_aas_json_file()`, we can switch to the `StrictAASFromJsonDecoder`
# (see step 3) for a stricter error reporting.

# step 5.2: reading contents of the XML file as an ObjectStore
xml_file_data = basyx.aas.adapter.xml.read_aas_xml_file('data.xml')

# Again, we can use `failsafe=False` for switching on stricter error reporting in the parser.

# step 5.3: Retrieving the objects from the ObjectStore
# For more information on the available techniques, see `tutorial_storage.py`.
submodel_from_xml = xml_file_data.get_identifiable('https://acplt.org/Simple_Submodel')
assert isinstance(submodel_from_xml, model.Submodel)
