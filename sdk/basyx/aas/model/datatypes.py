# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
"""
This module defines native Python types for all simple built-in XSD datatypes, as well as functions to (de)serialize
them from/into their lexical XML representation.

See https://www.w3.org/TR/xmlschema-2/#built-in-datatypes for the XSD simple type hierarchy and more information on the
datatypes. All types from this type hierarchy (except for ``token`` and its descendants) are implemented or aliased in
this module using their pythonized: Duration, DateTime, GMonthDay, String, Integer, Decimal, Short …. These types are
meant to be used directly for data values in the context of Asset Administration Shells.

There are three conversion functions for usage in BaSyx Python SDK's model and adapters:

* :meth:`~basyx.aas.model.datatypes.xsd_repr` serializes any XSD type from this module into its lexical representation
* :meth:`~basyx.aas.model.datatypes.from_xsd` parses an XSD type from its lexical representation (its required to name
  the type for unambiguous conversion)
* :meth:`~basyx.aas.model.datatypes.trivial_cast` type-cast a python value into an XSD type,
  if this is trivially possible.
  Meant for fixing the type of :class:`Properties' <basyx.aas.model.submodel.Property>` values automatically,
  esp. for literal values.
"""
import base64
import datetime
import decimal
import re
from typing import Type, Union, Dict, Optional

import dateutil.relativedelta

Duration = dateutil.relativedelta.relativedelta
DateTime = datetime.datetime
Time = datetime.time
Boolean = bool
Double = float
Decimal = decimal.Decimal
Integer = int
String = str


class Date(datetime.date):
    __slots__ = '_tzinfo'

    def __new__(cls, year: int, month: Optional[int] = None, day: Optional[int] = None,
                tzinfo: Optional[datetime.tzinfo] = None) -> "Date":
        res: "Date" = datetime.date.__new__(cls, year, month, day)  # type: ignore  # pickle support is not in typeshed
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        res._tzinfo = tzinfo  # type: ignore  # Workaround for MyPy bug, not recognizing our additional __slots__
        return res

    def begin(self) -> datetime.datetime:
        return datetime.datetime(self.year, self.month, self.day, 0, 0, 0, 0, self.tzinfo)

    @property
    def tzinfo(self):
        """timezone info object"""
        return self._tzinfo

    def utcoffset(self):
        """Return the timezone offset as timedelta positive east of UTC (negative west of
        UTC)."""
        if self._tzinfo is None:
            return None
        return self._tzinfo.utcoffset(self)

    def __repr__(self):
        if self.tzinfo is not None:
            return super().__repr__()[:-1] + ", tzinfo={})".format(self.tzinfo)
        else:
            return super().__repr__()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, datetime.date):
            return NotImplemented
        other_tzinfo = other.tzinfo if hasattr(other, 'tzinfo') else None  # type: ignore
        return datetime.date.__eq__(self, other) and self.tzinfo == other_tzinfo

    def __copy__(self):
        cls = self.__class__
        result = cls.__new__(cls, self.year, self.month, self.day, self.tzinfo)
        return result

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls, self.year, self.month, self.day, self.tzinfo)
        memo[id(self)] = result
        return result

    # TODO override comparison operators
    # TODO add into_datetime function
    # TODO add includes(:DateTime) -> bool function


class GYearMonth:
    __slots__ = ('year', 'month', 'tzinfo')

    def __init__(self, year: int, month: int, tzinfo: Optional[datetime.tzinfo] = None):
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        if not 1 <= month <= 12:
            raise ValueError("{} is out of the allowed range for month".format(month))
        self.year: int = year
        self.month: int = month
        self.tzinfo: Optional[datetime.tzinfo] = tzinfo

    def into_date(self, day: int = 1) -> Date:
        return Date(self.year, self.month, day, self.tzinfo)

    @classmethod
    def from_date(cls, date: datetime.date) -> "GYearMonth":
        tzinfo = date.tzinfo if hasattr(date, 'tzinfo') else None  # type: ignore
        return cls(date.year, date.month, tzinfo)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GYearMonth):
            return NotImplemented
        return self.year == other.year and self.month == other.month and self.tzinfo == other.tzinfo

    # TODO override comparison operators
    # TODO add includes(:Union[DateTime, Date]) -> bool function


