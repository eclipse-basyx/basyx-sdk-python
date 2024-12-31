# Copyright (c) 2024 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module implements the "Specification of the Asset Administration Shell Part 2 Application Programming Interfaces".
However, several features and routes are currently not supported:

1. Correlation ID: Not implemented because it was deemed unnecessary for this server.

2. Extent Parameter (`withBlobValue/withoutBlobValue`):
   Not implemented due to the lack of support in JSON/XML serialization.

3. Route `/shells/{aasIdentifier}/asset-information/thumbnail`: Not implemented because the specification lacks clarity.

4. Serialization and Description Routes:
   - `/serialization`
   - `/description`
   These routes are not implemented at this time.

5. Value, Path, and PATCH Routes:
   - All `/…/value$`, `/…/path$`, and `PATCH` routes are currently not implemented.

6. Operation Invocation Routes: The following routes are not implemented because operation invocation
   is not yet supported by the `basyx-python-sdk`:
   - `POST /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke`
   - `POST /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke/$value`
   - `POST /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async`
   - `POST /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/invoke-async/$value`
   - `GET /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-status/{handleId}`
   - `GET /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}`
   - `GET /submodels/{submodelIdentifier}/submodel-elements/{idShortPath}/operation-results/{handleId}/$value`
"""

import abc
import base64
import binascii
import datetime
import enum
import io
import json
import itertools

from lxml import etree
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import werkzeug.utils
from werkzeug.exceptions import BadRequest, Conflict, NotFound, UnprocessableEntity
from werkzeug.routing import MapAdapter, Rule, Submount
from werkzeug.wrappers import Request, Response
from werkzeug.datastructures import FileStorage

from basyx.aas import model
from ._generic import XML_NS_MAP
from .xml import XMLConstructables, read_aas_xml_element, xml_serialization, object_to_xml_element
from .json import AASToJsonEncoder, StrictAASFromJsonDecoder, StrictStrippedAASFromJsonDecoder
from . import aasx

from typing import Callable, Dict, Iterable, Iterator, List, Optional, Type, TypeVar, Union, Tuple


@enum.unique
class MessageType(enum.Enum):
    UNDEFINED = enum.auto()
    INFO = enum.auto()
    WARNING = enum.auto()
    ERROR = enum.auto()
    EXCEPTION = enum.auto()

    def __str__(self):
        return self.name.capitalize()


class Message:
    def __init__(self, code: str, text: str, message_type: MessageType = MessageType.UNDEFINED,
                 timestamp: Optional[datetime.datetime] = None):
        self.code: str = code
        self.text: str = text
        self.message_type: MessageType = message_type
        self.timestamp: datetime.datetime = timestamp if timestamp is not None \
            else datetime.datetime.now(datetime.timezone.utc)


class Result:
    def __init__(self, success: bool, messages: Optional[List[Message]] = None):
        if messages is None:
            messages = []
        self.success: bool = success
        self.messages: List[Message] = messages


class ResultToJsonEncoder(AASToJsonEncoder):
    @classmethod
    def _result_to_json(cls, result: Result) -> Dict[str, object]:
        return {
            "success": result.success,
            "messages": result.messages
        }

    @classmethod
    def _message_to_json(cls, message: Message) -> Dict[str, object]:
        return {
            "messageType": message.message_type,
            "text": message.text,
            "code": message.code,
            "timestamp": message.timestamp.isoformat()
        }

    def default(self, obj: object) -> object:
        if isinstance(obj, Result):
            return self._result_to_json(obj)
        if isinstance(obj, Message):
            return self._message_to_json(obj)
        if isinstance(obj, MessageType):
            return str(obj)
        return super().default(obj)


class StrippedResultToJsonEncoder(ResultToJsonEncoder):
    stripped = True


ResponseData = Union[Result, object, List[object]]


class APIResponse(abc.ABC, Response):
    @abc.abstractmethod
    def __init__(self, obj: Optional[ResponseData] = None, cursor: Optional[int] = None,
                 stripped: bool = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if obj is None:
            self.status_code = 204
        else:
            self.data = self.serialize(obj, cursor, stripped)

    @abc.abstractmethod
    def serialize(self, obj: ResponseData, cursor: Optional[int], stripped: bool) -> str:
        pass


class JsonResponse(APIResponse):
    def __init__(self, *args, content_type="application/json", **kwargs):
        super().__init__(*args, **kwargs, content_type=content_type)

    def serialize(self, obj: ResponseData, cursor: Optional[int], stripped: bool) -> str:
        if cursor is None:
            data = obj
        else:
            data = {
                "paging_metadata": {"cursor": str(cursor)},
                "result": obj
            }
        return json.dumps(
            data,
            cls=StrippedResultToJsonEncoder if stripped else ResultToJsonEncoder,
            separators=(",", ":")
        )


class XmlResponse(APIResponse):
    def __init__(self, *args, content_type="application/xml", **kwargs):
        super().__init__(*args, **kwargs, content_type=content_type)

    def serialize(self, obj: ResponseData, cursor: Optional[int], stripped: bool) -> str:
        root_elem = etree.Element("response", nsmap=XML_NS_MAP)
        if cursor is not None:
            root_elem.set("cursor", str(cursor))
        if isinstance(obj, Result):
            result_elem = result_to_xml(obj, **XML_NS_MAP)
            for child in result_elem:
                root_elem.append(child)
        elif isinstance(obj, list):
            for item in obj:
                item_elem = object_to_xml_element(item)
                root_elem.append(item_elem)
        else:
            obj_elem = object_to_xml_element(obj)
            for child in obj_elem:
                root_elem.append(child)
        etree.cleanup_namespaces(root_elem)
        xml_str = etree.tostring(root_elem, xml_declaration=True, encoding="utf-8")
        return xml_str  # type: ignore[return-value]


class XmlResponseAlt(XmlResponse):
    def __init__(self, *args, content_type="text/xml", **kwargs):
        super().__init__(*args, **kwargs, content_type=content_type)


def result_to_xml(result: Result, **kwargs) -> etree._Element:
    result_elem = etree.Element("result", **kwargs)
    success_elem = etree.Element("success")
    success_elem.text = xml_serialization.boolean_to_xml(result.success)
    messages_elem = etree.Element("messages")
    for message in result.messages:
        messages_elem.append(message_to_xml(message))

    result_elem.append(success_elem)
    result_elem.append(messages_elem)
    return result_elem


def message_to_xml(message: Message) -> etree._Element:
    message_elem = etree.Element("message")
    message_type_elem = etree.Element("messageType")
    message_type_elem.text = str(message.message_type)
    text_elem = etree.Element("text")
    text_elem.text = message.text
    code_elem = etree.Element("code")
    code_elem.text = message.code
    timestamp_elem = etree.Element("timestamp")
    timestamp_elem.text = message.timestamp.isoformat()

    message_elem.append(message_type_elem)
    message_elem.append(text_elem)
    message_elem.append(code_elem)
    message_elem.append(timestamp_elem)
    return message_elem


def get_response_type(request: Request) -> Type[APIResponse]:
    response_types: Dict[str, Type[APIResponse]] = {
        "application/json": JsonResponse,
        "application/xml": XmlResponse,
        "text/xml": XmlResponseAlt
    }
    if len(request.accept_mimetypes) == 0 or request.accept_mimetypes.best in (None, "*/*"):
        return JsonResponse
    mime_type = request.accept_mimetypes.best_match(response_types)
    if mime_type is None:
        raise werkzeug.exceptions.NotAcceptable("This server supports the following content types: "
                                                + ", ".join(response_types.keys()))
    return response_types[mime_type]


def http_exception_to_response(exception: werkzeug.exceptions.HTTPException, response_type: Type[APIResponse]) \
        -> APIResponse:
    headers = exception.get_headers()
    location = exception.get_response().location
    if location is not None:
        headers.append(("Location", location))
    if exception.code and exception.code >= 400:
        message = Message(type(exception).__name__, exception.description if exception.description is not None else "",
                          MessageType.ERROR)
        result = Result(False, [message])
    else:
        result = Result(False)
    return response_type(result, status=exception.code, headers=headers)


def is_stripped_request(request: Request) -> bool:
    return request.args.get("level") == "core"


T = TypeVar("T")

BASE64URL_ENCODING = "utf-8"


def base64url_decode(data: str) -> str:
    try:
        # If the requester omits the base64 padding, an exception will be raised.
        # However, Python doesn't complain about too much padding,
        # thus we simply always append two padding characters (==).
        # See also: https://stackoverflow.com/a/49459036/4780052
        decoded = base64.urlsafe_b64decode(data + "==").decode(BASE64URL_ENCODING)
    except binascii.Error:
        raise BadRequest(f"Encoded data {data} is invalid base64url!")
    except UnicodeDecodeError:
        raise BadRequest(f"Encoded base64url value is not a valid {BASE64URL_ENCODING} string!")
    return decoded


def base64url_encode(data: str) -> str:
    encoded = base64.urlsafe_b64encode(data.encode(BASE64URL_ENCODING)).decode("ascii")
    return encoded


class HTTPApiDecoder:
    # these are the types we can construct (well, only the ones we need)
    type_constructables_map = {
        model.AssetAdministrationShell: XMLConstructables.ASSET_ADMINISTRATION_SHELL,
        model.AssetInformation: XMLConstructables.ASSET_INFORMATION,
        model.ModelReference: XMLConstructables.MODEL_REFERENCE,
        model.SpecificAssetId: XMLConstructables.SPECIFIC_ASSET_ID,
        model.Qualifier: XMLConstructables.QUALIFIER,
        model.Submodel: XMLConstructables.SUBMODEL,
        model.SubmodelElement: XMLConstructables.SUBMODEL_ELEMENT,
        model.Reference: XMLConstructables.REFERENCE
    }

    @classmethod
    def check_type_supportance(cls, type_: type):
        if type_ not in cls.type_constructables_map:
            raise TypeError(f"Parsing {type_} is not supported!")

    @classmethod
    def assert_type(cls, obj: object, type_: Type[T]) -> T:
        if not isinstance(obj, type_):
            raise UnprocessableEntity(f"Object {obj!r} is not of type {type_.__name__}!")
        return obj

    @classmethod
    def json_list(cls, data: Union[str, bytes], expect_type: Type[T], stripped: bool, expect_single: bool) -> List[T]:
        cls.check_type_supportance(expect_type)
        decoder: Type[StrictAASFromJsonDecoder] = StrictStrippedAASFromJsonDecoder if stripped \
            else StrictAASFromJsonDecoder
        try:
            parsed = json.loads(data, cls=decoder)
            if not isinstance(parsed, list):
                if not expect_single:
                    raise UnprocessableEntity(f"Expected List[{expect_type.__name__}], got {parsed!r}!")
                parsed = [parsed]
            elif expect_single:
                raise UnprocessableEntity(f"Expected a single object of type {expect_type.__name__}, got {parsed!r}!")
            # TODO: the following is ugly, but necessary because references aren't self-identified objects
            #  in the json schema
            # TODO: json deserialization will always create an ModelReference[Submodel], xml deserialization determines
            #  that automatically
            constructor: Optional[Callable[..., T]] = None
            args = []
            if expect_type is model.ModelReference:
                constructor = decoder._construct_model_reference  # type: ignore[assignment]
                args.append(model.Submodel)
            elif expect_type is model.AssetInformation:
                constructor = decoder._construct_asset_information  # type: ignore[assignment]
            elif expect_type is model.SpecificAssetId:
                constructor = decoder._construct_specific_asset_id  # type: ignore[assignment]
            elif expect_type is model.Reference:
                constructor = decoder._construct_reference  # type: ignore[assignment]
            elif expect_type is model.Qualifier:
                constructor = decoder._construct_qualifier  # type: ignore[assignment]

            if constructor is not None:
                # construct elements that aren't self-identified
                return [constructor(obj, *args) for obj in parsed]

        except (KeyError, ValueError, TypeError, json.JSONDecodeError, model.AASConstraintViolation) as e:
            raise UnprocessableEntity(str(e)) from e

        return [cls.assert_type(obj, expect_type) for obj in parsed]

    @classmethod
    def base64urljson_list(cls, data: str, expect_type: Type[T], stripped: bool, expect_single: bool) -> List[T]:
        data = base64url_decode(data)
        return cls.json_list(data, expect_type, stripped, expect_single)

    @classmethod
    def json(cls, data: Union[str, bytes], expect_type: Type[T], stripped: bool) -> T:
        return cls.json_list(data, expect_type, stripped, True)[0]

    @classmethod
    def base64urljson(cls, data: str, expect_type: Type[T], stripped: bool) -> T:
        data = base64url_decode(data)
        return cls.json_list(data, expect_type, stripped, True)[0]

    @classmethod
    def xml(cls, data: bytes, expect_type: Type[T], stripped: bool) -> T:
        cls.check_type_supportance(expect_type)
        try:
            xml_data = io.BytesIO(data)
            rv = read_aas_xml_element(xml_data, cls.type_constructables_map[expect_type],
                                      stripped=stripped, failsafe=False)
        except (KeyError, ValueError) as e:
            # xml deserialization creates an error chain. since we only return one error, return the root cause
            f: BaseException = e
            while f.__cause__ is not None:
                f = f.__cause__
            raise UnprocessableEntity(str(f)) from e
        except (etree.XMLSyntaxError, model.AASConstraintViolation) as e:
            raise UnprocessableEntity(str(e)) from e
        return cls.assert_type(rv, expect_type)

    @classmethod
    def request_body(cls, request: Request, expect_type: Type[T], stripped: bool) -> T:
        """
        TODO: werkzeug documentation recommends checking the content length before retrieving the body to prevent
              running out of memory. but it doesn't state how to check the content length
              also: what would be a reasonable maximum content length? the request body isn't limited by the xml/json
              schema
            In the meeting (25.11.2020) we discussed, this may refer to a reverse proxy in front of this WSGI app,
            which should limit the maximum content length.
        """
        valid_content_types = ("application/json", "application/xml", "text/xml")

        if request.mimetype not in valid_content_types:
            raise werkzeug.exceptions.UnsupportedMediaType(
                f"Invalid content-type: {request.mimetype}! Supported types: "
                + ", ".join(valid_content_types))

        if request.mimetype == "application/json":
            return cls.json(request.get_data(), expect_type, stripped)
        return cls.xml(request.get_data(), expect_type, stripped)


class Base64URLConverter(werkzeug.routing.UnicodeConverter):

    def to_url(self, value: model.Identifier) -> str:
        return super().to_url(base64url_encode(value))

    def to_python(self, value: str) -> model.Identifier:
        value = super().to_python(value)
        decoded = base64url_decode(super().to_python(value))
        return decoded


class IdShortPathConverter(werkzeug.routing.UnicodeConverter):
    id_short_sep = "."

    def to_url(self, value: List[str]) -> str:
        return super().to_url(self.id_short_sep.join(value))

    def to_python(self, value: str) -> List[str]:
        id_shorts = super().to_python(value).split(self.id_short_sep)
        for id_short in id_shorts:
            try:
                model.Referable.validate_id_short(id_short)
            except (ValueError, model.AASConstraintViolation):
                raise BadRequest(f"{id_short} is not a valid id_short!")
        return id_shorts


class WSGIApp:
    def __init__(self, object_store: model.AbstractObjectStore, file_store: aasx.AbstractSupplementaryFileContainer,
                 base_path: str = "/api/v3.0"):
        self.object_store: model.AbstractObjectStore = object_store
        self.file_store: aasx.AbstractSupplementaryFileContainer = file_store
        self.url_map = werkzeug.routing.Map([
            Submount(base_path, [
                Rule("/serialization", methods=["GET"], endpoint=self.not_implemented),
                Rule("/description", methods=["GET"], endpoint=self.not_implemented),
                Rule("/shells", methods=["GET"], endpoint=self.get_aas_all),
                Rule("/shells", methods=["POST"], endpoint=self.post_aas),
                Submount("/shells", [
                    Rule("/$reference", methods=["GET"], endpoint=self.get_aas_all_reference),
                    Rule("/<base64url:aas_id>", methods=["GET"], endpoint=self.get_aas),
                    Rule("/<base64url:aas_id>", methods=["PUT"], endpoint=self.put_aas),
                    Rule("/<base64url:aas_id>", methods=["DELETE"], endpoint=self.delete_aas),
                    Submount("/<base64url:aas_id>", [
                        Rule("/$reference", methods=["GET"], endpoint=self.get_aas_reference),
                        Rule("/asset-information", methods=["GET"], endpoint=self.get_aas_asset_information),
                        Rule("/asset-information", methods=["PUT"], endpoint=self.put_aas_asset_information),
                        Rule("/asset-information/thumbnail", methods=["GET", "PUT", "DELETE"],
                             endpoint=self.not_implemented),
                        Rule("/submodel-refs", methods=["GET"], endpoint=self.get_aas_submodel_refs),
                        Rule("/submodel-refs", methods=["POST"], endpoint=self.post_aas_submodel_refs),
                        Rule("/submodel-refs/<base64url:submodel_id>", methods=["DELETE"],
                             endpoint=self.delete_aas_submodel_refs_specific),
                        Submount("/submodels", [
                            Rule("/<base64url:submodel_id>", methods=["PUT"],
                                 endpoint=self.put_aas_submodel_refs_submodel),
                            Rule("/<base64url:submodel_id>", methods=["DELETE"],
                                 endpoint=self.delete_aas_submodel_refs_submodel),
                            Rule("/<base64url:submodel_id>", endpoint=self.aas_submodel_refs_redirect),
                            Rule("/<base64url:submodel_id>/<path:path>", endpoint=self.aas_submodel_refs_redirect)
                        ])
                    ])
                ]),
                Rule("/submodels", methods=["GET"], endpoint=self.get_submodel_all),
                Rule("/submodels", methods=["POST"], endpoint=self.post_submodel),
                Submount("/submodels", [
                    Rule("/$metadata", methods=["GET"], endpoint=self.get_submodel_all_metadata),
                    Rule("/$reference", methods=["GET"], endpoint=self.get_submodel_all_reference),
                    Rule("/$value", methods=["GET"], endpoint=self.not_implemented),
                    Rule("/$path", methods=["GET"], endpoint=self.not_implemented),
                    Rule("/<base64url:submodel_id>", methods=["GET"], endpoint=self.get_submodel),
                    Rule("/<base64url:submodel_id>", methods=["PUT"], endpoint=self.put_submodel),
                    Rule("/<base64url:submodel_id>", methods=["DELETE"], endpoint=self.delete_submodel),
                    Rule("/<base64url:submodel_id>", methods=["PATCH"], endpoint=self.not_implemented),
                    Submount("/<base64url:submodel_id>", [
                        Rule("/$metadata", methods=["GET"], endpoint=self.get_submodels_metadata),
                        Rule("/$metadata", methods=["PATCH"], endpoint=self.not_implemented),
                        Rule("/$value", methods=["GET"], endpoint=self.not_implemented),
                        Rule("/$value", methods=["PATCH"], endpoint=self.not_implemented),
                        Rule("/$reference", methods=["GET"], endpoint=self.get_submodels_reference),
                        Rule("/$path", methods=["GET"], endpoint=self.not_implemented),
                        Rule("/submodel-elements", methods=["GET"], endpoint=self.get_submodel_submodel_elements),
                        Rule("/submodel-elements", methods=["POST"],
                             endpoint=self.post_submodel_submodel_elements_id_short_path),
                        Submount("/submodel-elements", [
                            Rule("/$metadata", methods=["GET"],
                                 endpoint=self.get_submodel_submodel_elements_metadata),
                            Rule("/$reference", methods=["GET"],
                                 endpoint=self.get_submodel_submodel_elements_reference),
                            Rule("/$value", methods=["GET"], endpoint=self.not_implemented),
                            Rule("/$path", methods=["GET"], endpoint=self.not_implemented),
                            Rule("/<id_short_path:id_shorts>", methods=["GET"],
                                 endpoint=self.get_submodel_submodel_elements_id_short_path),
                            Rule("/<id_short_path:id_shorts>", methods=["POST"],
                                 endpoint=self.post_submodel_submodel_elements_id_short_path),
                            Rule("/<id_short_path:id_shorts>", methods=["PUT"],
                                 endpoint=self.put_submodel_submodel_elements_id_short_path),
                            Rule("/<id_short_path:id_shorts>", methods=["DELETE"],
                                 endpoint=self.delete_submodel_submodel_elements_id_short_path),
                            Rule("/<id_short_path:id_shorts>", methods=["PATCH"], endpoint=self.not_implemented),
                            Submount("/<id_short_path:id_shorts>", [
                                Rule("/$metadata", methods=["GET"],
                                     endpoint=self.get_submodel_submodel_elements_id_short_path_metadata),
                                Rule("/$metadata", methods=["PATCH"], endpoint=self.not_implemented),
                                Rule("/$reference", methods=["GET"],
                                     endpoint=self.get_submodel_submodel_elements_id_short_path_reference),
                                Rule("/$value", methods=["GET"], endpoint=self.not_implemented),
                                Rule("/$value", methods=["PATCH"], endpoint=self.not_implemented),
                                Rule("/$path", methods=["GET"], endpoint=self.not_implemented),
                                Rule("/attachment", methods=["GET"],
                                     endpoint=self.get_submodel_submodel_element_attachment),
                                Rule("/attachment", methods=["PUT"],
                                     endpoint=self.put_submodel_submodel_element_attachment),
                                Rule("/attachment", methods=["DELETE"],
                                     endpoint=self.delete_submodel_submodel_element_attachment),
                                Rule("/invoke", methods=["POST"], endpoint=self.not_implemented),
                                Rule("/invoke/$value", methods=["POST"], endpoint=self.not_implemented),
                                Rule("/invoke-async", methods=["POST"], endpoint=self.not_implemented),
                                Rule("/invoke-async/$value", methods=["POST"], endpoint=self.not_implemented),
                                Rule("/operation-status/<base64url:handleId>", methods=["GET"],
                                     endpoint=self.not_implemented),
                                Submount("/operation-results", [
                                    Rule("/<base64url:handleId>", methods=["GET"],
                                         endpoint=self.not_implemented),
                                    Rule("/<base64url:handleId>/$value", methods=["GET"],
                                         endpoint=self.not_implemented)
                                ]),
                                Rule("/qualifiers", methods=["GET"],
                                     endpoint=self.get_submodel_submodel_element_qualifiers),
                                Rule("/qualifiers", methods=["POST"],
                                     endpoint=self.post_submodel_submodel_element_qualifiers),
                                Submount("/qualifiers", [
                                    Rule("/<base64url:qualifier_type>", methods=["GET"],
                                         endpoint=self.get_submodel_submodel_element_qualifiers),
                                    Rule("/<base64url:qualifier_type>", methods=["PUT"],
                                         endpoint=self.put_submodel_submodel_element_qualifiers),
                                    Rule("/<base64url:qualifier_type>", methods=["DELETE"],
                                         endpoint=self.delete_submodel_submodel_element_qualifiers)
                                ])
                            ])
                        ]),
                        Rule("/qualifiers", methods=["GET"],
                             endpoint=self.get_submodel_submodel_element_qualifiers),
                        Rule("/qualifiers", methods=["POST"],
                             endpoint=self.post_submodel_submodel_element_qualifiers),
                        Submount("/qualifiers", [
                            Rule("/<base64url:qualifier_type>", methods=["GET"],
                                 endpoint=self.get_submodel_submodel_element_qualifiers),
                            Rule("/<base64url:qualifier_type>", methods=["PUT"],
                                 endpoint=self.put_submodel_submodel_element_qualifiers),
                            Rule("/<base64url:qualifier_type>", methods=["DELETE"],
                                 endpoint=self.delete_submodel_submodel_element_qualifiers)
                        ])
                    ])
                ]),
                Rule("/concept-descriptions", methods=["GET"], endpoint=self.get_concept_description_all),
                Rule("/concept-descriptions", methods=["POST"], endpoint=self.post_concept_description),
                Submount("/concept-descriptions", [
                    Rule("/<base64url:concept_id>", methods=["GET"], endpoint=self.get_concept_description),
                    Rule("/<base64url:concept_id>", methods=["PUT"], endpoint=self.put_concept_description),
                    Rule("/<base64url:concept_id>", methods=["DELETE"], endpoint=self.delete_concept_description),
                ]),
            ])
        ], converters={
            "base64url": Base64URLConverter,
            "id_short_path": IdShortPathConverter
        }, strict_slashes=False)

    # TODO: the parameters can be typed via builtin wsgiref with Python 3.11+
    def __call__(self, environ, start_response) -> Iterable[bytes]:
        response: Response = self.handle_request(Request(environ))
        return response(environ, start_response)

    def _get_obj_ts(self, identifier: model.Identifier, type_: Type[model.provider._IT]) -> model.provider._IT:
        identifiable = self.object_store.get(identifier)
        if not isinstance(identifiable, type_):
            raise NotFound(f"No {type_.__name__} with {identifier} found!")
        identifiable.update()
        return identifiable

    def _get_all_obj_of_type(self, type_: Type[model.provider._IT]) -> Iterator[model.provider._IT]:
        for obj in self.object_store:
            if isinstance(obj, type_):
                obj.update()
                yield obj

    def _resolve_reference(self, reference: model.ModelReference[model.base._RT]) -> model.base._RT:
        try:
            return reference.resolve(self.object_store)
        except (KeyError, TypeError, model.UnexpectedTypeError) as e:
            raise werkzeug.exceptions.InternalServerError(str(e)) from e

    @classmethod
    def _get_nested_submodel_element(cls, namespace: model.UniqueIdShortNamespace, id_shorts: List[str]) \
            -> model.SubmodelElement:
        if not id_shorts:
            raise ValueError("No id_shorts specified!")

        try:
            ret = namespace.get_referable(id_shorts)
        except KeyError as e:
            raise NotFound(e.args[0])
        except (TypeError, ValueError) as e:
            raise BadRequest(e.args[0])

        if not isinstance(ret, model.SubmodelElement):
            raise BadRequest(f"{ret!r} is not a submodel element!")
        return ret

    def _get_submodel_or_nested_submodel_element(self, url_args: Dict) -> Union[model.Submodel, model.SubmodelElement]:
        submodel = self._get_submodel(url_args)
        id_shorts: List[str] = url_args.get("id_shorts", [])
        try:
            return self._get_nested_submodel_element(submodel, id_shorts)
        except ValueError:
            return submodel

    @classmethod
    def _expect_namespace(cls, obj: object, needle: str) -> model.UniqueIdShortNamespace:
        if not isinstance(obj, model.UniqueIdShortNamespace):
            raise BadRequest(f"{obj!r} is not a namespace, can't locate {needle}!")
        return obj

    @classmethod
    def _namespace_submodel_element_op(cls, namespace: model.UniqueIdShortNamespace, op: Callable[[str], T], arg: str) \
            -> T:
        try:
            return op(arg)
        except KeyError as e:
            raise NotFound(f"Submodel element with id_short {arg} not found in {namespace!r}") from e

    @classmethod
    def _qualifiable_qualifier_op(cls, qualifiable: model.Qualifiable, op: Callable[[str], T], arg: str) -> T:
        try:
            return op(arg)
        except KeyError as e:
            raise NotFound(f"Qualifier with type {arg!r} not found in {qualifiable!r}") from e

    @classmethod
    def _get_submodel_reference(cls, aas: model.AssetAdministrationShell, submodel_id: model.NameType) \
            -> model.ModelReference[model.Submodel]:
        # TODO: this is currently O(n), could be O(1) as aas.submodel, but keys would have to precisely match, as they
        #  are hashed including their KeyType
        for ref in aas.submodel:
            if ref.get_identifier() == submodel_id:
                return ref
        raise NotFound(f"The AAS {aas!r} doesn't have a submodel reference to {submodel_id!r}!")

    @classmethod
    def _get_slice(cls, request: Request, iterator: Iterable[T]) -> Tuple[Iterator[T], int]:
        limit_str = request.args.get('limit', default="10")
        cursor_str = request.args.get('cursor', default="0")
        try:
            limit, cursor = int(limit_str), int(cursor_str)
            if limit < 0 or cursor < 0:
                raise ValueError
        except ValueError:
            raise BadRequest("Cursor and limit must be positive integers!")
        start_index = cursor
        end_index = cursor + limit
        paginated_slice = itertools.islice(iterator, start_index, end_index)
        return paginated_slice, end_index

    def _get_shells(self, request: Request) -> Tuple[Iterator[model.AssetAdministrationShell], int]:
        aas: Iterator[model.AssetAdministrationShell] = self._get_all_obj_of_type(model.AssetAdministrationShell)

        id_short = request.args.get("idShort")
        if id_short is not None:
            aas = filter(lambda shell: shell.id_short == id_short, aas)

        asset_ids = request.args.getlist("assetIds")
        if asset_ids is not None:
            # Decode and instantiate SpecificAssetIds
            # This needs to be a list, otherwise we can only iterate it once.
            specific_asset_ids: List[model.SpecificAssetId] = list(
                map(lambda asset_id: HTTPApiDecoder.base64urljson(asset_id, model.SpecificAssetId, False), asset_ids))
            # Filter AAS based on these SpecificAssetIds
            aas = filter(lambda shell: all(specific_asset_id in shell.asset_information.specific_asset_id
                                           for specific_asset_id in specific_asset_ids), aas)

        paginated_aas, end_index = self._get_slice(request, aas)
        return paginated_aas, end_index

    def _get_shell(self, url_args: Dict) -> model.AssetAdministrationShell:
        return self._get_obj_ts(url_args["aas_id"], model.AssetAdministrationShell)

    def _get_submodels(self, request: Request) -> Tuple[Iterator[model.Submodel], int]:
        submodels: Iterator[model.Submodel] = self._get_all_obj_of_type(model.Submodel)
        id_short = request.args.get("idShort")
        if id_short is not None:
            submodels = filter(lambda sm: sm.id_short == id_short, submodels)
        semantic_id = request.args.get("semanticId")
        if semantic_id is not None:
            spec_semantic_id = HTTPApiDecoder.base64urljson(
                semantic_id, model.Reference, False)  # type: ignore[type-abstract]
            submodels = filter(lambda sm: sm.semantic_id == spec_semantic_id, submodels)
        paginated_submodels, end_index = self._get_slice(request, submodels)
        return paginated_submodels, end_index

    def _get_submodel(self, url_args: Dict) -> model.Submodel:
        return self._get_obj_ts(url_args["submodel_id"], model.Submodel)

    def _get_submodel_submodel_elements(self, request: Request, url_args: Dict) -> \
            Tuple[Iterator[model.SubmodelElement], int]:
        submodel = self._get_submodel(url_args)
        paginated_submodel_elements: Iterator[model.SubmodelElement]
        paginated_submodel_elements, end_index = self._get_slice(request, submodel.submodel_element)
        return paginated_submodel_elements, end_index

    def _get_submodel_submodel_elements_id_short_path(self, url_args: Dict) -> model.SubmodelElement:
        submodel = self._get_submodel(url_args)
        submodel_element = self._get_nested_submodel_element(submodel, url_args["id_shorts"])
        return submodel_element

    def _get_concept_description(self, url_args):
        return self._get_obj_ts(url_args["concept_id"], model.ConceptDescription)

    def handle_request(self, request: Request):
        map_adapter: MapAdapter = self.url_map.bind_to_environ(request.environ)
        try:
            response_t = get_response_type(request)
        except werkzeug.exceptions.NotAcceptable as e:
            return e

        try:
            endpoint, values = map_adapter.match()
            return endpoint(request, values, response_t=response_t, map_adapter=map_adapter)

        # any raised error that leaves this function will cause a 500 internal server error
        # so catch raised http exceptions and return them
        except werkzeug.exceptions.HTTPException as e:
            return http_exception_to_response(e, response_t)

    # ------ all not implemented ROUTES -------
    def not_implemented(self, request: Request, url_args: Dict, **_kwargs) -> Response:
        raise werkzeug.exceptions.NotImplemented("This route is not implemented!")

    # ------ AAS REPO ROUTES -------
    def get_aas_all(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        aashells, cursor = self._get_shells(request)
        return response_t(list(aashells), cursor=cursor)

    def post_aas(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                 map_adapter: MapAdapter) -> Response:
        aas = HTTPApiDecoder.request_body(request, model.AssetAdministrationShell, False)
        try:
            self.object_store.add(aas)
        except KeyError as e:
            raise Conflict(f"AssetAdministrationShell with Identifier {aas.id} already exists!") from e
        aas.commit()
        created_resource_url = map_adapter.build(self.get_aas, {
            "aas_id": aas.id
        }, force_external=True)
        return response_t(aas, status=201, headers={"Location": created_resource_url})

    def get_aas_all_reference(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                              **_kwargs) -> Response:
        aashells, cursor = self._get_shells(request)
        references: list[model.ModelReference] = [model.ModelReference.from_referable(aas)
                                                  for aas in aashells]
        return response_t(references, cursor=cursor)

    # --------- AAS ROUTES ---------
    def get_aas(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        return response_t(aas)

    def get_aas_reference(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        reference = model.ModelReference.from_referable(aas)
        return response_t(reference)

    def put_aas(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        aas.update_from(HTTPApiDecoder.request_body(request, model.AssetAdministrationShell,
                                                    is_stripped_request(request)))
        aas.commit()
        return response_t()

    def delete_aas(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        self.object_store.remove(aas)
        return response_t()

    def get_aas_asset_information(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                  **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        return response_t(aas.asset_information)

    def put_aas_asset_information(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                  **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        aas.asset_information = HTTPApiDecoder.request_body(request, model.AssetInformation, False)
        aas.commit()
        return response_t()

    def get_aas_submodel_refs(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                              **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        submodel_refs: Iterator[model.ModelReference[model.Submodel]]
        submodel_refs, cursor = self._get_slice(request, aas.submodel)
        return response_t(list(submodel_refs), cursor=cursor)

    def post_aas_submodel_refs(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                               **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        sm_ref = HTTPApiDecoder.request_body(request, model.ModelReference, False)
        if sm_ref in aas.submodel:
            raise Conflict(f"{sm_ref!r} already exists!")
        aas.submodel.add(sm_ref)
        aas.commit()
        return response_t(sm_ref, status=201)

    def delete_aas_submodel_refs_specific(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                          **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        aas.submodel.remove(self._get_submodel_reference(aas, url_args["submodel_id"]))
        aas.commit()
        return response_t()

    def put_aas_submodel_refs_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                       **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        sm_ref = self._get_submodel_reference(aas, url_args["submodel_id"])
        submodel = self._resolve_reference(sm_ref)
        new_submodel = HTTPApiDecoder.request_body(request, model.Submodel, is_stripped_request(request))
        # determine whether the id changed in advance, in case something goes wrong while updating the submodel
        id_changed: bool = submodel.id != new_submodel.id
        # TODO: https://github.com/eclipse-basyx/basyx-python-sdk/issues/216
        submodel.update_from(new_submodel)
        submodel.commit()
        if id_changed:
            aas.submodel.remove(sm_ref)
            aas.submodel.add(model.ModelReference.from_referable(submodel))
            aas.commit()
        return response_t()

    def delete_aas_submodel_refs_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                          **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        sm_ref = self._get_submodel_reference(aas, url_args["submodel_id"])
        submodel = self._resolve_reference(sm_ref)
        self.object_store.remove(submodel)
        aas.submodel.remove(sm_ref)
        aas.commit()
        return response_t()

    def aas_submodel_refs_redirect(self, request: Request, url_args: Dict, map_adapter: MapAdapter, response_t=None,
                                   **_kwargs) -> Response:
        aas = self._get_shell(url_args)
        # the following makes sure the reference exists
        self._get_submodel_reference(aas, url_args["submodel_id"])
        redirect_url = map_adapter.build(self.get_submodel, {
            "submodel_id": url_args["submodel_id"]
        }, force_external=True)
        if "path" in url_args:
            redirect_url += "/" + url_args["path"]
        if request.query_string:
            redirect_url += "?" + request.query_string.decode("ascii")
        return werkzeug.utils.redirect(redirect_url, 307)

    # ------ SUBMODEL REPO ROUTES -------
    def get_submodel_all(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        submodels, cursor = self._get_submodels(request)
        return response_t(list(submodels), cursor=cursor, stripped=is_stripped_request(request))

    def post_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                      map_adapter: MapAdapter) -> Response:
        submodel = HTTPApiDecoder.request_body(request, model.Submodel, is_stripped_request(request))
        try:
            self.object_store.add(submodel)
        except KeyError as e:
            raise Conflict(f"Submodel with Identifier {submodel.id} already exists!") from e
        submodel.commit()
        created_resource_url = map_adapter.build(self.get_submodel, {
            "submodel_id": submodel.id
        }, force_external=True)
        return response_t(submodel, status=201, headers={"Location": created_resource_url})

    def get_submodel_all_metadata(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                  **_kwargs) -> Response:
        submodels, cursor = self._get_submodels(request)
        return response_t(list(submodels), cursor=cursor, stripped=True)

    def get_submodel_all_reference(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                   **_kwargs) -> Response:
        submodels, cursor = self._get_submodels(request)
        references: list[model.ModelReference] = [model.ModelReference.from_referable(submodel)
                                                  for submodel in submodels]
        return response_t(references, cursor=cursor, stripped=is_stripped_request(request))

    # --------- SUBMODEL ROUTES ---------

    def delete_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        self.object_store.remove(self._get_obj_ts(url_args["submodel_id"], model.Submodel))
        return response_t()

    def get_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        submodel = self._get_submodel(url_args)
        return response_t(submodel, stripped=is_stripped_request(request))

    def get_submodels_metadata(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                               **_kwargs) -> Response:
        submodel = self._get_submodel(url_args)
        return response_t(submodel, stripped=True)

    def get_submodels_reference(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                **_kwargs) -> Response:
        submodel = self._get_submodel(url_args)
        reference = model.ModelReference.from_referable(submodel)
        return response_t(reference, stripped=is_stripped_request(request))

    def put_submodel(self, request: Request, url_args: Dict, response_t: Type[APIResponse], **_kwargs) -> Response:
        submodel = self._get_submodel(url_args)
        submodel.update_from(HTTPApiDecoder.request_body(request, model.Submodel, is_stripped_request(request)))
        submodel.commit()
        return response_t()

    def get_submodel_submodel_elements(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                       **_kwargs) -> Response:
        submodel_elements, cursor = self._get_submodel_submodel_elements(request, url_args)
        return response_t(list(submodel_elements), cursor=cursor, stripped=is_stripped_request(request))

    def get_submodel_submodel_elements_metadata(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                **_kwargs) -> Response:
        submodel_elements, cursor = self._get_submodel_submodel_elements(request, url_args)
        return response_t(list(submodel_elements), cursor=cursor, stripped=True)

    def get_submodel_submodel_elements_reference(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                 **_kwargs) -> Response:
        submodel_elements, cursor = self._get_submodel_submodel_elements(request, url_args)
        references: list[model.ModelReference] = [model.ModelReference.from_referable(element) for element in
                                                  list(submodel_elements)]
        return response_t(references, cursor=cursor, stripped=is_stripped_request(request))

    def get_submodel_submodel_elements_id_short_path(self, request: Request, url_args: Dict,
                                                     response_t: Type[APIResponse],
                                                     **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        return response_t(submodel_element, stripped=is_stripped_request(request))

    def get_submodel_submodel_elements_id_short_path_metadata(self, request: Request, url_args: Dict,
                                                              response_t: Type[APIResponse], **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        return response_t(submodel_element, stripped=True)

    def get_submodel_submodel_elements_id_short_path_reference(self, request: Request, url_args: Dict,
                                                               response_t: Type[APIResponse], **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        reference = model.ModelReference.from_referable(submodel_element)
        return response_t(reference, stripped=is_stripped_request(request))

    def post_submodel_submodel_elements_id_short_path(self, request: Request, url_args: Dict,
                                                      response_t: Type[APIResponse],
                                                      map_adapter: MapAdapter):
        parent = self._get_submodel_or_nested_submodel_element(url_args)
        if not isinstance(parent, model.UniqueIdShortNamespace):
            raise BadRequest(f"{parent!r} is not a namespace, can't add child submodel element!")
        # TODO: remove the following type: ignore comment when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        new_submodel_element = HTTPApiDecoder.request_body(request,
                                                           model.SubmodelElement,  # type: ignore[type-abstract]
                                                           is_stripped_request(request))
        try:
            parent.add_referable(new_submodel_element)
        except model.AASConstraintViolation as e:
            if e.constraint_id != 22:
                raise
            raise Conflict(f"SubmodelElement with idShort {new_submodel_element.id_short} already exists "
                           f"within {parent}!")
        submodel = self._get_submodel(url_args)
        id_short_path = url_args.get("id_shorts", [])
        created_resource_url = map_adapter.build(self.get_submodel_submodel_elements_id_short_path, {
            "submodel_id": submodel.id,
            "id_shorts": id_short_path + [new_submodel_element.id_short]
        }, force_external=True)
        return response_t(new_submodel_element, status=201, headers={"Location": created_resource_url})

    def put_submodel_submodel_elements_id_short_path(self, request: Request, url_args: Dict,
                                                     response_t: Type[APIResponse],
                                                     **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        # TODO: remove the following type: ignore comment when mypy supports abstract types for Type[T]
        # see https://github.com/python/mypy/issues/5374
        new_submodel_element = HTTPApiDecoder.request_body(request,
                                                           model.SubmodelElement,  # type: ignore[type-abstract]
                                                           is_stripped_request(request))
        submodel_element.update_from(new_submodel_element)
        submodel_element.commit()
        return response_t()

    def delete_submodel_submodel_elements_id_short_path(self, request: Request, url_args: Dict,
                                                        response_t: Type[APIResponse],
                                                        **_kwargs) -> Response:
        sm_or_se = self._get_submodel_or_nested_submodel_element(url_args)
        parent: model.UniqueIdShortNamespace = self._expect_namespace(sm_or_se.parent, sm_or_se.id_short)
        self._namespace_submodel_element_op(parent, parent.remove_referable, sm_or_se.id_short)
        return response_t()

    def get_submodel_submodel_element_attachment(self, request: Request, url_args: Dict, **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        if not isinstance(submodel_element, (model.Blob, model.File)):
            raise BadRequest(f"{submodel_element!r} is not a Blob or File, no file content to download!")
        if submodel_element.value is None:
            raise NotFound(f"{submodel_element!r} has no attachment!")

        value: bytes
        if isinstance(submodel_element, model.Blob):
            value = submodel_element.value
        else:
            if not submodel_element.value.startswith("/"):
                raise BadRequest(f"{submodel_element!r} references an external file: {submodel_element.value}")
            bytes_io = io.BytesIO()
            try:
                self.file_store.write_file(submodel_element.value, bytes_io)
            except KeyError:
                raise NotFound(f"No such file: {submodel_element.value}")
            value = bytes_io.getvalue()

        # Blob and File both have the content_type attribute
        return Response(value, content_type=submodel_element.content_type)  # type: ignore[attr-defined]

    def put_submodel_submodel_element_attachment(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                 **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)

        # spec allows PUT only for File, not for Blob
        if not isinstance(submodel_element, model.File):
            raise BadRequest(f"{submodel_element!r} is not a File, no file content to update!")
        elif submodel_element.value is not None:
            raise Conflict(f"{submodel_element!r} already references a file!")

        filename = request.form.get('fileName')
        if filename is None:
            raise BadRequest("No 'fileName' specified!")
        elif not filename.startswith("/"):
            raise BadRequest(f"Given 'fileName' doesn't start with a slash (/): {filename}")

        file_storage: Optional[FileStorage] = request.files.get('file')
        if file_storage is None:
            raise BadRequest("Missing file to upload")
        elif file_storage.mimetype != submodel_element.content_type:
            raise werkzeug.exceptions.UnsupportedMediaType(
                f"Request body is of type {file_storage.mimetype!r}, "
                f"while {submodel_element!r} has content_type {submodel_element.content_type!r}!")

        submodel_element.value = self.file_store.add_file(filename, file_storage.stream, submodel_element.content_type)
        submodel_element.commit()
        return response_t()

    def delete_submodel_submodel_element_attachment(self, request: Request, url_args: Dict,
                                                    response_t: Type[APIResponse],
                                                    **_kwargs) -> Response:
        submodel_element = self._get_submodel_submodel_elements_id_short_path(url_args)
        if not isinstance(submodel_element, (model.Blob, model.File)):
            raise BadRequest(f"{submodel_element!r} is not a Blob or File, no file content to delete!")
        elif submodel_element.value is None:
            raise NotFound(f"{submodel_element!r} has no attachment!")

        if isinstance(submodel_element, model.Blob):
            submodel_element.value = None
        else:
            if not submodel_element.value.startswith("/"):
                raise BadRequest(f"{submodel_element!r} references an external file: {submodel_element.value}")
            try:
                self.file_store.delete_file(submodel_element.value)
            except KeyError:
                pass
            submodel_element.value = None

        submodel_element.commit()
        return response_t()

    def get_submodel_submodel_element_qualifiers(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                 **_kwargs) -> Response:
        sm_or_se = self._get_submodel_or_nested_submodel_element(url_args)
        qualifier_type = url_args.get("qualifier_type")
        if qualifier_type is None:
            return response_t(list(sm_or_se.qualifier))
        return response_t(self._qualifiable_qualifier_op(sm_or_se, sm_or_se.get_qualifier_by_type, qualifier_type))

    def post_submodel_submodel_element_qualifiers(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                  map_adapter: MapAdapter) -> Response:
        sm_or_se = self._get_submodel_or_nested_submodel_element(url_args)
        qualifier = HTTPApiDecoder.request_body(request, model.Qualifier, is_stripped_request(request))
        if sm_or_se.qualifier.contains_id("type", qualifier.type):
            raise Conflict(f"Qualifier with type {qualifier.type} already exists!")
        sm_or_se.qualifier.add(qualifier)
        sm_or_se.commit()
        created_resource_url = map_adapter.build(self.get_submodel_submodel_element_qualifiers, {
            "submodel_id": url_args["submodel_id"],
            "id_shorts": url_args.get("id_shorts") or None,
            "qualifier_type": qualifier.type
        }, force_external=True)
        return response_t(qualifier, status=201, headers={"Location": created_resource_url})

    def put_submodel_submodel_element_qualifiers(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                                 map_adapter: MapAdapter) -> Response:
        sm_or_se = self._get_submodel_or_nested_submodel_element(url_args)
        new_qualifier = HTTPApiDecoder.request_body(request, model.Qualifier, is_stripped_request(request))
        qualifier_type = url_args["qualifier_type"]
        qualifier = self._qualifiable_qualifier_op(sm_or_se, sm_or_se.get_qualifier_by_type, qualifier_type)
        qualifier_type_changed = qualifier_type != new_qualifier.type
        if qualifier_type_changed and sm_or_se.qualifier.contains_id("type", new_qualifier.type):
            raise Conflict(f"A qualifier of type {new_qualifier.type!r} already exists for {sm_or_se!r}")
        sm_or_se.remove_qualifier_by_type(qualifier.type)
        sm_or_se.qualifier.add(new_qualifier)
        sm_or_se.commit()
        if qualifier_type_changed:
            created_resource_url = map_adapter.build(self.get_submodel_submodel_element_qualifiers, {
                "submodel_id": url_args["submodel_id"],
                "id_shorts": url_args.get("id_shorts") or None,
                "qualifier_type": new_qualifier.type
            }, force_external=True)
            return response_t(new_qualifier, status=201, headers={"Location": created_resource_url})
        return response_t(new_qualifier)

    def delete_submodel_submodel_element_qualifiers(self, request: Request, url_args: Dict,
                                                    response_t: Type[APIResponse],
                                                    **_kwargs) -> Response:
        sm_or_se = self._get_submodel_or_nested_submodel_element(url_args)
        qualifier_type = url_args["qualifier_type"]
        self._qualifiable_qualifier_op(sm_or_se, sm_or_se.remove_qualifier_by_type, qualifier_type)
        sm_or_se.commit()
        return response_t()

    # --------- CONCEPT DESCRIPTION ROUTES ---------
    def get_concept_description_all(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                    **_kwargs) -> Response:
        concept_descriptions: Iterator[model.ConceptDescription] = self._get_all_obj_of_type(model.ConceptDescription)
        concept_descriptions, cursor = self._get_slice(request, concept_descriptions)
        return response_t(list(concept_descriptions), cursor=cursor, stripped=is_stripped_request(request))

    def post_concept_description(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                 map_adapter: MapAdapter) -> Response:
        concept_description = HTTPApiDecoder.request_body(request, model.ConceptDescription,
                                                          is_stripped_request(request))
        try:
            self.object_store.add(concept_description)
        except KeyError as e:
            raise Conflict(f"ConceptDescription with Identifier {concept_description.id} already exists!") from e
        concept_description.commit()
        created_resource_url = map_adapter.build(self.get_concept_description, {
            "concept_id": concept_description.id
        }, force_external=True)
        return response_t(concept_description, status=201, headers={"Location": created_resource_url})

    def get_concept_description(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                **_kwargs) -> Response:
        concept_description = self._get_concept_description(url_args)
        return response_t(concept_description, stripped=is_stripped_request(request))

    def put_concept_description(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                **_kwargs) -> Response:
        concept_description = self._get_concept_description(url_args)
        concept_description.update_from(HTTPApiDecoder.request_body(request, model.ConceptDescription,
                                                                    is_stripped_request(request)))
        concept_description.commit()
        return response_t()

    def delete_concept_description(self, request: Request, url_args: Dict, response_t: Type[APIResponse],
                                   **_kwargs) -> Response:
        self.object_store.remove(self._get_concept_description(url_args))
        return response_t()


if __name__ == "__main__":
    from werkzeug.serving import run_simple
    from basyx.aas.examples.data.example_aas import create_full_example

    run_simple("localhost", 8080, WSGIApp(create_full_example(), aasx.DictSupplementaryFileContainer()),
               use_debugger=True, use_reloader=True)
