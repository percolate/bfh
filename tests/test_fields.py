# -*- coding: utf-8 -*-
from unittest import TestCase

import datetime

from bfh import Schema
from bfh.exceptions import Invalid
from bfh.fields import (
    ObjectField,
    IntegerField,
    IsoDateString,
    UnicodeField,
    ArrayField,
    Subschema
)


class TestFieldValidation(TestCase):
    def test_int_validation(self):
        field = IntegerField()

        assert field.validate(1)

        with self.assertRaises(Invalid):
            field.validate("wow")

        with self.assertRaises(Invalid):
            field.validate(1.0)

        with self.assertRaises(Invalid):
            field.validate([])

        with self.assertRaises(Invalid):
            field.validate(None)

    def test_optional_validation(self):
        """Fields are required by default but can be made optional"""
        field = IntegerField(required=False)
        assert field.validate(None)

    def test_unicode_validation(self):
        field = UnicodeField()

        assert field.validate(u'wow ☃')

        assert field.validate('still ok')

        with self.assertRaises(Invalid):
            field.validate(1.0)

        with self.assertRaises(Invalid):
            field.validate(None)

        field = UnicodeField(required=False)

        assert field.validate(u'wow ☃')

        assert field.validate(None)

        with self.assertRaises(Invalid):
            field.validate(1)

        field = UnicodeField(strict=True)

        assert field.validate(u'nice snowman ☃')

        with self.assertRaises(Invalid):
            field.validate('not strict enough')

    def test_array_validation(self):
        field = ArrayField(int)

        assert field.validate([1, 2, 3])

        with self.assertRaises(Invalid):
            field.validate(["a", 1, 1.0])

        with self.assertRaises(Invalid):
            field.validate(None)

        with self.assertRaises(Invalid):
            field.validate({1: "A", 2: "B"})

        with self.assertRaises(Invalid):
            field.validate("hiya")

        field = ArrayField(int, required=False)

        assert field.validate([1, 2, 3])

        assert field.validate(None)

        with self.assertRaises(Invalid):
            field.validate(1)

        class SomeSchema(Schema):
            good = IntegerField()

        field = ArrayField(SomeSchema, required=False)

        assert field.validate([SomeSchema(good=1)])

        assert field.validate([{"good": 1}])

        assert field.validate(None)

        with self.assertRaises(Invalid):
            field.validate([SomeSchema(good="bad")])

        with self.assertRaises(Invalid):
            field.validate([{"good": "bad"}])

        with self.assertRaises(Invalid):
            field.validate([{"wat": "whatever"}])

    def test_object_validation(self):
        field = ObjectField()

        assert field.validate({})

        assert field.validate({"foo": "bar"})

        with self.assertRaises(Invalid):
            field.validate(1)

        with self.assertRaises(Invalid):
            field.validate([])

        with self.assertRaises(Invalid):
            field.validate(None)

        class SomeSchema(Schema):
            inner = IntegerField()

        assert field.validate(SomeSchema(inner=1))

        with self.assertRaises(Invalid):
            field.validate(SomeSchema(inner="wow"))

        field = ObjectField(required=False)

        assert field.validate({"foo": "bar"})

        assert field.validate(None)

    def test_subschema_validation(self):
        class SomeSchema(Schema):
            inner = IntegerField()

        field = Subschema(SomeSchema)

        assert field.validate(SomeSchema(inner=1))

        with self.assertRaises(Invalid):
            field.validate(SomeSchema(inner="wow"))

        with self.assertRaises(Invalid):
            field.validate(SomeSchema(inner=None))

        with self.assertRaises(Invalid):
            field.validate(None)

        with self.assertRaises(Invalid):
            field.validate(SomeSchema())

        with self.assertRaises(Invalid):
            field.validate({})

        field = Subschema(SomeSchema, required=False)

        assert field.validate(SomeSchema(inner=1))

        assert field.validate(None)

        assert field.validate({})

        assert field.validate(SomeSchema())

        assert field.validate(SomeSchema(inner=None))

        with self.assertRaises(Invalid):
            field.validate(SomeSchema(inner="wow"))

    def test_required_within_not_required_validation(self):
        """A required child of an empty optional schema shouldn't invalidate"""
        class MostIn(Schema):
            foo = IntegerField()

        class Inner(Schema):
            maybe = Subschema(MostIn, required=True)

        class Outer(Schema):
            maybe = Subschema(Inner, required=False)

        full = Outer(maybe=Inner(maybe=MostIn(foo=1)))
        assert full.validate()

        oops = Outer(maybe=Inner(maybe=MostIn(foo="A")))
        with self.assertRaises(Invalid):
            oops.validate()

        empty = Outer(maybe=None)
        assert empty.validate()

        inner_empty = Outer(maybe=Inner(maybe=None))
        assert inner_empty.validate()

        innermost = Outer(maybe=Inner(maybe=MostIn(foo=None)))
        assert innermost.validate()

    def test_isodatestring_validation(self):
        field = IsoDateString()

        assert field.validate("2015-10-11T00:00:00")
        assert field.validate("2015-10-11T00:00:00Z")
        assert field.validate("2015-10-11T00:00:00+00:00")

        with self.assertRaises(Invalid):
            field.validate("not a date string")

        with self.assertRaises(Invalid):
            field.validate(1)

        with self.assertRaises(Invalid):
            field.validate(datetime.datetime.now())