class GYear:
    __slots__ = ('year', 'tzinfo')

    def __init__(self, year: int, tzinfo: Optional[datetime.tzinfo] = None):
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        self.year: int = year
        self.tzinfo: Optional[datetime.tzinfo] = tzinfo

    def into_date(self, month: int = 1, day: int = 1) -> Date:
        return Date(self.year, month, day, self.tzinfo)

    @classmethod
    def from_date(cls, date: datetime.date) -> "GYear":
        tzinfo = date.tzinfo if hasattr(date, 'tzinfo') else None  # type: ignore
        return cls(date.year, tzinfo)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GYear):
            return NotImplemented
        return self.year == other.year and self.tzinfo == other.tzinfo

    # TODO override comparison operators
    # TODO add includes(:Union[DateTime, Date]) -> bool function


class GMonthDay:
    __slots__ = ('month', 'day', 'tzinfo')

    def __init__(self, month: int, day: int, tzinfo: Optional[datetime.tzinfo] = None):
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        if not 1 <= day <= 31:
            raise ValueError("{} is out of the allowed range for day of month".format(day))
        if not 1 <= month <= 12:
            raise ValueError("{} is out of the allowed range for month".format(month))
        self.month: int = month
        self.day: int = day
        self.tzinfo: Optional[datetime.tzinfo] = tzinfo

    def into_date(self, year: int = 1970) -> Date:
        return Date(year, self.month, self.day, self.tzinfo)

    @classmethod
    def from_date(cls, date: datetime.date) -> "GMonthDay":
        tzinfo = date.tzinfo if hasattr(date, 'tzinfo') else None  # type: ignore
        return cls(date.month, date.year, tzinfo)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GMonthDay):
            return NotImplemented
        return self.month == other.month and self.day == other.day and self.tzinfo == other.tzinfo

    # TODO override comparison operators
    # TODO add includes(:Union[DateTime, Date]) -> bool function


class GDay:
    __slots__ = ('day', 'tzinfo')

    def __init__(self, day: int, tzinfo: Optional[datetime.tzinfo] = None):
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        if not 1 <= day <= 31:
            raise ValueError("{} is out of the allowed range for day of month".format(day))
        self.day: int = day
        self.tzinfo: Optional[datetime.tzinfo] = tzinfo

    def into_date(self, year: int = 1970, month: int = 1) -> Date:
        return Date(year, month, self.day, self.tzinfo)

    @classmethod
    def from_date(cls, date: datetime.date) -> "GDay":
        tzinfo = date.tzinfo if hasattr(date, 'tzinfo') else None  # type: ignore
        return cls(date.day, tzinfo)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GDay):
            return NotImplemented
        return self.day == other.day and self.tzinfo == other.tzinfo

    # TODO override comparison operators
    # TODO add includes(:Union[DateTime, Date]) -> bool function


class GMonth:
    __slots__ = ('month', 'tzinfo')

    def __init__(self, month: int, tzinfo: Optional[datetime.tzinfo] = None):
        # TODO normalize tzinfo to '+12:00' through '-11:59'
        if not 1 <= month <= 12:
            raise ValueError("{} is out of the allowed range for month".format(month))
        self.month: int = month
        self.tzinfo: Optional[datetime.tzinfo] = tzinfo

    def into_date(self, year: int = 1970, day: int = 1) -> Date:
        return Date(year, self.month, day, self.tzinfo)

    @classmethod
    def from_date(cls, date: datetime.date) -> "GMonth":
        tzinfo = date.tzinfo if hasattr(date, 'tzinfo') else None  # type: ignore
        return cls(date.month, tzinfo)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GMonth):
            return NotImplemented
        return self.month == other.month and self.tzinfo == other.tzinfo

    # TODO override comparison operators
    # TODO add includes(:Union[DateTime, Date]) -> bool function


