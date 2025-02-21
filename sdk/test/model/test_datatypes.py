# Copyright (c) 2025 the Eclipse BaSyx Authors
#
# This program and the accompanying materials are made available under the terms of the MIT License, available in
# the LICENSE file of this project.
#
# SPDX-License-Identifier: MIT
import datetime
import math
import unittest
import copy

import dateutil

from basyx.aas import model


class TestIntTypes(unittest.TestCase):
    def test_parse_int(self) -> None:
        self.assertEqual(5, model.datatypes.from_xsd("5", model.datatypes.Integer))
        self.assertEqual(6, model.datatypes.from_xsd("6", model.datatypes.Byte))
        self.assertEqual(7, model.datatypes.from_xsd("7", model.datatypes.NonNegativeInteger))
        self.assertEqual(8, model.datatypes.from_xsd("8", model.datatypes.Long))
        self.assertEqual(9, model.datatypes.from_xsd("9", model.datatypes.Int))
        self.assertEqual(10, model.datatypes.from_xsd("10", model.datatypes.Short))
        self.assertEqual(-123456789012345678901234567890,
                         model.datatypes.from_xsd("-123456789012345678901234567890", model.datatypes.Integer))
        self.assertEqual(2147483647, model.datatypes.from_xsd("2147483647", model.datatypes.Int))
        self.assertEqual(-2147483648, model.datatypes.from_xsd("-2147483648", model.datatypes.Int))
        self.assertEqual(-32768, model.datatypes.from_xsd("-32768", model.datatypes.Short))
        self.assertEqual(-128, model.datatypes.from_xsd("-128", model.datatypes.Byte))
        self.assertEqual(-9223372036854775808,
                         model.datatypes.from_xsd("-9223372036854775808", model.datatypes.Long))

    def test_serialize_int(self) -> None:
        self.assertEqual("5", model.datatypes.xsd_repr(model.datatypes.Integer(5)))
        self.assertEqual("6", model.datatypes.xsd_repr(model.datatypes.Byte(6)))
        self.assertEqual("7", model.datatypes.xsd_repr(model.datatypes.NonNegativeInteger(7)))
        self.assertEqual("-128", model.datatypes.xsd_repr(model.datatypes.Byte(-128)))

    def test_range_error(self) -> None:
        with self.assertRaises(ValueError) as cm:
            model.datatypes.NonNegativeInteger(-7)
        self.assertEqual("-7 is out of the allowed range for type NonNegativeInteger", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.Byte(128)
        self.assertEqual("128 is out of the allowed range for type Byte", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.UnsignedByte(256)
        self.assertEqual("256 is out of the allowed range for type UnsignedByte", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.UnsignedByte(1000)
        self.assertEqual("1000 is out of the allowed range for type UnsignedByte", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.PositiveInteger(0)
        self.assertEqual("0 is out of the allowed range for type PositiveInteger", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.Int(2147483648)
        self.assertEqual("2147483648 is out of the allowed range for type Int", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.Long(2**63)
        self.assertEqual(str(2**63)+" is out of the allowed range for type Long", str(cm.exception))

    def test_trivial_cast(self) -> None:
        val = model.datatypes.trivial_cast(5, model.datatypes.UnsignedByte)
        self.assertEqual(5, val)
        self.assertIsInstance(val, model.datatypes.UnsignedByte)

        val = model.datatypes.trivial_cast(-7, model.datatypes.Integer)
        self.assertEqual(-7, val)
        self.assertIsInstance(val, model.datatypes.Integer)

        with self.assertRaises(ValueError) as cm:
            model.datatypes.trivial_cast(-7, model.datatypes.PositiveInteger)
        self.assertEqual("-7 is out of the allowed range for type PositiveInteger", str(cm.exception))
        with self.assertRaises(TypeError) as cm_2:
            model.datatypes.trivial_cast(6.7, model.datatypes.Integer)
        self.assertEqual("6.7 cannot be trivially casted into int", str(cm_2.exception))
        with self.assertRaises(TypeError) as cm_2:
            model.datatypes.trivial_cast("17", model.datatypes.Int)
        self.assertEqual("'17' cannot be trivially casted into Int", str(cm_2.exception))


class TestStringTypes(unittest.TestCase):
    def test_normalized_string(self) -> None:
        self.assertEqual("abc", model.datatypes.NormalizedString("abc"))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.NormalizedString("ab\nc")
        self.assertEqual("\\r, \\n and \\t are not allowed in NormalizedStrings", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.NormalizedString("ab\tc")
        self.assertEqual("\\r, \\n and \\t are not allowed in NormalizedStrings", str(cm.exception))
        self.assertEqual("abc", model.datatypes.NormalizedString.from_string("a\r\nb\tc"))

    def test_serialize(self) -> None:
        self.assertEqual("abc", model.datatypes.from_xsd("abc", model.datatypes.String))
        self.assertEqual("abc", model.datatypes.from_xsd("abc", model.datatypes.NormalizedString))
        self.assertEqual("abc", model.datatypes.xsd_repr(model.datatypes.String("abc")))
        self.assertEqual("abc", model.datatypes.xsd_repr(model.datatypes.NormalizedString("abc")))


class TestDateTimeTypes(unittest.TestCase):
    def test_parse_duration(self) -> None:
        # Examples from https://www.w3.org/TR/xmlschema-2/#duration-lexical-repr
        self.assertEqual(dateutil.relativedelta.relativedelta(years=1, months=2, hours=2),
                         model.datatypes.from_xsd("P1Y2MT2H", model.datatypes.Duration))
        self.assertEqual(dateutil.relativedelta.relativedelta(months=1347),
                         model.datatypes.from_xsd("P0Y1347M", model.datatypes.Duration))
        self.assertEqual(dateutil.relativedelta.relativedelta(months=1347),
                         model.datatypes.from_xsd("P0Y1347M0D", model.datatypes.Duration))
        self.assertEqual(dateutil.relativedelta.relativedelta(months=-1347),
                         model.datatypes.from_xsd("-P1347M", model.datatypes.Duration))
        self.assertEqual(dateutil.relativedelta.relativedelta(years=1, months=2, days=3, hours=10, minutes=30),
                         model.datatypes.from_xsd("P1Y2M3DT10H30M", model.datatypes.Duration))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("P-1347M", model.datatypes.Duration)
        self.assertEqual("Value is not a valid XSD duration string", str(cm.exception))

    def test_serialize_duration(self) -> None:
        self.assertEqual("P1Y2MT2H",
                         model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta(years=1, months=2, hours=2)))
        self.assertEqual("P112Y3M",
                         model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta(months=1347)))
        self.assertEqual("-P112Y3M",
                         model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta(months=-1347)))
        self.assertEqual("P1Y2M3DT10H30M",
                         model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta(years=1, months=2, days=3,
                                                                                       hours=10, minutes=30)))
        zero_val = model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta())
        self.assertGreaterEqual(len(zero_val), 3)
        self.assertEqual("P", zero_val[0])
        with self.assertRaises(ValueError) as cm:
            model.datatypes.xsd_repr(dateutil.relativedelta.relativedelta(months=-5, days=3))
        self.assertEqual("Relative Durations with mixed signs are not allowed according to XSD.", str(cm.exception))

    def test_parse_date(self) -> None:
        self.assertEqual(datetime.date(2020, 1, 24), model.datatypes.from_xsd("2020-01-24", model.datatypes.Date))
        self.assertEqual(model.datatypes.Date(2020, 1, 24, datetime.timezone.utc),
                         model.datatypes.from_xsd("2020-01-24Z", model.datatypes.Date))
        self.assertEqual(model.datatypes.Date(2020, 1, 24, datetime.timezone(datetime.timedelta(hours=11, minutes=20))),
                         model.datatypes.from_xsd("2020-01-24+11:20", model.datatypes.Date))
        self.assertEqual(model.datatypes.Date(2020, 1, 24, datetime.timezone(datetime.timedelta(hours=-8))),
                         model.datatypes.from_xsd("2020-01-24-08:00", model.datatypes.Date))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("2020-01-24+11", model.datatypes.Date)
        self.assertEqual("Value is not a valid XSD date string", str(cm.exception))

    def test_serialize_date(self) -> None:
        self.assertEqual("2020-01-24", model.datatypes.xsd_repr(model.datatypes.Date(2020, 1, 24)))
        self.assertEqual("2020-01-24Z", model.datatypes.xsd_repr(
            model.datatypes.Date(2020, 1, 24, datetime.timezone.utc)))
        self.assertEqual("2020-01-24+11:20", model.datatypes.xsd_repr(
            model.datatypes.Date(2020, 1, 24, datetime.timezone(datetime.timedelta(hours=11, minutes=20)))))

    def test_parse_partial_dates(self) -> None:
        self.assertEqual(model.datatypes.GYear(2019),
                         model.datatypes.from_xsd("2019", model.datatypes.GYear))
        self.assertEqual(model.datatypes.GMonth(7),
                         model.datatypes.from_xsd("--07", model.datatypes.GMonth))
        self.assertEqual(model.datatypes.GYearMonth(2020, 5),
                         model.datatypes.from_xsd("2020-05", model.datatypes.GYearMonth))
        self.assertEqual(model.datatypes.GMonthDay(12, 6),
                         model.datatypes.from_xsd("--12-06", model.datatypes.GMonthDay))
        self.assertEqual(model.datatypes.GDay(23),
                         model.datatypes.from_xsd("---23", model.datatypes.GDay))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("--23", model.datatypes.GDay)
        self.assertEqual("Value is not a valid XSD GDay string", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("---23", model.datatypes.GMonth)
        self.assertEqual("Value is not a valid XSD GMonth string", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("10", model.datatypes.GYear)
        self.assertEqual("Value is not a valid XSD GYear string", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("25-10", model.datatypes.GMonthDay)
        self.assertEqual("Value is not a valid XSD GMonthDay string", str(cm.exception))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("10-10", model.datatypes.GYearMonth)
        self.assertEqual("Value is not a valid XSD GYearMonth string", str(cm.exception))

    def test_copy_date(self) -> None:
        date = model.datatypes.Date(2020, 1, 24)
        date_copy_shallow = copy.copy(date)
        self.assertEqual(date, date_copy_shallow)
        date_copy_deep = copy.deepcopy(date)
        self.assertEqual(date, date_copy_deep)

    def test_serialize_partial_dates(self) -> None:
        self.assertEqual("2019", model.datatypes.xsd_repr(model.datatypes.GYear(2019)))
        self.assertEqual("2019Z", model.datatypes.xsd_repr(model.datatypes.GYear(2019, datetime.timezone.utc)))
        self.assertEqual("--07", model.datatypes.xsd_repr(model.datatypes.GMonth(7)))
        self.assertEqual("2020-05", model.datatypes.xsd_repr(model.datatypes.GYearMonth(2020, 5)))
        self.assertEqual("2020-05-05:15", model.datatypes.xsd_repr(
            model.datatypes.GYearMonth(2020, 5, datetime.timezone(datetime.timedelta(hours=-5, minutes=-15)))))
        self.assertEqual("--12-06", model.datatypes.xsd_repr(model.datatypes.GMonthDay(12, 6)))
        self.assertEqual("--12-06+07:00", model.datatypes.xsd_repr(
            model.datatypes.GMonthDay(12, 6, datetime.timezone(datetime.timedelta(hours=7)))))
        self.assertEqual("---23", model.datatypes.xsd_repr(model.datatypes.GDay(23)))

    def test_parse_datetime(self) -> None:
        self.assertEqual(datetime.datetime(2020, 1, 24, 15, 25, 17),
                         model.datatypes.from_xsd("2020-01-24T15:25:17", model.datatypes.DateTime))
        self.assertEqual(datetime.datetime(2020, 1, 24, 15, 25, 17, tzinfo=datetime.timezone.utc),
                         model.datatypes.from_xsd("2020-01-24T15:25:17Z", model.datatypes.DateTime))
        self.assertEqual(datetime.datetime(2020, 1, 24, 15, 25, 17,
                                           tzinfo=datetime.timezone(datetime.timedelta(hours=1))),
                         model.datatypes.from_xsd("2020-01-24T15:25:17+01:00", model.datatypes.DateTime))
        self.assertEqual(datetime.datetime(2020, 1, 24, 15, 25, 17,
                                           tzinfo=datetime.timezone(datetime.timedelta(minutes=-20))),
                         model.datatypes.from_xsd("2020-01-24T15:25:17-00:20", model.datatypes.DateTime))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("--2020-01-24T15:25:17-00:20", model.datatypes.DateTime)
        self.assertEqual("Value is not a valid XSD datetime string", str(cm.exception))

    def test_serialize_datetime(self) -> None:
        self.assertEqual("2020-01-24T15:25:17",
                         model.datatypes.xsd_repr(model.datatypes.DateTime(2020, 1, 24, 15, 25, 17)))
        self.assertEqual("2020-01-24T15:25:17+00:00",
                         model.datatypes.xsd_repr(
                             model.datatypes.DateTime(2020, 1, 24, 15, 25, 17, tzinfo=datetime.timezone.utc)))
        self.assertEqual("2020-01-24T15:25:17+01:00",
                         model.datatypes.xsd_repr(
                             model.datatypes.DateTime(2020, 1, 24, 15, 25, 17,
                                                      tzinfo=datetime.timezone(datetime.timedelta(hours=1)))))
        self.assertEqual("2020-01-24T15:25:17-00:20",
                         model.datatypes.xsd_repr(
                             model.datatypes.DateTime(2020, 1, 24, 15, 25, 17,
                                                      tzinfo=datetime.timezone(datetime.timedelta(minutes=-20)))))

    def test_parse_time(self) -> None:
        self.assertEqual(datetime.time(15, 25, 17),
                         model.datatypes.from_xsd("15:25:17", model.datatypes.Time))
        self.assertEqual(datetime.time(15, 25, 17, tzinfo=datetime.timezone.utc),
                         model.datatypes.from_xsd("15:25:17Z", model.datatypes.Time))
        self.assertEqual(datetime.time(15, 25, 17, 250000, tzinfo=datetime.timezone(datetime.timedelta(hours=1))),
                         model.datatypes.from_xsd("15:25:17.25+01:00", model.datatypes.Time))
        self.assertEqual(datetime.time(15, 25, 17, tzinfo=datetime.timezone(datetime.timedelta(minutes=-20))),
                         model.datatypes.from_xsd("15:25:17-00:20", model.datatypes.Time))

    def test_serialize_time(self) -> None:
        self.assertEqual("15:25:17", model.datatypes.xsd_repr(datetime.time(15, 25, 17)))
        self.assertEqual("15:25:17+00:00", model.datatypes.xsd_repr(
            datetime.time(15, 25, 17, tzinfo=datetime.timezone.utc)))
        self.assertEqual("15:25:17.250000+01:00", model.datatypes.xsd_repr(
            datetime.time(15, 25, 17, 250000, tzinfo=datetime.timezone(datetime.timedelta(hours=1)))))

    def test_trivial_cast(self) -> None:
        val = model.datatypes.trivial_cast(datetime.date(2017, 11, 13), model.datatypes.Date)
        self.assertEqual(model.datatypes.Date(2017, 11, 13), val)
        self.assertIsInstance(val, model.datatypes.Date)
        with self.assertRaises(TypeError) as cm:
            model.datatypes.trivial_cast("2017-25-13", model.datatypes.Date)
        self.assertEqual("'2017-25-13' cannot be trivially casted into Date", str(cm.exception))


class TestBoolType(unittest.TestCase):
    def test_parse_bool(self) -> None:
        self.assertEqual(True, model.datatypes.from_xsd("true", model.datatypes.Boolean))
        self.assertEqual(True, model.datatypes.from_xsd("1", model.datatypes.Boolean))
        self.assertEqual(False, model.datatypes.from_xsd("false", model.datatypes.Boolean))
        self.assertEqual(False, model.datatypes.from_xsd("0", model.datatypes.Boolean))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("TRUE", model.datatypes.Boolean)
        self.assertEqual("Invalid literal for XSD bool type", str(cm.exception))

    def test_serialize_bool(self) -> None:
        self.assertEqual("true", model.datatypes.xsd_repr(True))
        self.assertEqual("false", model.datatypes.xsd_repr(False))


class TestBinaryTypes(unittest.TestCase):
    def test_base64(self) -> None:
        self.assertEqual(b"abc\0def", model.datatypes.from_xsd("YWJjAGRlZg==", model.datatypes.Base64Binary))
        self.assertEqual("YWJjAGRlZg==", model.datatypes.xsd_repr(model.datatypes.Base64Binary(b"abc\0def")))
        val = model.datatypes.trivial_cast(b"abc\0def", model.datatypes.Base64Binary)
        self.assertEqual(model.datatypes.Base64Binary(b"abc\0def"), val)
        self.assertIsInstance(val, model.datatypes.Base64Binary)

    def test_hex(self) -> None:
        self.assertEqual(b"abc\0def", model.datatypes.from_xsd("61626300646566", model.datatypes.HexBinary))
        self.assertEqual("61626300646566", model.datatypes.xsd_repr(model.datatypes.HexBinary(b"abc\0def")))
        val = model.datatypes.trivial_cast(b"abc\0def", model.datatypes.HexBinary)
        self.assertEqual(model.datatypes.HexBinary(b"abc\0def"), val)
        self.assertIsInstance(val, model.datatypes.HexBinary)


class TestFloatType(unittest.TestCase):
    def test_float(self) -> None:
        self.assertEqual(5.1, model.datatypes.from_xsd("5.1", model.datatypes.Double))
        self.assertEqual(-7.0, model.datatypes.from_xsd("-7", model.datatypes.Double))
        self.assertEqual(5300, model.datatypes.from_xsd("5.3E3", model.datatypes.Double))
        self.assertTrue(math.isnan(model.datatypes.from_xsd("NaN", model.datatypes.Double)))  # type: ignore
        self.assertEqual(float("inf"), model.datatypes.from_xsd("INF", model.datatypes.Double))
        self.assertEqual(float("-inf"), model.datatypes.from_xsd("-INF", model.datatypes.Double))

        self.assertEqual("5.1", model.datatypes.xsd_repr(5.1))
        self.assertEqual("-7.0", model.datatypes.xsd_repr(-7.0))
        self.assertEqual("5.3E+18", model.datatypes.xsd_repr(5300000000000000000.0))
        self.assertEqual("NaN", model.datatypes.xsd_repr(float("nan")))
        self.assertEqual("INF", model.datatypes.xsd_repr(float("inf")))
        self.assertEqual("-INF", model.datatypes.xsd_repr(float("-inf")))


class TestDecimalType(unittest.TestCase):
    def test_parse_decimal(self) -> None:
        self.assertEqual(model.datatypes.Decimal("0.1"), model.datatypes.from_xsd("0.1", model.datatypes.Decimal))
        with self.assertRaises(ValueError) as cm:
            model.datatypes.from_xsd("foo", model.datatypes.Decimal)
        self.assertEqual("Cannot convert 'foo' to Decimal!", str(cm.exception))

    def test_serialize_decimal(self) -> None:
        self.assertEqual("0.1", model.datatypes.xsd_repr(model.datatypes.Decimal("0.1")))
