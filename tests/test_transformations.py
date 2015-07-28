import datetime
from unittest import TestCase

from bfh import Schema, Mapping
from bfh.exceptions import Missing
from bfh.fields import (
    ArrayField,
    Subschema,
    IntegerField,
    UnicodeField,
)
from bfh.transformations import (
    All,
    Bool,
    Const,
    Concat,
    Do,
    Get,
    Int,
    Many,
    ManySubmap,
    Num,
    Str,
    ParseDate,
    Submapping,
    utc,
)

try:
    string_type = unicode
except NameError:
    string_type = str


class TestAll(TestCase):
    def test_all_is_all_by_default(self):
        class Myschema(Schema):
            wow = IntegerField()

        extras = {"wow": 1, "other": 2}
        m = Myschema(extras)
        allof = All()(m)
        self.assertEqual(extras, allof)

        # without a schema, we obvs have to pass everything
        schemaless = All(strict=True)(extras)
        self.assertEqual(extras, schemaless)

        # the 'strict' flag means extra kwargs outside the schema
        # get filtered out.
        filtered = All(strict=True)(m)
        self.assertEqual({"wow": 1}, filtered)


class TestGet(TestCase):
    def test_can_get_from_dict(self):
        my_dict = {"path": "goal"}
        result = Get("path")(my_dict)
        self.assertEqual(result, "goal")

    def test_can_nest(self):
        my_dict = {"path": {"subpath": "goal"}}
        result = Get("path", "subpath")(my_dict)
        self.assertEqual(result, "goal")

    def test_can_nest_deeply(self):
        my_dict = {"path": {"deep": {"deeper": {"deepest": "goal"}}}}
        result = Get("path", "deep", "deeper", "deepest")(my_dict)
        self.assertEqual(result, "goal")

    def test_can_get_from_obj(self):
        class MyObj(object):
            path = "goal"
        result = Get("path")(MyObj())
        self.assertEqual(result, "goal")

    def test_default_is_not_required(self):
        my_dict = {"path": "goal"}
        result = Get("else")(my_dict)
        self.assertIsNone(result)

    def test_mandatory_raises(self):
        my_dict = {"path": "goal"}
        with self.assertRaises(Missing):
            Get("other", required=True)(my_dict)


class TestCoerce(TestCase):
    def test_can_coerce_int(self):
        my_int = 1
        result = Int(my_int)()
        self.assertEqual(my_int, result)
        result = Int(str(my_int))()
        self.assertEqual(my_int, result)
        result = Int(string_type(my_int))()
        self.assertEqual(my_int, result)
        result = Int(float(my_int))()
        self.assertEqual(my_int, result)

    def test_can_coerce_num(self):
        my_float = 1.01
        result = Num(my_float)()
        self.assertEqual(my_float, result)
        result = Num(int(my_float))()
        self.assertEqual(1.0, result)
        result = Num(string_type(my_float))()
        self.assertEqual(my_float, result)

    def test_can_coerce_unicode(self):
        my_str = u"1"
        result = Str(my_str)()
        self.assertEqual(my_str, result)
        result = Str(int(my_str))()
        self.assertEqual(my_str, result)
        result = Str(float(my_str))()
        self.assertEqual(u"1.0", result)

    def test_can_coerce_bool(self):
        result = Bool(True)()
        self.assertIs(True, result)
        result = Bool(1)()
        self.assertIs(True, result)
        result = Bool("wow")()
        self.assertIs(True, result)
        result = Bool(0)()
        self.assertIs(False, result)
        result = Bool(None)()
        self.assertIs(None, result)

    def test_can_nest_coercion(self):
        my_int = 1
        nested = Str(Bool(Num(my_int)))
        result = nested()
        self.assertEqual(result, u"True")


class TestConcat(TestCase):
    def test_can_concat(self):
        first = "one"
        second = "two"
        result = Concat(first, second)()
        self.assertEqual(first + second, result)

        third = "three"
        result = Concat(first, second, third)()
        self.assertEqual(first + second + third, result)

    def test_can_nest_concat(self):
        first = "one"
        second = "two"
        third = "three"
        result = Concat(first, Concat(second, third))()
        self.assertEqual(first + second + third, result)

    def test_none_behavior(self):
        result = Concat(None, "alone")()
        self.assertEqual("alone", result)

        concatter = Concat(None, "alone", strict=True)
        with self.assertRaises(TypeError):
            concatter()


class TestDo(TestCase):
    def test_can_do(self):
        start = "wow"
        transform = lambda a: a.upper()
        result = Do(transform, start)()
        self.assertEqual("WOW", result)

    def test_multiple_args(self):
        transform = lambda a, b, c: a + b + c
        result = Do(transform, 1, 2, 3)()
        self.assertEqual(6, result)


