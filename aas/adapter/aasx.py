# Copyright 2019 PyI40AAS Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
"""
TODO
"""
import abc
import io
import logging
import os
import re
from typing import Dict, Tuple, IO, Union, List, Set, Optional

from .. import model
from .json.json_deserialization import read_json_aas_file
from .json.json_serialization import write_aas_json_file
import pyecma376_2
from ..util import traversal

logger = logging.getLogger(__name__)


class AASXReader:
    def __init__(self, file: Union[os.PathLike, str, IO]):
        try:
            logger.debug("Opening {} as AASX pacakge for reading ...".format(file))
            self.reader = pyecma376_2.ZipPackageReader(file)
        except Exception as e:
            raise ValueError("{} is not a valid ECMA376-2 (OPC) file".format(file)) from e

    def get_core_properties(self) -> pyecma376_2.OPCCoreProperties:
        return self.reader.get_core_properties()

    def get_thumbnail(self) -> Optional[bytes]:
        try:
            thumbnail_part = self.reader.get_related_parts_by_type()[pyecma376_2.RELATIONSHIP_TYPE_THUMBNAIL][0]
        except IndexError:
            return None

        with self.reader.open_part(thumbnail_part) as p:
            return p.read()

    def read_into(self, object_store: model.AbstractObjectStore,
                  file_store: "AbstractSupplementaryFileContainer") -> Set[model.Identifier]:
        # Find AASX-Origin part
        core_rels = self.reader.get_related_parts_by_type()
        try:
            aasx_origin_part = core_rels["http://www.admin-shell.io/aasx/relationships/aasx-origin"][0]
        except IndexError as e:
            raise ValueError("Not a valid AASX file: aasx-origin Relationship is missing.") from e

        read_identifiables: Set[model.Identifier] = set()

        # Iterate AAS files
        for aas_part in self.reader.get_related_parts_by_type(aasx_origin_part)[
                "http://www.admin-shell.io/aasx/relationships/aas-spec"]:
            self._read_aas_part_into(aas_part, object_store, file_store, read_identifiables)

            # Iterate split parts of AAS file
            for split_part in self.reader.get_related_parts_by_type(aas_part)[
                    "http://www.admin-shell.io/aasx/relationships/aas-spec-split"]:
                self._read_aas_part_into(split_part, object_store, file_store, read_identifiables)

        return read_identifiables

    def close(self) -> None:
        self.reader.close()

    def __enter__(self) -> "AASXReader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _read_aas_part_into(self, part_name: str,
                            object_store: model.AbstractObjectStore,
                            file_store: "AbstractSupplementaryFileContainer",
                            read_identifiables: Set[model.Identifier]):
        """
        TODO

        :param part_name:
        :param object_store:
        :param file_store:
        :param read_identifiables:
        :return:
        """
        for obj in self._parse_aas_part(part_name):
            if obj.identification in read_identifiables:
                continue
            if obj.identification not in object_store:
                object_store.add(obj)
                read_identifiables.add(obj.identification)
                if isinstance(obj, model.Submodel):
                    self._collect_supplementary_files(part_name, obj, file_store)
            else:
                # TODO non-failsafe mode? Merge-mode?
                logger.warning("Skipping {}, since an object with the same id is already contained in the "
                               "ObjectStore".format(obj))

    def _parse_aas_part(self, part_name: str) -> model.DictObjectStore:
        """
        TODO

        :param part_name:
        :param content_type:
        :param file_handle:
        :return:
        """
        content_type = self.reader.get_content_type(part_name)
        extension = part_name.split("/")[-1].split(".")[-1]
        if content_type.split(";")[0] in ("text/xml", "application/xml") or content_type == "" and extension == "xml":
            logger.debug("Parsing AAS objects from XML stream in OPC part {} ...".format(part_name))
            # TODO XML Deserialization
            raise NotImplementedError("XML deserialization is not implemented yet. Thus, AASX files with XML parts are "
                                      "not supported.")
        elif content_type.split(";")[0] in ("text/json", "application/json") \
                or content_type == "" and extension == "json":
            logger.debug("Parsing AAS objects from JSON stream in OPC part {} ...".format(part_name))
            with self.reader.open_part(part_name) as p:
                return read_json_aas_file(io.TextIOWrapper(p, encoding='utf-8-sig'))
        else:
            logger.error("Could not determine part format of AASX part {}".format(part_name))
            # TODO failsafe mode?
            raise ValueError("Unknown Content Type '{}' and extension '{}' of AASX part {}"
                             .format(content_type, extension, part_name))

    def _collect_supplementary_files(self,
                                     part_name: str,
                                     submodel: model.Submodel,
                                     file_store: "AbstractSupplementaryFileContainer") -> None:
        """
        TODO
        :param part_name:
        :param submodel:
        :param file_store:
        """
        for element in traversal.walk_submodel(submodel):
            if isinstance(element, model.File):
                if element.value is None:
                    continue
                absolute_name = pyecma376_2.package_model.part_realpath(element.value, part_name)
                element.value = absolute_name
                # TODO compare/merge files by hash?
                if absolute_name not in file_store:
                    logger.debug("Reading supplementary file {} from AASX package ...".format(absolute_name))
                    with self.reader.open_part(absolute_name) as p:
                        file_store.add_file(absolute_name, p, self.reader.get_content_type(absolute_name))


