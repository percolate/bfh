# -*- coding: utf-8 -*-
from unittest import TestCase

import datetime

import six

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
        fields = [
            IntegerField(required=False),
            UnicodeField(required=False),
            ObjectField(required=False),
            ArrayField(required=False),
            IsoDateString(required=False),
            # subschema tested elsewhere...
        ]
        for field in fields:
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

        if six.PY2:
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


class TestDefaultValuesForField(TestCase):

    def set_up_schema(self, default):
        class FirstSchema(Schema):
            foo = UnicodeField(required=False, default=default)
        return FirstSchema

    def test_default_interface(self):

        def test_callable():
            return {"wow": 1}

        schema = self.set_up_schema(test_callable)

        wow = schema()
        self.assertEqual(wow.foo, {"wow": 1})

        wow1 = schema(foo={"zip": "pow"})
        self.assertEqual(wow1.foo, {"zip": "pow"})

        wow1.foo = None
        self.assertEqual(wow1.foo, {"wow": 1})

        wow2 = schema(foo=None)
        self.assertEqual(wow2.foo, {"wow": 1})

        my1 = schema()
        my2 = schema()

        my1.foo["wow"] = 2

        self.assertEqual(my2.foo, {"wow": 1})
        self.assertEqual(my1.foo, {"wow": 2})

    def test_callable_as_default(self):

        def test_callable():
            return "testing"

        first_schema = self.set_up_schema(test_callable)
        source = first_schema()
        self.assertEqual({"foo": "testing"}, source.serialize())

        def test_false_callable():
            return False

        second_schema = self.set_up_schema(test_false_callable)
        second_source = second_schema()
        self.assertEqual({"foo": False}, second_source.serialize())


class TestSubSchemaCoercion(TestCase):
    def test_explicit_array_coercion(self):
        class Inner(Schema):
            foo = UnicodeField()

        class Outer(Schema):
            many = ArrayField(Inner)

        my_outer = Outer(many=[{"foo": "bar"}])
        self.assertIsInstance(my_outer.many[0], Inner)

    def test_subschema_coercion(self):
        class Inner(Schema):
            foo = UnicodeField()

        class Outer(Schema):
            inner = Subschema(Inner)

        my_outer = Outer(inner={"foo": "bar"})
        self.assertIsInstance(my_outer.inner, Inner)


class TestNoneSafe(TestCase):
    """
    When a field is not required, it should accept None as a value.

    ... and even when it is a required, it should accept None without an error.
    """
    def test_array_none_safe(self):
        class Sub(Schema):
            foo = UnicodeField()

        class My(Schema):
            stuff = ArrayField(Sub, required=False)

        # these may or may not be valid, but should not error on init
        assert My(stuff=[{"foo": "bar"}])
        assert My(stuff=[Sub(foo="bar")])
        assert My(stuff=[1, 2, 3])
        assert My(stuff=[])
        assert My()
        assert My(stuff=None)