class TestMixedTransformations(TestCase):
    def test_can_mix_transformations(self):
        original = {"foo": 1, "bar": 2}
        concat_getter = Concat(Str(Get("foo")), ":", Str(Get("bar")))
        result = concat_getter(original)
        expected = u"1:2"
        self.assertEqual(expected, result)

        int_concatter = Int(Concat("1", Str(Get("bar")), "3"))
        result = int_concatter(original)
        self.assertEqual(123, result)


class TestParseDate(TestCase):
    def test_can_parse_timestamp(self):
        my_birthday = 397994400
        result = ParseDate(my_birthday)()
        self.assertEqual(datetime.datetime(1982, 8, 12, 10, tzinfo=utc),
                         result)

    def test_can_parse_string(self):
        my_birthdays = [
            u'1982-08-12T10:00:00',
            u'1982-08-12T10:00:00Z',
            u'1982-08-12T06:00:00-04:00',
            "Fri Aug 12 10:00:00 +0000 1982",
            "Friday, August 12, 1982, 10AM UTC"
        ]

        for birthday in my_birthdays:
            result = ParseDate(birthday)()
            self.assertEqual(datetime.datetime(1982, 8, 12, 10, tzinfo=utc),
                             result)


class TestSubmapping(TestCase):
    def test_can_pass_all_to_submap(self):
        source = {
            "flat": 1,
            "nice": 2
        }

        class Source(Schema):
            flat = IntegerField()
            nice = IntegerField()

        class TargetInner(Schema):
            goal = IntegerField()

        class Target(Schema):
            inner = Subschema(TargetInner)

        class Inner(Mapping):
            goal = Get("flat")

        class Outer(Mapping):
            inner = Submapping(Inner, All())

        transformed = Outer().apply(source).serialize()
        self.assertEqual({"inner": {"goal": 1}}, transformed)

        class OuterWithSourceTarget(Outer):
            source_schema = Source
            target_schema = Target

        transformed = OuterWithSourceTarget().apply(source).serialize()
        self.assertEqual({"inner": {"goal": 1}}, transformed)

    def test_can_pass_part_to_submap(self):
        source = {
            "nested": {
                "okay": 3
            }
        }

        class Inner(Mapping):
            goal = Get("okay")

        class Outer(Mapping):
            inner = Submapping(Inner, Get("nested"))

        transformed = Outer().apply(source).serialize()
        self.assertEqual({"inner": {"goal": 3}}, transformed)


class TestIdempotence(TestCase):
    def test_idempotent(self):
        """Stateful is hateful"""
        class Hm(Mapping):
            wow = Int(Get('wow'), required=False)

        first = {"wow": 1}
        second = {}
        third = {"wow": 3}
        result1 = Hm().apply(first).serialize()
        result2 = Hm().apply(second).serialize()
        result3 = Hm().apply(third).serialize()

        assert result1 == first
        assert result2 == second
        assert result3 == third


class TestMany(TestCase):
    def test_simple_many(self):
        class Source(Schema):
            together = ArrayField(IntegerField())
            sep_1 = IntegerField()
            sep_2 = IntegerField()

        class MyMap(Mapping):
            source_schema = Source

            numbers = Many(Int, Get('together'))
            more_numbers = Many(Int, Get('sep_1'), Get('sep_2'), Const(6))

        source = {
            "together": [1, 2, 3],
            "sep_1": 4,
            "sep_2": 5
        }

        transformed = MyMap().apply(source).serialize()
        self.assertEqual(transformed['numbers'], [1, 2, 3])
        self.assertEqual(transformed['more_numbers'], [4, 5, 6])

        class Simpler(Mapping):
            numbers = Many(Int, Get('wow'))

        source = {"wow": []}
        expected = {}
        transformed = Simpler().apply(source).serialize()
        self.assertEqual(expected, transformed)

        source = {"wow": None}
        expected = {}
        transformed = Simpler().apply(source).serialize()
        self.assertEqual(expected, transformed)

    def test_many_submap(self):
        class Inner(Schema):
            wow = UnicodeField()

        class Source(Schema):
            items = ArrayField(Subschema(Inner))

        class Sub(Mapping):
            inner = Get('wow')

        class MyMap(Mapping):
            numbers = ManySubmap(Sub, Get('items'))

        source = {
            "items": [
                {"wow": "one"},
                {"wow": "two"}
            ]
        }

        transformed = MyMap().apply(source).serialize()
        expected = {
            "numbers": [
                {"inner": "one"},
                {"inner": "two"}
            ]
        }
        self.assertEqual(expected, transformed)

        class WithConst(MyMap):
            const = Const(1)

        source = {"items": []}
        expected = {"const": 1}
        transformed = WithConst().apply(source).serialize()
        self.assertEqual(expected, transformed)

        class Deep(Mapping):
            nested = ManySubmap(Sub, Get("one", "two"))

        source = {
            "one": {
                "two": []
            }
        }
        expected = {}
        transformed = Deep().apply(source).serialize()
        self.assertEqual(expected, transformed)

        class HasNone(Mapping):
            inner = ManySubmap(Sub, Const(None))

        transformed = HasNone().apply({}).serialize()
        self.assertEqual({}, transformed)