class AASXWriter:
    """
    TODO
    """
    AASX_ORIGIN_PART_NAME = "/aasx/aasx-origin"

    def __init__(self, file: Union[os.PathLike, str, IO]):
        self._aas_part_names: List[str] = []
        self._thumbnail_part: Optional[str] = None
        self._properties_part: Optional[str] = None
        self._aas_name_friendlyfier = NameFriendlyfier()

        # Open OPC package writer
        self.writer = pyecma376_2.ZipPackageWriter(file)

        # Create AASX origin part
        logger.debug("Creating AASX origin part in AASX package ...")
        p = self.writer.open_part(self.AASX_ORIGIN_PART_NAME, "text/plain")
        p.close()

    # TODO allow to specify, which supplementary parts (submodels, conceptDescriptions) should be added to the package
    # TODO allow to select JSON/XML serialization
    def write_aas(self,
                  aas_id: model.Identifier,
                  object_store: model.AbstractObjectStore,
                  file_store: "AbstractSupplementaryFileContainer") -> None:
        """
        TODO

        :param aas_id:
        :param object_store:
        :param file_store:
        :return:
        """
        aas_friendly_name = self._aas_name_friendlyfier.get_friendly_name(aas_id)
        aas_part_name = "/aasx/{0}/{0}.aas.json".format(aas_friendly_name)
        self._aas_part_names.append(aas_part_name)
        aas_friendlyfier = NameFriendlyfier()

        aas: model.AssetAdministrationShell = object_store.get_identifiable(aas_id)  # type: ignore
        objects_to_be_written: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        objects_to_be_written.add(aas)

        # Add the Asset object to the objects in the AAS part
        try:
            objects_to_be_written.add(aas.asset.resolve(object_store))
        except KeyError:
            # Don't add asset to the AASX file, if it is not included in the object store
            pass

        # Add referenced ConceptDescriptions to the AAS part
        for dictionary in aas.concept_dictionary:
            for concept_rescription_ref in dictionary.concept_description:
                try:
                    objects_to_be_written.add(concept_rescription_ref.resolve(object_store))
                except KeyError:
                    # Don't add asset to the AASX file, if it is not included in the given object store
                    # Also ignore duplicate ConceptDescriptions (i.e. same Description referenced from multiple
                    # Dictionaries)
                    pass

        # Write AAS part
        logger.debug("Writing AAS {} to part {} in AASX package ...".format(aas.identification, aas_part_name))
        with self.writer.open_part(aas_part_name, "application/json") as p:
            write_aas_json_file(io.TextIOWrapper(p, encoding='utf-8'), objects_to_be_written)

        # Create a AAS split part for each (available) submodel of the AAS
        aas_split_part_names: List[str] = []
        for submodel_ref in aas.submodel:
            try:
                submodel = submodel_ref.resolve(object_store)
            except KeyError:
                # Don't add submodel to the AASX file, if it is not included in the given object store
                continue
            submodel_friendly_name = aas_friendlyfier.get_friendly_name(submodel.identification)
            submodel_part_name = "/aasx/{0}/{1}/{1}.submodel.json".format(aas_friendly_name, submodel_friendly_name)
            self._write_submodel_part(file_store, submodel, submodel_part_name)
            aas_split_part_names.append(submodel_part_name)

        # Add relationships from AAS part to (submodel) split parts
        logger.debug("Writing aas-spec-split relationships for AAS {} to AASX package ..."
                     .format(aas.identification))
        self.writer.write_relationships(
            (pyecma376_2.OPCRelationship("r{}".format(i),
                                         "http://www.admin-shell.io/aasx/relationships/aas-spec-split",
                                         submodel_part_name,
                                         pyecma376_2.OPCTargetMode.INTERNAL)
             for i, submodel_part_name in enumerate(aas_split_part_names)),
            aas_part_name)

    def _write_submodel_part(self, file_store: "AbstractSupplementaryFileContainer",
                             submodel: model.Submodel, submodel_part_name: str) -> None:
        """
        TODO

        :param file_store:
        :param submodel:
        :param submodel_part_name:
        :return:
        """
        logger.debug("Writing Submodel {} to part {} in AASX package ..."
                     .format(submodel.identification, submodel_part_name))

        submodel_file_objects: model.DictObjectStore[model.Identifiable] = model.DictObjectStore()
        submodel_file_objects.add(submodel)
        with self.writer.open_part(submodel_part_name, "application/json") as p:
            write_aas_json_file(io.TextIOWrapper(p, encoding='utf-8'), submodel_file_objects)

        # Write submodel's supplementary files to AASX file
        submodel_file_names = []
        for element in traversal.walk_submodel(submodel):
            if isinstance(element, model.File):
                file_name = element.value
                if file_name is None:
                    continue
                try:
                    content_type = file_store.get_content_type(file_name)
                except KeyError:
                    logger.warning("Could not find file {} in file store, referenced from {}."
                                   .format(file_name, element))
                    continue
                # TODO avoid double writes of same file
                logger.debug("Writing supplementary file {} to AASX package ...".format(file_name))
                with self.writer.open_part(file_name, content_type) as p:
                    file_store.write_file(file_name, p)
                submodel_file_names.append(pyecma376_2.package_model.normalize_part_name(file_name))

        # Add relationships from submodel to supplementary parts
        # TODO should the relationships be added from the AAS instead?
        logger.debug("Writing aas-suppl relationships for Submodel {} to AASX package ..."
                     .format(submodel.identification))
        self.writer.write_relationships(
            (pyecma376_2.OPCRelationship("r{}".format(i),
                                         "http://www.admin-shell.io/aasx/relationships/aas-suppl",
                                         submodel_file_name,
                                         pyecma376_2.OPCTargetMode.INTERNAL)
             for i, submodel_file_name in enumerate(submodel_file_names)),
            submodel_part_name)

    def write_core_properties(self, core_properties: pyecma376_2.OPCCoreProperties):
        """
        TODO
        :param core_properties:
        :return:
        """
        if self._properties_part is not None:
            raise RuntimeError("Core Properties have already been written.")
        logger.debug("Writing core properties to AASX package ...")
        with self.writer.open_part(pyecma376_2.DEFAULT_CORE_PROPERTIES_NAME, "application/xml") as p:
            core_properties.write_xml(p)
        self._properties_part = pyecma376_2.DEFAULT_CORE_PROPERTIES_NAME

    def write_thumbnail(self, name: str, data: bytearray, content_type: str):
        """
        TODO
        """
        if self._thumbnail_part is not None:
            raise RuntimeError("package thumbnail has already been written to {}.".format(self._thumbnail_part))
        with self.writer.open_part(name, content_type) as p:
            p.write(data)
        self._thumbnail_part = name

    def close(self):
        """
        TODO
        :return:
        """
        self._write_aasx_origin_relationships()
        self._write_package_relationships()
        self.writer.close()

    def __enter__(self) -> "AASXWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _write_aasx_origin_relationships(self):
        """
        TODO
        :return:
        """
        # Add relationships from AASX-origin part to AAS parts
        logger.debug("Writing aas-spec relationships to AASX package ...")
        self.writer.write_relationships(
            (pyecma376_2.OPCRelationship("r{}".format(i), "http://www.admin-shell.io/aasx/relationships/aas-spec",
                                         aas_part_name,
                                         pyecma376_2.OPCTargetMode.INTERNAL)
             for i, aas_part_name in enumerate(self._aas_part_names)),
            self.AASX_ORIGIN_PART_NAME)

    def _write_package_relationships(self):
        """
        TODO
        :return:
        """
        logger.debug("Writing package relationships to AASX package ...")
        package_relationships: List[pyecma376_2.OPCRelationship] = [
            pyecma376_2.OPCRelationship("r1", "http://www.admin-shell.io/aasx/relationships/aasx-origin",
                                        self.AASX_ORIGIN_PART_NAME,
                                        pyecma376_2.OPCTargetMode.INTERNAL),
        ]
        if self._properties_part is not None:
            package_relationships.append(pyecma376_2.OPCRelationship(
                "r2", pyecma376_2.RELATIONSHIP_TYPE_CORE_PROPERTIES, self._properties_part,
                pyecma376_2.OPCTargetMode.INTERNAL))
        if self._thumbnail_part is not None:
            package_relationships.append(pyecma376_2.OPCRelationship(
                "r3", pyecma376_2.RELATIONSHIP_TYPE_THUMBNAIL, self._thumbnail_part,
                pyecma376_2.OPCTargetMode.INTERNAL))
        self.writer.write_relationships(package_relationships)