class Base64Binary(bytearray):
    pass


class HexBinary(bytearray):
    pass


class Float(float):
    """ A 32bit IEEE754 float. This can not be represented with Python """
    pass


class Long(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        # [-9223372036854775808, 9223372036854775807]
        if res > 2**63-1 or res < -2**63:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class Int(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        # [-2147483648, 2147483647]
        if res > 2**31-1 or res < -2**31:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class Short(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        # [-32768, 32767]
        if res > 2**15-1 or res < -2**15:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class Byte(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        # [-128,127]
        if res > 2**7-1 or res < -2**7:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class NonPositiveInteger(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if res > 0:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class NegativeInteger(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if res >= 0:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class NonNegativeInteger(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if res < 0:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class PositiveInteger(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if res <= 0:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class UnsignedLong(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if not 0 <= res <= 2**64-1:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class UnsignedInt(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if not 0 <= res <= 2**32-1:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class UnsignedShort(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if not 0 <= res <= 2**16-1:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class UnsignedByte(int):
    def __new__(cls, *args, **kwargs):
        res = int.__new__(cls, *args, **kwargs)
        if not 0 <= res <= 2**8-1:
            raise ValueError("{} is out of the allowed range for type {}".format(res, cls.__name__))
        return res


class AnyURI(str):
    # TODO validate values
    pass


class NormalizedString(str):
    def __new__(cls, *args, **kwargs):
        res = str.__new__(cls, *args, **kwargs)
        if ('\r' in res) or ('\n' in res) or ('\t' in res):
            raise ValueError("\\r, \\n and \\t are not allowed in NormalizedStrings")
        return res

    @classmethod
    def from_string(cls, value: str) -> "NormalizedString":
        """
        Make a string a normalized string by simply dropping all carriage return, newline and tab characters.
        """
        return cls(value.translate({0xD: None, 0xA: None, 0x9: None}))


AnyXSDType = Union[
    Duration, DateTime, Date, Time, GYearMonth, GYear, GMonthDay, GMonth, GDay, Boolean, Base64Binary,
    HexBinary, Float, Double, Decimal, Integer, Long, Int, Short, Byte, NonPositiveInteger, NegativeInteger,
    NonNegativeInteger, PositiveInteger, UnsignedLong, UnsignedInt, UnsignedShort, UnsignedByte, AnyURI, String,
    NormalizedString]


XSD_TYPE_NAMES: Dict[Type[AnyXSDType], str] = {k: "xs:" + v for k, v in {
    Duration: "duration",
    DateTime: "dateTime",
    Date: "date",
    Time: "time",
    GYearMonth: "gYearMonth",
    GYear: "gYear",
    GMonthDay: "gMonthDay",
    GMonth: "gMonth",
    GDay: "gDay",
    Boolean: "boolean",
    Base64Binary: "base64Binary",
    HexBinary: "hexBinary",
    Float: "float",
    Double: "double",
    Decimal: "decimal",
    Integer: "integer",
    Long: "long",
    Int: "int",
    Short: "short",
    Byte: "byte",
    NonPositiveInteger: "nonPositiveInteger",
    NegativeInteger: "negativeInteger",
    NonNegativeInteger: "nonNegativeInteger",
    PositiveInteger: "positiveInteger",
    UnsignedLong: "unsignedLong",
    UnsignedShort: "unsignedShort",
    UnsignedInt: "unsignedByte",
    AnyURI: "anyURI",
    String: "string",
    NormalizedString: "normalizedString",
}.items()}
XSD_TYPE_CLASSES: Dict[str, Type[AnyXSDType]] = {v: k for k, v in XSD_TYPE_NAMES.items()}


def trivial_cast(value, type_: Type[AnyXSDType]) -> AnyXSDType:  # workaround. We should be able to use a TypeVar here
    """
    Type-cast a python value into an XSD type, if this is a trivial conversion

    The main purpose of this function is to allow AAS :class:`Properties <basyx.aas.model.submodel.Property>`
    (and similar objects with XSD-type values) to take Python literal values and convert them to their XSD type.
    However, we want to stay strongly typed, so we only allow this type-cast if it is trivial to do, i.e. does not
    change the value's semantics. Examples, where this holds true:

    * int → :class:`~basyx.aas.model.datatypes.Int` (if the value is in the expected range)
    * bytes → :class:`~basyx.aas.model.datatypes.Base64Binary`
    * datetime.date → :class:`~basyx.aas.model.datatypes.Date`

    Yet, it is not allowed to cast float → :class:`basyx.aas.model.datatypes.Int`.

    :param value: The value to cast
    :param type_: Target type to cast into. Must be an XSD type from this module
    """
    if isinstance(value, type_):
        return value
    for baseclass in (int, float, str):
        if isinstance(value, baseclass) and issubclass(type_, baseclass):
            return type_(value)  # type: ignore
    if isinstance(value, (bytes, bytearray)) and issubclass(type_, bytearray):
        return type_(value)  # type: ignore
    if isinstance(value, datetime.date) and issubclass(type_, Date):
        return Date(value.year, value.month, value.day)
    raise TypeError("{} cannot be trivially casted into {}".format(repr(value), type_.__name__))


def xsd_repr(value: AnyXSDType) -> str:
    """
    Serialize an XSD type value into it's lexical representation

    :param value: Any XSD type (from this module)
    :returns: Lexical representation as string
    """
    if isinstance(value, Duration):
        return _serialize_duration(value)
    elif isinstance(value, (DateTime, Time)):
        # TODO fix trailing zeros of seconds fraction (XSD:
        #  "The fractional second string, if present, must not end in '0'")
        return value.isoformat()
    elif isinstance(value, Date):
        return value.isoformat() + _serialize_date_tzinfo(value)
    elif isinstance(value, GYearMonth):
        return "{:02d}-{:02d}".format(value.year, value.month) + _serialize_date_tzinfo(value)
    elif isinstance(value, GYear):
        return "{:04d}".format(value.year) + _serialize_date_tzinfo(value)
    elif isinstance(value, GMonthDay):
        return "--{:02d}-{:02d}".format(value.month, value.day) + _serialize_date_tzinfo(value)
    elif isinstance(value, GDay):
        return "---{:02d}".format(value.day) + _serialize_date_tzinfo(value)
    elif isinstance(value, GMonth):
        return "--{:02d}".format(value.month) + _serialize_date_tzinfo(value)
    elif isinstance(value, Boolean):
        return "true" if value else "false"
    elif isinstance(value, Base64Binary):
        return base64.b64encode(value).decode()
    elif isinstance(value, HexBinary):
        return value.hex()
    elif isinstance(value, str):
        return value
    elif isinstance(value, float):
        return repr(value).translate({0x65: 'E', 0x66: 'F', 0x69: 'I', 0x6e: 'N'})
    else:
        return str(value)


def _serialize_date_tzinfo(date: Union[Date, GYear, GMonth, GDay, GYearMonth, GMonthDay]) -> str:
    if date.tzinfo is not None:
        if not isinstance(date, Date):
            date = date.into_date()
        offset: datetime.timedelta = date.tzinfo.utcoffset(datetime.datetime(date.year, date.month, date.day, 0, 0, 0))
        offset_seconds = (offset.total_seconds() + 3600*12) % (3600*24) - 3600*12
        if offset_seconds // 60 == 0:
            return "Z"
        return "{}{:02.0f}:{:02.0f}".format("+" if offset_seconds >= 0 else "-",
                                            abs(offset_seconds) // 3600,
                                            (abs(offset_seconds) // 60) % 60)
    return ""


def _serialize_duration(value: Duration) -> str:
    value = value.normalized()
    signs = set(val < 0
                for val in (value.years, value.months, value.days, value.hours, value.minutes, value.seconds,
                            value.microseconds)
                if val != 0)
    if len(signs) > 1:
        raise ValueError("Relative Durations with mixed signs are not allowed according to XSD.")
    elif len(signs) == 0:
        return "P0D"

    result = "-" if signs.pop() else ""
    result += "P"
    if value.years:
        result += "{:.0f}Y".format(abs(value.years))
    if value.months:
        result += "{:.0f}M".format(abs(value.months))
    if value.days:
        result += "{:.0f}D".format(abs(value.days))

    time = ""
    if value.hours:
        time += "{:.0f}H".format(abs(value.hours))
    if value.minutes:
        time += "{:.0f}M".format(abs(value.minutes))
    if value.seconds or value.microseconds:
        time += "{:.8g}S".format(decimal.Decimal(abs(value.seconds))
                                 + decimal.Decimal(abs(value.microseconds)) / 1000000)
    if time:
        result += "T" + time
    return result


def from_xsd(value: str, type_: Type[AnyXSDType]) -> AnyXSDType:  # workaround. We should be able to use a TypeVar here
    """
    Parse an XSD type value from its lexical representation

    :param value: Lexical representation
    :param type_: The expected XSD type (from this module). It is required to choose the correct conversion.
    """
    if type_ is Boolean:
        return _parse_xsd_bool(value)
    elif issubclass(type_, (int, float, str)):
        return type_(value)
    elif type_ is decimal.Decimal:
        try:
            return decimal.Decimal(value)
        except decimal.InvalidOperation as e:
            # We cannot use the original exception text here, because the text differs depending on
            # whether the _decimal or _pydecimal module is used. Furthermore, the _decimal doesn't provide
            # a real error message suited for end users, but provides a list of conditions that trigger the exception.
            # See https://github.com/python/cpython/issues/76420
            # Raising our own error message allows us to verify it in the tests.
            raise ValueError(f"Cannot convert '{value}' to Decimal!") from e
    elif type_ is Duration:
        return _parse_xsd_duration(value)
    elif type_ is DateTime:
        return _parse_xsd_datetime(value)
    elif type_ is Date:
        return _parse_xsd_date(value)
    elif type_ is Time:
        return _parse_xsd_time(value)
    elif type_ is Base64Binary:
        return Base64Binary(base64.b64decode(value.encode()))
    elif type_ is HexBinary:
        return HexBinary(bytes.fromhex(value))
    elif type_ is GYear:
        return _parse_xsd_gyear(value)
    elif type_ is GMonth:
        return _parse_xsd_gmonth(value)
    elif type_ is GDay:
        return _parse_xsd_gday(value)
    elif type_ is GYearMonth:
        return _parse_xsd_gyearmonth(value)
    elif type_ is GMonthDay:
        return _parse_xsd_gmonthday(value)
    raise ValueError("{} is not a valid simple built-in XSD type".format(type_.__name__))


DURATION_RE = re.compile(r'^(-?)P(\d+Y)?(\d+M)?(\d+D)?(T(\d+H)?(\d+M)?((\d+)(\.\d+)?S)?)?$')
DATETIME_RE = re.compile(r'^(-?)(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(\.\d+)?([+\-](\d\d):(\d\d)|Z)?$')
TIME_RE = re.compile(r'^(\d\d):(\d\d):(\d\d)(\.\d+)?([+\-](\d\d):(\d\d)|Z)?$')
DATE_RE = re.compile(r'^(-?)(\d\d\d\d)-(\d\d)-(\d\d)([+\-](\d\d):(\d\d)|Z)?$')


def _parse_xsd_duration(value: str) -> Duration:
    match = DURATION_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD duration string")
    res = Duration(years=int(match[2][:-1]) if match[2] else 0,
                   months=int(match[3][:-1]) if match[3] else 0,
                   days=int(match[4][:-1]) if match[4] else 0,
                   hours=int(match[6][:-1]) if match[6] else 0,
                   minutes=int(match[7][:-1]) if match[7] else 0,
                   seconds=int(match[9]) if match[8] else 0,
                   microseconds=int(float(match[10])*1e6) if match[10] else 0)
    if match[1]:
        res = -res
    return res


def _parse_xsd_date_tzinfo(value: str) -> Optional[datetime.tzinfo]:
    if not value:
        return None
    if value == "Z":
        return datetime.timezone.utc
    return datetime.timezone(datetime.timedelta(hours=int(value[1:3]), minutes=int(value[4:6]))
                             * (-1 if value[0] == '-' else 1))


def _parse_xsd_date(value: str) -> Date:
    match = DATE_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD date string")
    if match[1]:
        raise ValueError("Negative Dates are not supported by Python")
    return Date(int(match[2]), int(match[3]), int(match[4]), _parse_xsd_date_tzinfo(match[5]))


def _parse_xsd_datetime(value: str) -> DateTime:
    match = DATETIME_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD datetime string")
    if match[1]:
        raise ValueError("Negative Dates are not supported by Python")
    microseconds = int(float(match[8]) * 1e6) if match[8] else 0
    return DateTime(int(match[2]), int(match[3]), int(match[4]), int(match[5]), int(match[6]), int(match[7]),
                    microseconds, _parse_xsd_date_tzinfo(match[9]))


def _parse_xsd_time(value: str) -> Time:
    match = TIME_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD datetime string")
    microseconds = int(float(match[4]) * 1e6) if match[4] else 0
    return Time(int(match[1]), int(match[2]), int(match[3]), microseconds, _parse_xsd_date_tzinfo(match[5]))


def _parse_xsd_bool(value: str) -> Boolean:
    if value in {"1", "true"}:
        return True
    elif value in {"0", "false"}:
        return False
    else:
        raise ValueError("Invalid literal for XSD bool type")


GYEAR_RE = re.compile(r'^(\d\d\d\d)([+\-]\d\d:\d\d|Z)?$')
GMONTH_RE = re.compile(r'^--(\d\d)([+\-]\d\d:\d\d|Z)?$')
GDAY_RE = re.compile(r'^---(\d\d)([+\-]\d\d:\d\d|Z)?$')
GYEARMONTH_RE = re.compile(r'^(\d\d\d\d)-(\d\d)([+\-]\d\d:\d\d|Z)?$')
GMONTHDAY_RE = re.compile(r'^--(\d\d)-(\d\d)([+\-]\d\d:\d\d|Z)?$')


def _parse_xsd_gyear(value: str) -> GYear:
    match = GYEAR_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD GYear string")
    return GYear(int(match[1]), _parse_xsd_date_tzinfo(match[2]))


def _parse_xsd_gmonth(value: str) -> GMonth:
    match = GMONTH_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD GMonth string")
    return GMonth(int(match[1]), _parse_xsd_date_tzinfo(match[2]))


def _parse_xsd_gday(value: str) -> GDay:
    match = GDAY_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD GDay string")
    return GDay(int(match[1]), _parse_xsd_date_tzinfo(match[2]))


def _parse_xsd_gyearmonth(value: str) -> GYearMonth:
    match = GYEARMONTH_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD GYearMonth string")
    return GYearMonth(int(match[1]), int(match[2]), _parse_xsd_date_tzinfo(match[3]))


def _parse_xsd_gmonthday(value: str) -> GMonthDay:
    match = GMONTHDAY_RE.match(value)
    if not match:
        raise ValueError("Value is not a valid XSD GMonthDay string")
    return GMonthDay(int(match[1]), int(match[2]), _parse_xsd_date_tzinfo(match[3]))
