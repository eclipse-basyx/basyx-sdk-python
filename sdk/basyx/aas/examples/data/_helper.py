# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
Helper classes for checking two objects for completeness and correctness and reporting the check results.

.. warning::
    This module is intended for internal use only.
"""
import pprint
from typing import List, NamedTuple, Iterator, Dict, Any, Type, Union, Set, Iterable, TypeVar

from ... import model


_LIST_OR_COLLECTION = TypeVar("_LIST_OR_COLLECTION", model.SubmodelElementList, model.SubmodelElementCollection)


class CheckResult(NamedTuple):
    expectation: str
    result: bool
    data: Dict[str, Any]

    def __repr__(self):
        return "{}: {} ({})".format("OK  " if self.result else "FAIL",
                                    self.expectation,
                                    ", ".join("{}={}".format(k, pprint.pformat(v, depth=2, width=2 ** 14, compact=True))
                                              for k, v in self.data.items()))


class DataChecker:
    """
    A helper class to perform multiple checks/assertions of given data and report the result.

    Typical usage:

    .. code-block:: python

        data = {'a': 1, 'b': 2}
        dc = DataChecker()
        dc.check(len(data) > 0, "data is not empty")
        if dc.check('a' in data, "a is in data", keys=list(data.keys())):
            dc.check(data['a'] == data['b'], "a == b", a=data['a'], b=data['b'])
            dc.check(data['a'] > 0, "a is positive", a=data['a'])

        for result in dc.failed_checks:
            print(result)
    """

    def __init__(self, raise_immediately: bool = False):
        """
        :param raise_immediately: If True, a failed check will raise an AssertionError instead of gathering the
                                  CheckResults for later analysis
        """
        self.checks: List[CheckResult] = []
        self.raise_immediately = raise_immediately

    def check(self, expression: bool, expectation: str, **kwargs) -> bool:
        """
        Checks if ``expression`` is True and adds / stores the check result for later analysis.

        :param expression: The boolean to be checked for
        :param expectation: A string describing, what the data was expected to look like (for later listing of
                            successful and failed checks)
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        if not expression and self.raise_immediately:
            raise AssertionError("Check failed: {}".format(expectation), kwargs)
        self.checks.append(CheckResult(expectation, expression, kwargs))
        return expression

    def extend(self, other: "DataChecker") -> None:
        """
        Extend the list of check results with another DataChecker's check results
        """
        self.checks.extend(other.checks)

    @property
    def failed_checks(self) -> Iterator[CheckResult]:
        return (result for result in self.checks if not result.result)

    @property
    def successful_checks(self) -> Iterator[CheckResult]:
        return (result for result in self.checks if result.result)

    def raise_failed(self) -> None:
        """
        Raise AssertionError if any check failed
        """
        failed = list(self.failed_checks)
        if len(failed) > 0:
            raise AssertionError("{} of {} checks failed".format(len(failed), len(self.checks)),
                                 [f.expectation for f in failed])