class NameFriendlyfier:
    """
    A simple helper class to create unique "AAS friendly names" according to DotAAS, section 7.6.

    Objects of this class store the already created friendly names to avoid name collisions within one set of names.
    """
    RE_NON_ALPHANUMERICAL = re.compile(r"[^a-zA-Z0-9]")

    def __init__(self) -> None:
        self.issued_names: Set[str] = set()

    def get_friendly_name(self, identifier: model.Identifier):
        """
        Generate a friendly name from an AAS identifier.

        According to section 7.6 of "Details of the Asset Administration Shell", all non-alphanumerical characters are
        replaced with underscores. We also replace all non-ASCII characters to generate valid URIs as the result.
        If this replacement results in a collision with a previously generated friendly name of this NameFriendlifier,
        a number is appended with underscore to the friendly name. Example

            >>> friendlyfier = NameFriendlyfier()
            >>> friendlyfier.get_friendly_name(model.Identifier("http://example.com/AAS-a", model.IdentifierType.IRI))
            "http___example_com_AAS_a"
            >>> friendlyfier.get_friendly_name(model.Identifier("http://example.com/AAS+a", model.IdentifierType.IRI))
            "http___example_com_AAS_a_1"

        """
        # friendlify name
        raw_name = self.RE_NON_ALPHANUMERICAL.sub('_', identifier.id)

        # Unify name (avoid collisions)
        amended_name = raw_name
        i = 1
        while amended_name in self.issued_names:
            amended_name = "{}_{}".format(raw_name, i)
            i += 1

        self.issued_names.add(amended_name)
        return amended_name


class AbstractSupplementaryFileContainer(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def add_file(self, name: str, file: IO[bytes], content_type: str) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def get_content_type(self, name: str) -> str:
        pass  # pragma: no cover

    @abc.abstractmethod
    def write_file(self, name: str, file: IO[bytes]) -> None:
        pass  # pragma: no cover

    @abc.abstractmethod
    def __contains__(self, item: str) -> bool:
        pass  # pragma: no cover


class DictSupplementaryFileContainer(AbstractSupplementaryFileContainer, Dict[str, Tuple[bytes, str]]):
    def add_file(self, name: str, file: IO[bytes], content_type: str) -> None:
        self[name] = (file.read(), content_type)

    def get_content_type(self, name: str) -> str:
        return self[name][1]

    def write_file(self, name: str, file: IO[bytes]) -> None:
        file.write(self[name][0])

    def __contains__(self, item: object) -> bool: ...   # This stub is required to make MyPy happy