class TestFieldSerialization(TestCase):
    """
    Tests serialization for field types.

    N.B. serialization is not validation. In general we should pass invalid
    data through untouched.
    """
    def test_array_serialization(self):
        field = ArrayField(int)

        flat = [1, 2, 3]
        self.assertEqual(flat, field.serialize(flat))

        self.assertEqual(None, field.serialize(None))

        self.assertEqual([], field.serialize([]))

        self.assertEqual("wow", field.serialize("wow"))

        class SomeSchema(Schema):
            wat = IntegerField()

        field = ArrayField(Subschema)
        source = [SomeSchema(wat=1), SomeSchema(wat=2)]
        self.assertEqual([{"wat": 1}, {"wat": 2}], field.serialize(source))
        source = [SomeSchema(), SomeSchema()]
        self.assertEqual([], field.serialize(source))
        self.assertEqual([{"wat": None}, {"wat": None}],
                         field.serialize(source, implicit_nulls=False))

    def test_object_serialization(self):
        field = ObjectField()

        self.assertEqual({}, field.serialize(None))

        self.assertEqual([], field.serialize([]))

        self.assertEqual("wow", field.serialize("wow"))

        source = {"wow": "cool"}
        self.assertEqual(source, field.serialize(source))

        class SomeSchema(Schema):
            great = ArrayField(int)

        source = SomeSchema(great=[1, 2, 3])
        self.assertEqual({"great": [1, 2, 3]}, field.serialize(source))

        source = {"implicit": None}
        self.assertEqual({}, field.serialize(source))
        self.assertEqual(source, field.serialize(source, implicit_nulls=False))

    def test_subschema_serialization(self):
        class SomeSchema(Schema):
            great = ArrayField(int, required=False)

        field = Subschema(SomeSchema)

        self.assertEqual({}, field.serialize(None))

        self.assertEqual([], field.serialize([]))

        self.assertEqual("wow", field.serialize("wow"))

        source = SomeSchema(great=[1, 2, 3])
        self.assertEqual({"great": [1, 2, 3]}, field.serialize(source))
        source = SomeSchema(great=None)
        self.assertEqual({}, field.serialize(source))

        field = Subschema(SomeSchema, required=False)
        source = SomeSchema(great=[1, 2, 3])
        self.assertEqual({"great": [1, 2, 3]}, field.serialize(source))
        source = SomeSchema(great=None)
        self.assertEqual({}, field.serialize(source))
        self.assertEqual({"great": None},
                         field.serialize(source, implicit_nulls=False))

    def test_unicode_serialization(self):
        field = UnicodeField()

        assert field.serialize(u'wow ☃')

        assert field.serialize('still ok')

        assert field.serialize(1.0)

        assert field.serialize(None) is None

        field = UnicodeField(strict=True)

        assert field.serialize(u'nice snowman ☃')

        assert field.serialize('not strict enough')