class AASDataChecker(DataChecker):
    def __init__(self, check_extensions: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.check_extensions = check_extensions

    def _check_submodel_element(self, object_: model.SubmodelElement, expected_object: model.SubmodelElement):
        if self.check_is_instance(object_, expected_object.__class__):
            if isinstance(object_, model.Property):
                return self.check_property_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.MultiLanguageProperty):
                return self.check_multi_language_property_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.Range):
                return self.check_range_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.Blob):
                return self.check_blob_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.File):
                return self.check_file_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.ReferenceElement):
                return self.check_reference_element_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.SubmodelElementCollection):
                return self.check_submodel_element_collection_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.SubmodelElementList):
                return self.check_submodel_element_list_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.AnnotatedRelationshipElement):
                return self.check_annotated_relationship_element_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.RelationshipElement):
                return self.check_relationship_element_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.Operation):
                return self.check_operation_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.Capability):
                return self.check_capability_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.Entity):
                return self.check_entity_equal(object_, expected_object)  # type: ignore
            if isinstance(object_, model.BasicEventElement):
                return self.check_basic_event_element_equal(object_, expected_object)  # type: ignore
            else:
                raise AttributeError('Submodel Element class not implemented')

    def _check_has_extension_equal(self, object_: model.HasExtension, expected_object: model.HasExtension):
        """
        Checks if the HasExtension object_ has the same HasExtension attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The HasExtension object which shall be checked
        :param expected_object: The expected HasExtension object
        :return: The value of expression to be used in control statements
        """
        if not self.check_extensions:
            return
        self.check_contained_element_length(object_, 'extension', model.Extension, len(expected_object.extension))
        for expected_extension in expected_object.extension:
            extension = object_.extension.get('name', expected_extension.name)
            if self.check(extension is not None, f'{expected_extension!r} must exist'):
                self._check_extension_equal(extension, expected_extension)  # type: ignore

        found_extensions = self._find_extra_namespace_set_elements_by_name(object_.extension, expected_object.extension)
        self.check(found_extensions == set(), f'{object_!r} must not have extra extensions', value=found_extensions)

    def _check_extension_equal(self, object_: model.Extension, expected_object: model.Extension):
        """
        Checks if the Extension object_ has the same Extension attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The Extension object which shall be checked
        :param expected_object: The expected Extension object
        :return: The value of expression to be used in control statements
        """
        self._check_has_semantics_equal(object_, expected_object)
        self.check_attribute_equal(object_, 'name', expected_object.name)
        self.check_attribute_equal(object_, 'value_type', expected_object.value_type)
        self.check_attribute_equal(object_, 'value', expected_object.value)
        self.check_attribute_equal(object_, 'refers_to', expected_object.refers_to)

    def _check_referable_equal(self, object_: model.Referable, expected_object: model.Referable):
        """
        Checks if the referable object_ has the same referable attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The referable object which shall be checked
        :param expected_object: The expected referable object
        :return: The value of expression to be used in control statements
        """
        # For SubmodelElementLists, the id_shorts of children are randomly generated.
        # Thus, this check would always fail if enabled.
        if not isinstance(object_.parent, model.SubmodelElementList):
            self.check_attribute_equal(object_, "id_short", expected_object.id_short)
        self.check_attribute_equal(object_, "category", expected_object.category)
        self.check_attribute_equal(object_, "description", expected_object.description)
        self.check_attribute_equal(object_, "display_name", expected_object.display_name)
        self._check_has_extension_equal(object_, expected_object)

    def _check_identifiable_equal(self, object_: model.Identifiable, expected_object: model.Identifiable):
        """
        Checks if the identifiable object_ has the same identifiable attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The identifiable object which shall be checked
        :param expected_object: The expected identifiable object
        :return: The value of expression to be used in control statements
        """
        self._check_referable_equal(object_, expected_object)
        self.check_attribute_equal(object_, "administration", expected_object.administration)
        if object_.administration is not None and expected_object.administration is not None:
            self._check_has_data_specification_equal(object_.administration, expected_object.administration)
        self.check_attribute_equal(object_, "id", expected_object.id)

    def _check_has_semantics_equal(self, object_: model.HasSemantics, expected_object: model.HasSemantics):
        """
        Checks if the HasSemantic object_ has the same HasSemantics attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The HasSemantic object which shall be checked
        :param expected_object: The expected HasSemantic object
        :return: The value of expression to be used in control statements
        """
        self.check_attribute_equal(object_, "semantic_id", expected_object.semantic_id)
        if isinstance(expected_object.semantic_id, model.ModelReference) and self.check(
            isinstance(object_.semantic_id, model.ModelReference),
            "{} must be a ModelReference".format(repr(object_)),
        ):  # type: ignore
            self.check(
                object_.semantic_id.type == expected_object.semantic_id.type,  # type: ignore
                "ModelReference type {} of {} must be equal to {}".format(
                    object_.semantic_id.type,  # type: ignore
                    repr(object_),
                    expected_object.semantic_id.type,
                ),
            )
        for suppl_semantic_id in expected_object.supplemental_semantic_id:
            given_semantic_id = self._find_reference(suppl_semantic_id, object_.supplemental_semantic_id)
            self.check(given_semantic_id is not None, f"{object_!r} must have supplementalSemanticId",
                       value=suppl_semantic_id)

        found_elements = self._find_extra_object(object_.supplemental_semantic_id,
                                                 expected_object.supplemental_semantic_id, model.Reference)
        self.check(found_elements == set(), '{} must not have extra supplementalSemanticId'.format(repr(object_)),
                   value=found_elements)

    def _check_has_kind_equal(self, object_: model.HasKind, expected_object: model.HasKind):
        """
        Checks if the HasKind object_ has the same HasKind attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The HasKind object which shall be checked
        :param expected_object: The expected HasKind object
        :return: The value of expression to be used in control statements
        """
        self.check_attribute_equal(object_, "kind", expected_object.kind)

    def _check_qualifiable_equal(self, object_: model.Qualifiable, expected_object: model.Qualifiable):
        """
        Checks if the qualifiable object_ has the same qualifiables attributes as the expected_value object and
        adds / stores the check result for later analysis.

        :param object_: The qualifiable object which shall be checked
        :param expected_object: The expected qualifiable object
        :return: The value of expression to be used in control statements
        """
        self.check_contained_element_length(object_, 'qualifier', model.Qualifier, len(expected_object.qualifier))
        for expected_element in expected_object.qualifier:
            element = self._find_element_by_attribute(expected_element, list(object_.qualifier), 'type')
            if self.check(element is not None, '{} must exist'.format(repr(expected_element))):
                if isinstance(element, model.Qualifier):
                    self._check_qualifier_equal(element, expected_element)  # type: ignore
                else:
                    raise TypeError('Qualifier class not implemented')

        found_elements = self._find_extra_elements_by_attribute(list(object_.qualifier),
                                                                list(expected_object.qualifier), 'type')
        self.check(found_elements == set(), 'Qualifiable Element {} must not have extra elements'.format(repr(object_)),
                   value=found_elements)

    def _check_has_data_specification_equal(self, object_: model.HasDataSpecification,
                                            expected_object: model.HasDataSpecification):
        """
        Checks if the HasDataSpecification object_ has the same HasDataSpecification attributes
        as the expected_value object and adds / stores the check result for later analysis.

        :param object_: The HasDataSpecification object which shall be checked
        :param expected_object: The expected HasDataSpecification object
        """
        self.check_contained_element_length(object_, 'embedded_data_specifications', model.EmbeddedDataSpecification,
                                            len(expected_object.embedded_data_specifications))
        for expected_dspec in expected_object.embedded_data_specifications:
            given_dspec = self._find_element_by_attribute(expected_dspec, object_.embedded_data_specifications,
                                                          'data_specification')
            if self.check(given_dspec is not None, 'EmbeddedDataSpecification {} must exist in {}'.format(
                    repr(expected_dspec.data_specification), repr(object_))):
                self.check_data_specification_content_equal(given_dspec.data_specification_content,  # type: ignore
                                                            expected_dspec.data_specification_content)

        found_elements = self._find_extra_elements_by_attribute(object_.embedded_data_specifications,
                                                                expected_object.embedded_data_specifications,
                                                                'data_specification')
        self.check(found_elements == set(), '{} must not have extra data specifications'.format(repr(object_)),
                   value=found_elements)

    def _check_abstract_attributes_submodel_element_equal(self, object_: model.SubmodelElement,
                                                          expected_value: model.SubmodelElement):
        """
        Checks if the given SubmodelElement objects are equal

        :param object_: Given submodel element object to check
        :param expected_value: expected submodel element object
        :return:
        """
        self._check_referable_equal(object_, expected_value)
        self._check_has_semantics_equal(object_, expected_value)
        self._check_qualifiable_equal(object_, expected_value)
        self._check_has_data_specification_equal(object_, expected_value)

    def _check_submodel_elements_equal_unordered(self, object_: _LIST_OR_COLLECTION,
                                                 expected_value: _LIST_OR_COLLECTION):
        """
        Checks if the given SubmodelElement objects are equal (in any order)

        :param object_: Given SubmodelElementCollection or SubmodelElementList containing the objects to check
        :param expected_value: SubmodelElementCollection or SubmodelElementList containing the expected elements
        :return:
        """
        for expected_element in expected_value.value:
            try:
                element = object_.get_referable(expected_element.id_short)
                self._check_submodel_element(element, expected_element)  # type: ignore
            except KeyError:
                self.check(False, 'Submodel Element {} must exist'.format(repr(expected_element)))

        found_elements = self._find_extra_namespace_set_elements_by_id_short(object_.value, expected_value.value)
        self.check(found_elements == set(), '{} must not have extra elements'.format(repr(object_)),
                   value=found_elements)

    def check_property_equal(self, object_: model.Property, expected_value: model.Property):
        """
        Checks if the given Property objects are equal

        :param object_: Given property object to check
        :param expected_value: expected property object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value_type', expected_value.value_type)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'value_id', expected_value.value_id)

    def check_multi_language_property_equal(self, object_: model.MultiLanguageProperty,
                                            expected_value: model.MultiLanguageProperty):
        """
        Checks if the given MultiLanguageProperty objects are equal

        :param object_: Given MultiLanguageProperty object to check
        :param expected_value: expected MultiLanguageProperty object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'value_id', expected_value.value_id)

    def check_range_equal(self, object_: model.Range, expected_value: model.Range):
        """
        Checks if the given Range objects are equal

        :param object_: Given Range object to check
        :param expected_value: expected Range object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value_type', expected_value.value_type)
        self.check_attribute_equal(object_, 'min', expected_value.min)
        self.check_attribute_equal(object_, 'max', expected_value.max)

    def check_blob_equal(self, object_: model.Blob, expected_value: model.Blob):
        """
        Checks if the given Blob objects are equal

        :param object_: Given Blob object to check
        :param expected_value: expected Blob object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'content_type', expected_value.content_type)

    def check_file_equal(self, object_: model.File, expected_value: model.File):
        """
        Checks if the given File objects are equal

        :param object_: Given File object to check
        :param expected_value: expected File object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'content_type', expected_value.content_type)

    def check_resource_equal(self, object_: model.Resource, expected_value: model.Resource):
        """
        Checks if the given Resource objects are equal

        :param object_: Given Resource object to check
        :param expected_value: expected Resource object
        :return:
        """
        self.check_attribute_equal(object_, 'path', expected_value.path)
        self.check_attribute_equal(object_, 'content_type', expected_value.content_type)

    def check_reference_element_equal(self, object_: model.ReferenceElement, expected_value: model.ReferenceElement):
        """
        Checks if the given ReferenceElement objects are equal

        :param object_: Given ReferenceElement object to check
        :param expected_value: expected ReferenceElement object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'value', expected_value.value)

    def check_submodel_element_collection_equal(self, object_: model.SubmodelElementCollection,
                                                expected_value: model.SubmodelElementCollection):
        """
        Checks if the given SubmodelElementCollection objects are equal

        :param object_: Given SubmodelElementCollection object to check
        :param expected_value: expected SubmodelElementCollection object
        :return:
        """
        # the submodel elements are compared unordered, as collections are unordered
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_contained_element_length(object_, 'value', model.SubmodelElement, len(expected_value.value))
        self._check_submodel_elements_equal_unordered(object_, expected_value)

    def check_submodel_element_list_equal(self, object_: model.SubmodelElementList,
                                          expected_value: model.SubmodelElementList):
        """
        Checks if the given SubmodelElementList objects are equal

        :param object_: Given SubmodelElementList object to check
        :param expected_value: expected SubmodelElementList object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'order_relevant', expected_value.order_relevant)
        self.check_attribute_equal(object_, 'semantic_id_list_element', expected_value.semantic_id_list_element)
        self.check_attribute_equal(object_, 'value_type_list_element', expected_value.value_type_list_element)
        self.check_attribute_equal(object_, 'type_value_list_element', expected_value.type_value_list_element)
        self.check_contained_element_length(object_, 'value', object_.type_value_list_element,
                                            len(expected_value.value))
        if not object_.order_relevant or not expected_value.order_relevant:
            # It is impossible to compare SubmodelElementLists with order_relevant=False, since it is impossible
            # to know which element should be compared against which other element.
            raise NotImplementedError("A SubmodelElementList with order_relevant=False cannot be compared!")

        # compare ordered
        for se1, se2 in zip(object_.value, expected_value.value):
            self._check_submodel_element(se1, se2)

    def check_relationship_element_equal(self, object_: model.RelationshipElement,
                                         expected_value: model.RelationshipElement):
        """
        Checks if the given RelationshipElement objects are equal

        :param object_: Given RelationshipElement object to check
        :param expected_value: expected RelationshipElement object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'first', expected_value.first)
        self.check_attribute_equal(object_, 'second', expected_value.second)

    def check_annotated_relationship_element_equal(self, object_: model.AnnotatedRelationshipElement,
                                                   expected_value: model.AnnotatedRelationshipElement):
        """
        Checks if the given AnnotatedRelationshipElement objects are equal

        :param object_: Given AnnotatedRelationshipElement object to check
        :param expected_value: expected AnnotatedRelationshipElement object
        :return:
        """
        self.check_relationship_element_equal(object_, expected_value)
        self.check_contained_element_length(object_, 'annotation', model.DataElement,
                                            len(expected_value.annotation))
        for expected_data_element in expected_value.annotation:
            try:
                object_.get_referable(expected_data_element.id_short)
            except KeyError:
                self.check(False, 'Annotation {} must exist'.format(repr(expected_data_element)))

        found_elements = self._find_extra_namespace_set_elements_by_id_short(object_.annotation,
                                                                             expected_value.annotation)
        self.check(found_elements == set(), 'Annotated Reference {} must not have extra '
                                            'references'.format(repr(object_)),
                   value=found_elements)

    def _check_reference_equal(self, object_: model.Reference, expected_value: model.Reference):
        """
        Checks if the given Reference objects are equal

        :param object_: Given Reference object to check
        :param expected_value: expected Reference object
        :return:
        """
        self.check(object_ == expected_value, "{} must be == {}".format(repr(object_), repr(expected_value)))

    def _find_reference(self, object_: model.Reference, search_list: Iterable) -> Union[model.Reference, None]:
        """
        Find a reference in a list

        :param object_: Given reference which should be found in list
        :param search_list: List in which the given reference should be found
        :return: the searched reference if found else none
        """
        for element in search_list:
            if object_ == element:
                return element
        return None

    def _find_specific_asset_id(self, object_: model.SpecificAssetId, search_list: Iterable) \
            -> Union[model.SpecificAssetId, None]:
        """
        Find a SpecificAssetId in a list

        :param object_: Given SpecificAssetId which should be found in list
        :param search_list: List in which the given SpecificAssetId should be found
        :return: the searched SpecificAssetId if found else none
        """
        for element in search_list:
            if object_ == element:
                return element
        return None

    def _find_element_by_attribute(self, object_: object, search_list: Iterable, *attribute: str) -> object:
        """
        Find an element in a list

        :param object_: Given object which should be found in list
        :param search_list: List in which the given object should be found
        :param attribute: List of attributes on which the comparison should be done
        :return:
        """
        for element in search_list:
            if isinstance(element, object_.__class__):
                found = True
                for attr in attribute:
                    if getattr(object_, attr) != getattr(element, attr):
                        found = False
                if found:
                    return element
        return None

    def _find_extra_object(self, object_list: Iterable, search_list: Iterable,
                           type_) -> Union[Set, None]:
        """
        Find extra objects that are in object_list but still in search_list

        :param object_list: List which could contain more objects than the search_list has
        :param search_list: List which should be searched
        :param type_: type of objects which should be found
        :return: Set of objects that are in object_list but not in search_list
        """
        found_elements = set()
        for object_list_element in object_list:
            if isinstance(object_list_element, type_):
                found = False
                for search_list_element in search_list:
                    if isinstance(search_list_element, type_):
                        if object_list_element == search_list_element:
                            found = True
                            break
                if found is False:
                    found_elements.add(object_list_element)
        return found_elements

    def _find_extra_elements_by_attribute(self, object_list: Union[Set, List], search_list: Union[Set, List],
                                          *attribute: str) -> Set:
        """
        Find extra elements that are in object_list but not in search_list

        :param object_list: List which could contain more objects than the search_list has
        :param search_list: List which should be searched
        :param attribute: List of attributes on which the comparison should be done
        :return: Set of elements that are in object_list but not in search_list
        """
        found_elements = set()
        for object_list_element in object_list:
            found = False
            for search_list_element in search_list:
                for attr in attribute:
                    if getattr(object_list_element, attr) != getattr(search_list_element, attr):
                        found = False
                    else:
                        found = True
                if found:
                    break
            if found is False:
                found_elements.add(object_list_element)
        return found_elements

    def _find_extra_namespace_set_elements_by_attribute(self, object_list: model.NamespaceSet,
                                                        search_list: model.NamespaceSet, attr_name: str) -> Set:
        """
        Find extra elements that are in object_list but not in search_list by identifying attribute

        :param object_list: List which could contain more objects than the search_list has
        :param search_list: List which should be searched
        :param attr_name: Name of the identifying attribute
        :return: Set of elements that are in object_list but not in search_list
        """
        found_elements = set()
        for object_list_element in object_list:
            element = search_list.get(attr_name, getattr(object_list_element, attr_name))
            if element is None:
                found_elements.add(object_list_element)
        return found_elements

    def _find_extra_namespace_set_elements_by_id_short(self, object_list: model.NamespaceSet,
                                                       search_list: model.NamespaceSet) -> Set:
        """
        Find extra Referable objects that are in object_list but not in search_list

        :param object_list: List which could contain more objects than the search_list has
        :param search_list: List which should be searched
        :return: Set of elements that are in object_list but not in search_list
        """
        return self._find_extra_namespace_set_elements_by_attribute(object_list, search_list, 'id_short')

    def _find_extra_namespace_set_elements_by_name(self, object_list: model.NamespaceSet,
                                                   search_list: model.NamespaceSet) -> Set:
        """
        Find extra Extension object that are in object_list but not in search_list

        :param object_list: List which could contain more objects than the search_list has
        :param search_list: List which should be searched
        :return: Set of elements that are in object_list but not in search_list
        """
        return self._find_extra_namespace_set_elements_by_attribute(object_list, search_list, 'name')

    def check_operation_equal(self, object_: model.Operation, expected_value: model.Operation):
        """
        Checks if the given Operation objects are equal

        :param object_: Given Operation object to check
        :param expected_value: expected Operation object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        for input_nss, expected_nss, attr_name in (
                (object_.input_variable, expected_value.input_variable, 'input_variable'),
                (object_.output_variable, expected_value.output_variable, 'output_variable'),
                (object_.in_output_variable, expected_value.in_output_variable, 'in_output_variable')):
            self.check_contained_element_length(object_, attr_name, model.SubmodelElement, len(expected_nss))
            for var1, var2 in zip(input_nss, expected_nss):
                self._check_submodel_element(var1, var2)

    def check_capability_equal(self, object_: model.Capability, expected_value: model.Capability):
        """
        Checks if the given Capability objects are equal

        :param object_: Given Capability object to check
        :param expected_value: expected Capability object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)

    def check_entity_equal(self, object_: model.Entity, expected_value: model.Entity):
        """
        Checks if the given Entity objects are equal

        :param object_: Given Entity object to check
        :param expected_value: expected Entity object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'entity_type', expected_value.entity_type)
        self.check_attribute_equal(object_, 'global_asset_id', expected_value.global_asset_id)
        self._check_specific_asset_ids_equal(object_.specific_asset_id, expected_value.specific_asset_id, object_)
        self.check_contained_element_length(object_, 'statement', model.SubmodelElement, len(expected_value.statement))
        for expected_element in expected_value.statement:
            element = object_.get_referable(expected_element.id_short)
            self.check(element is not None, f'Entity {repr(expected_element)} must exist')

        found_elements = self._find_extra_namespace_set_elements_by_id_short(object_.statement,
                                                                             expected_value.statement)
        self.check(found_elements == set(), f'Entity {repr(object_)} must not have extra statements',
                   value=found_elements)

    def _check_specific_asset_ids_equal(self, object_: Iterable[model.SpecificAssetId],
                                        expected_value: Iterable[model.SpecificAssetId],
                                        object_parent):
        for expected_pair in expected_value:
            pair = self._find_specific_asset_id(expected_pair, object_)
            if self.check(pair is not None, f'SpecificAssetId {repr(expected_pair)} must exist'):
                self.check_specific_asset_id(pair, expected_pair)  # type: ignore

        found_elements = self._find_extra_object(object_, expected_value, model.SpecificAssetId)
        self.check(found_elements == set(), f'{repr(object_parent)} must not have extra specificAssetIds',
                   value=found_elements)

    def _check_event_element_equal(self, object_: model.EventElement, expected_value: model.EventElement):
        """
        Checks if the given EventElement objects are equal

        :param object_: Given EventElement object to check
        :param expected_value: expected EventElement object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)

    def check_basic_event_element_equal(self, object_: model.BasicEventElement,
                                        expected_value: model.BasicEventElement):
        """
        Checks if the given BasicEventElement objects are equal

        :param object_: Given BasicEventElement object to check
        :param expected_value: expected BasicEventElement object
        :return:
        """
        self._check_abstract_attributes_submodel_element_equal(object_, expected_value)
        self._check_event_element_equal(object_, expected_value)
        self.check_attribute_equal(object_, 'observed', expected_value.observed)
        self.check_attribute_equal(object_, 'direction', expected_value.direction)
        self.check_attribute_equal(object_, 'state', expected_value.state)
        self.check_attribute_equal(object_, 'message_topic', expected_value.message_topic)
        self.check_attribute_equal(object_, 'message_broker', expected_value.message_broker)
        self.check_attribute_equal(object_, 'last_update', expected_value.last_update)
        self.check_attribute_equal(object_, 'min_interval', expected_value.min_interval)
        self.check_attribute_equal(object_, 'max_interval', expected_value.max_interval)

    def check_submodel_equal(self, object_: model.Submodel, expected_value: model.Submodel):
        """
        Checks if the given Submodel objects are equal

        :param object_: Given Submodel object to check
        :param expected_value: expected Submodel object
        :return:
        """
        self._check_identifiable_equal(object_, expected_value)
        self._check_has_semantics_equal(object_, expected_value)
        self._check_has_kind_equal(object_, expected_value)
        self._check_qualifiable_equal(object_, expected_value)
        self._check_has_data_specification_equal(object_, expected_value)
        self.check_contained_element_length(object_, 'submodel_element', model.SubmodelElement,
                                            len(expected_value.submodel_element))
        for expected_element in expected_value.submodel_element:
            try:
                element = object_.get_referable(expected_element.id_short)
                self._check_submodel_element(element, expected_element)  # type: ignore
            except KeyError:
                self.check(False, 'Submodel Element {} must exist'.format(repr(expected_element)))

        found_elements = self._find_extra_namespace_set_elements_by_id_short(object_.submodel_element,
                                                                             expected_value.submodel_element)
        self.check(found_elements == set(), 'Submodel {} must not have extra submodel elements'.format(repr(object_)),
                   value=found_elements)

    def _check_qualifier_equal(self, object_: model.Qualifier, expected_value: model.Qualifier):
        """
        Checks if the given Qualifier objects are equal

        :param object_: Given Qualifier object to check
        :param expected_value: expected Qualifier object
        :return:
        """
        self.check_attribute_equal(object_, 'type', expected_value.type)
        self.check_attribute_equal(object_, 'value_type', expected_value.value_type)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'value_id', expected_value.value_id)
        self.check_attribute_equal(object_, 'kind', expected_value.kind)

    def check_specific_asset_id(self, object_: model.SpecificAssetId,
                                expected_value: model.SpecificAssetId):
        """
        Checks if the given SpecificAssetId objects are equal

        :param object_: Given SpecificAssetId object to check
        :param expected_value: expected SpecificAssetId object
        :return:
        """
        self.check_attribute_equal(object_, "name", expected_value.name)
        self.check_attribute_equal(object_, "value", expected_value.value)
        self.check_attribute_equal(object_, "external_subject_id", expected_value.external_subject_id)
        self.check_attribute_equal(object_, "semantic_id", expected_value.semantic_id)

    def check_asset_information_equal(self, object_: model.AssetInformation, expected_value: model.AssetInformation):
        """
        Checks if the given AssetInformation objects are equal

        :param object_: Given AssetInformation object to check
        :param expected_value: expected AssetInformation object
        :return:
        """
        self.check_attribute_equal(object_, 'asset_kind', expected_value.asset_kind)
        self.check_attribute_equal(object_, 'global_asset_id', expected_value.global_asset_id)
        self.check_contained_element_length(object_, 'specific_asset_id', model.SpecificAssetId,
                                            len(expected_value.specific_asset_id))
        self._check_specific_asset_ids_equal(object_.specific_asset_id, expected_value.specific_asset_id, object_)
        self.check_attribute_equal(object_, 'asset_type', object_.asset_type)
        if object_.default_thumbnail and expected_value.default_thumbnail:
            self.check_resource_equal(object_.default_thumbnail, expected_value.default_thumbnail)
        else:
            if object_.default_thumbnail:
                self.check(expected_value.default_thumbnail is not None,
                           'defaultThumbnail object {} must exist'.format(repr(object_.default_thumbnail)),
                           value=expected_value.default_thumbnail)
            else:
                self.check(expected_value.default_thumbnail is None, '{} must not have a '
                                                                     'defaultThumbnail object'.format(repr(object_)),
                           value=expected_value.default_thumbnail)

    def check_asset_administration_shell_equal(self, object_: model.AssetAdministrationShell,
                                               expected_value: model.AssetAdministrationShell):
        """
        Checks if the given AssetAdministrationShell objects are equal

        :param object_: Given AssetAdministrationShell object to check
        :param expected_value: expected AssetAdministrationShell object
        :return:
        """
        self._check_identifiable_equal(object_, expected_value)
        self._check_has_data_specification_equal(object_, expected_value)
        self.check_asset_information_equal(object_.asset_information, expected_value.asset_information)

        self.check_attribute_equal(object_, 'derived_from', expected_value.derived_from)
        self.check_contained_element_length(object_, 'submodel', model.ModelReference, len(expected_value.submodel))
        for expected_ref in expected_value.submodel:
            ref = self._find_reference(expected_ref, object_.submodel)
            if self.check(ref is not None, 'Submodel Reference {} must exist'.format(repr(expected_ref))):
                self._check_reference_equal(ref, expected_ref)  # type: ignore

        found_elements = self._find_extra_object(object_.submodel, expected_value.submodel, model.ModelReference)
        self.check(found_elements == set(), 'Asset Administration Shell {} must not have extra submodel '
                                            'references'.format(repr(object_)),
                   value=found_elements)

    def check_concept_description_equal(self, object_: model.ConceptDescription,
                                        expected_value: model.ConceptDescription):
        """
        Checks if the given ConceptDescription objects are equal

        :param object_: Given ConceptDescription object to check
        :param expected_value: expected ConceptDescription object
        :return:
        """
        self._check_identifiable_equal(object_, expected_value)
        self._check_has_data_specification_equal(object_, expected_value)
        self.check_contained_element_length(object_, 'is_case_of', model.Reference,
                                            len(expected_value.is_case_of))
        for expected_ref in expected_value.is_case_of:
            ref = self._find_reference(expected_ref, object_.is_case_of)
            if self.check(ref is not None, 'Concept Description Reference {} must exist'.format(repr(expected_ref))):
                self._check_reference_equal(ref, expected_ref)  # type: ignore

        found_elements = self._find_extra_object(object_.is_case_of, expected_value.is_case_of,
                                                 model.ModelReference)
        self.check(found_elements == set(), 'Concept Description Reference {} must not have extra '
                                            'is case of references'.format(repr(object_)),
                   value=found_elements)

    def check_data_specification_content_equal(
            self, object_: model.DataSpecificationContent,
            expected_value: model.DataSpecificationContent):
        """
        Checks if the given DataSpecificationContent objects are equal

        :param object_: Given DataSpecificationContent object to check
        :param expected_value: expected DataSpecificationContent object
        :return:
        """
        self.check(type(object_) is type(expected_value), "type({}) must be == type({})"
                   .format(repr(object_), repr(expected_value)))
        if isinstance(object_, model.base.DataSpecificationIEC61360):
            self._check_data_specification_iec61360_equal(object_, expected_value)  # type: ignore

    def _check_data_specification_iec61360_equal(self, object_: model.base.DataSpecificationIEC61360,
                                                 expected_value: model.base.DataSpecificationIEC61360):
        """
        Checks if the given IEC61360ConceptDescription objects are equal

        :param object_: Given IEC61360ConceptDescription object to check
        :param expected_value: expected IEC61360ConceptDescription object
        :return:
        """
        self.check_attribute_equal(object_, 'preferred_name', expected_value.preferred_name)
        self.check_attribute_equal(object_, 'short_name', expected_value.short_name)
        self.check_attribute_equal(object_, 'data_type', expected_value.data_type)
        self.check_attribute_equal(object_, 'definition', expected_value.definition)
        self.check_attribute_equal(object_, 'unit', expected_value.unit)
        self.check_attribute_equal(object_, 'unit_id', expected_value.unit_id)
        self.check_attribute_equal(object_, 'source_of_definition', expected_value.source_of_definition)
        self.check_attribute_equal(object_, 'symbol', expected_value.symbol)
        self.check_attribute_equal(object_, 'value_format', expected_value.value_format)
        self.check_attribute_equal(object_, 'value', expected_value.value)
        self.check_attribute_equal(object_, 'level_types', expected_value.level_types)

        if expected_value.value_list is not None:
            if self.check(object_.value_list is not None,
                          "ValueList must contain {} ValueReferencePairs".format(len(expected_value.value_list)),
                          value=expected_value.value_list):
                self._check_value_list_equal(object_.value_list, expected_value.value_list)  # type: ignore

        if object_.value_list is not None:
            if self.check(expected_value.value_list is not None,
                          "ValueList must contain 0 ValueReferencePairs", value=len(object_.value_list)):
                self._check_value_list_equal(object_.value_list, expected_value.value_list)  # type: ignore

    def _check_value_list_equal(self, object_: model.ValueList, expected_value: model.ValueList):
        """
        Checks if the given ValueList objects are equal

        :param object_: Given ValueList object to check
        :param expected_value: expected ValueList object
        :return:
        """
        for expected_pair in expected_value:
            pair = self._find_element_by_attribute(expected_pair, object_, 'value', 'value_id')
            self.check(pair is not None, 'ValueReferencePair[value={}, value_id={}] '
                                         'must exist'.format(expected_pair.value, expected_pair.value_id))

        found_elements = self._find_extra_elements_by_attribute(object_, expected_value, 'value', 'value_id')
        self.check(found_elements == set(), 'ValueList must not have extra ValueReferencePairs',
                   value=found_elements)

    def check_object_store(self, obj_store_1: model.DictObjectStore, obj_store_2: model.DictObjectStore):
        """
        Checks if the given object stores are equal

        :param obj_store_1: Given object store to check
        :param obj_store_2: expected object store
        :return:
        """
        # separate different kind of objects
        submodel_list_1 = []
        concept_description_list_1 = []
        shell_list_1 = []
        for obj in obj_store_1:
            if isinstance(obj, model.AssetAdministrationShell):
                shell_list_1.append(obj)
            elif isinstance(obj, model.Submodel):
                submodel_list_1.append(obj)
            elif isinstance(obj, model.ConceptDescription):
                concept_description_list_1.append(obj)
            else:
                raise KeyError('Check for {} not implemented'.format(obj))

        # separate different kind of objects
        submodel_list_2 = []
        concept_description_list_2 = []
        shell_list_2 = []
        for obj in obj_store_2:
            if isinstance(obj, model.AssetAdministrationShell):
                shell_list_2.append(obj)
            elif isinstance(obj, model.Submodel):
                submodel_list_2.append(obj)
            elif isinstance(obj, model.ConceptDescription):
                concept_description_list_2.append(obj)
            else:
                raise KeyError('Check for {} not implemented'.format(obj))

        for shell_2 in shell_list_2:
            shell_1 = obj_store_1.get(shell_2.id)
            if self.check(shell_1 is not None, 'Asset administration shell {} must exist in given asset administration'
                                               'shell list'.format(shell_2)):
                self.check_asset_administration_shell_equal(shell_1, shell_2)  # type: ignore

        found_elements = self._find_extra_elements_by_attribute(shell_list_1, shell_list_2, 'id')
        self.check(found_elements == set(), 'Given asset administration shell list must not have extra asset '
                                            'administration shells', value=found_elements)

        for submodel_2 in submodel_list_2:
            submodel_1 = obj_store_1.get(submodel_2.id)
            if self.check(submodel_1 is not None, 'Submodel {} must exist in given submodel list'.format(submodel_2)):
                self.check_submodel_equal(submodel_1, submodel_2)  # type: ignore

        found_elements = self._find_extra_elements_by_attribute(submodel_list_1, submodel_list_2, 'id')
        self.check(found_elements == set(), 'Given submodel list must not have extra submodels',
                   value=found_elements)

        for cd_2 in concept_description_list_2:
            cd_1 = obj_store_1.get(cd_2.id)
            if self.check(cd_1 is not None, 'Concept description {} must exist in given concept description '
                                            'list'.format(cd_2)):
                self.check_concept_description_equal(cd_1, cd_2)  # type: ignore

        found_elements = self._find_extra_elements_by_attribute(concept_description_list_1, concept_description_list_2,
                                                                'id')
        self.check(found_elements == set(), 'Given concept description list must not have extra concept '
                                            'descriptions',
                   value=found_elements)

    def check_attribute_equal(self, object_: object, attribute_name: str, expected_value: object, **kwargs) -> bool:
        """
        Checks if the value of the attribute in ``object_`` is the same as ``expected_value`` and adds / stores the
        check result for later analysis.

        :param object_: The object of which the attribute shall be checked
        :param attribute_name: The name of the attribute in the given object which shall be checked
        :param expected_value: The expected value of the attribute
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        # TODO: going by attribute name here isn't exactly pretty...
        if attribute_name in ('value_type', 'value_type_list_element', 'type_value_list_element') \
                and getattr(object_, attribute_name) is not None:
            # value_type_list_element can be None and doesn't have the __name__ attribute in this case
            kwargs['value'] = getattr(object_, attribute_name).__name__
            return self.check(getattr(object_, attribute_name) is expected_value,  # type:ignore
                              "Attribute {} of {} must be == {}".format(
                                  attribute_name, repr(object_), expected_value.__name__),  # type:ignore
                              **kwargs)
        else:
            kwargs['value'] = getattr(object_, attribute_name)
            return self.check(getattr(object_, attribute_name) == expected_value,
                              "Attribute {} of {} must be == {}".format(attribute_name, repr(object_), expected_value),
                              **kwargs)

    def check_element_in(self, object_: model.Referable, parent: object, **kwargs) -> bool:
        """
        Checks if ``object_`` exist in ``parent`` and adds / stores the check result for later analysis.

        :param object_: The object which shall be in parent
        :param parent: The parent in which ``object_`` shall exist
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        return self.check(object_.parent == parent,
                          "{} must exist in {}s".format(repr(object_), repr(parent)),
                          **kwargs)

    def check_contained_element_length(self, object_: object, attribute_name: str, class_name: Type,
                                       length: int, **kwargs) -> bool:
        """
        Checks if the ``object_`` has ``length`` elements of class ``class_name`` in attribute ``attribute_name`` and
        adds / stores the check result for later analysis.

        :param object_: The object of which the attribute shall be checked
        :param attribute_name: The name of the attribute in the given object which shall be checked
        :param class_name: The class name to decide which objects in the attribute shall be count
        :param length: The expected length of the attribute
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        count = 0
        for element in getattr(object_, attribute_name):
            if isinstance(element, class_name):
                count = count + 1
        kwargs['count'] = count
        return self.check(count == length,
                          "Attribute {} of {} must contain {} {}s".format(attribute_name, repr(object_),
                                                                          length, class_name.__name__),
                          **kwargs)

    def check_is_instance(self, object_: object, class_name: Type, **kwargs) -> bool:
        """
        Checks if ``object_`` is of type ``class_name`` and adds / stores the check result for later analysis.

        :param object_: The object of which the attribute shall be checked
        :param class_name: The class name which the ``object_`` shall be
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        kwargs['class'] = object_.__class__.__name__
        return self.check(isinstance(object_, class_name),
                          "{} must be of class {}".format(repr(object_), class_name.__name__),
                          **kwargs)

    def check_attribute_is_none(self, object_: object, attribute_name: str, **kwargs) -> bool:
        """
        Checks if the value of the attribute in ``object_`` is :class:`None` and adds / stores the check result for
        later analysis.

        :param object_: The object of which the attribute shall be checked
        :param attribute_name: The name of the attribute in the given object which shall be checked
        :param kwargs: Relevant values to add to the check result for further analysis (e.g. the compared values)
        :return: The value of expression to be used in control statements
        """
        kwargs['value'] = getattr(object_, attribute_name)
        return self.check(getattr(object_, attribute_name) is None,
                          "Attribute {} of {} must be None".format(attribute_name, repr(object_)),
                          **kwargs)
