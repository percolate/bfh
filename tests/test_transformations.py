import datetime
from unittest import TestCase

from bfh import Schema, Mapping, GenericSchema
from bfh.exceptions import Missing
from bfh.fields import (
    ArrayField,
    IntegerField,
    Subschema,
    UnicodeField,
    ObjectField,
)
from bfh.transformations import (
    All,
    Bool,
    Chain,
    Const,
    Concat,
    DateToIsoString,
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

    @classmethod
    def setUpClass(cls):
        cls.basic_data = {
            'content': 'some text',
            'id': 98749832,
            'user': {
                'name': 'Travis',
                'profile_img': 'tada.jpg'
            }
        }
        cls.non_strict_output = {
            'd': None,
            'user_name': 'Travis',
            'object': {
                'content': 'some text',
                'id': 98749832,
                'user': {
                    'name': 'Travis',
                    'profile_img': 'tada.jpg'
                }
            }
        }
        cls.strict_output = {
            'd': None,
            'user_name': 'Travis',
            'object': {
                'id': 98749832,
                'user': {
                    'name': 'Travis',
                }
            }
        }

    def test_all_is_all_by_default(self):
        class Myschema(Schema):
            wow = IntegerField()

        extras = {"wow": 1, "other": 2}
        m = Myschema(extras)

        # by default extra keys are passed through
        allof = All()(m)
        self.assertEqual(extras, allof.serialize())

        # without a schema, we obvs have to pass everything
        schemaless = All(strict=True)(extras)
        self.assertEqual(extras, schemaless)

        # the 'strict' flag means extra kwargs outside the schema
        # get filtered out.
        filtered = All(strict=True)(m)
        self.assertEqual({"wow": 1}, filtered.serialize())

    def test_no_bad_implementation(self):
        """Don't leak state"""
        class Myschema(Schema):
            wow = IntegerField()

        first = {"wow": 1, "other": 2}
        m = Myschema(first)
        m2 = Myschema()

        self.assertEqual(first, All()(m).serialize())
        self.assertEqual({'wow': None}, All()(m2).serialize(implicit_nulls=False))

    def test_all_passes_dict(self):
        source = {"foo": "bar", "wow": None}
        allof = All()(source)
        self.assertEqual(source, allof)

    def test_all_passes_any_object(self):
        class Some(object):
            foo = "bar"
            wow = None

        instance = Some()
        allof = All()(instance)
        self.assertEqual(allof, instance)

    def test_all_passes_nullish(self):
        class Myschema(Schema):
            maybe = ArrayField()

        instance = Myschema(maybe=[])
        allof = All(strict=True)(instance)
        self.assertEqual(allof.maybe, [])

    def test_all_nonstrict_mutation(self):
        """
        If schema instance is mutated, the output of All should reflect it.

        """
        class MySchema(Schema):
            wow = IntegerField(required=False)

        instance = MySchema(random=2)
        instance.wow = 1
        allof = All(strict=False)(instance)
        self.assertEqual({"wow": 1, "random": 2},
                         allof.serialize())

        # strict on the other hand...
        instance = MySchema(wow=1, random=2)
        instance.wow = 2
        allof = All(strict=True)(instance)
        self.assertEqual({"wow": 2}, allof.serialize())

    def test_all_on_generic_schema(self):
        """
        All should work with GenericSchema()

        """
        class AllLax(Mapping):
            obj = All(strict=False)

        class AllStrict(Mapping):
            obj = All(strict=True)

        source = GenericSchema(**{"target": 1})

        for mapping in (AllLax, AllStrict):
            result = mapping().apply(source).serialize()
            expected = {"obj": {"target": 1}}
            self.assertEqual(expected, result)

    def test_all_transformation_strict(self):
        class User(Schema):
            name = UnicodeField()

        class Message(Schema):
            id = IntegerField()
            user = Subschema(User)

        class Transformed(Schema):
            d = UnicodeField(required=False)
            user_name = UnicodeField()
            object = ObjectField()

        class SomeNonStrictMapping(Mapping):
            source_schema = Message
            target_schema = Transformed

            user_name = Get('user', 'name')
            object = All(strict=False)

        class SomeStrictMapping(Mapping):
            source_schema = Message
            target_schema = Transformed

            user_name = Get('user', 'name')
            object = All(strict=True)

        non_strict = SomeNonStrictMapping().apply(self.basic_data).serialize()
        strict = SomeStrictMapping().apply(self.basic_data).serialize()

        self.assertDictEqual(self.non_strict_output, non_strict)
        self.assertDictEqual(self.strict_output, strict)


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


class TestChain(TestCase):
    def test_can_chain_lists(self):
        list_one = [1, 2]
        list_two = [3, 4, 5]
        list_three = [6, 7]
        result = Chain(list_one, list_two, list_three)()
        self.assertEqual(result, [1, 2, 3, 4, 5, 6, 7])

    def test_can_chain_tuples(self):
        tuple_one = (1, 2)
        tuple_two = (3, 4)
        tuple_three = (5, 6)
        result = Chain(tuple_one, tuple_two, tuple_three)()
        self.assertEqual([1, 2, 3, 4, 5, 6], result)

    def test_can_chain_lists_and_tuples(self):
        list_one = [1, 2, 3]
        tuple_one = (4, 5)
        tuple_two = (6, 7)
        result = Chain(list_one, tuple_one, tuple_two)()
        self.assertEqual([1, 2, 3, 4, 5, 6, 7], result)

    def test_retains_nesting(self):
        list_one = [1, 2, 3]
        list_two = [4, [5]]
        result = Chain(list_one, list_two)()
        self.assertEqual([1, 2, 3, 4, [5]], result)


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


class TestIsoFormatDate(TestCase):
    def test_can_iso_format(self):
        my_birthday = datetime.datetime(1982, 8, 12, 10, tzinfo=utc)
        result = DateToIsoString(my_birthday)()
        self.assertEqual(u'1982-08-12T10:00:00+00:00', result)

    def test_raises_valueerror_on_bad_arg(self):
        with self.assertRaises(ValueError):
            DateToIsoString(1)()

    def test_raises_valueerror_on_no_arg(self):
        with self.assertRaises(ValueError):
            DateToIsoString()()


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

    def test_source_target_schema(self):
        source = {
            "nested": {
                "okay": 3
            }
        }

        class InnerSource(Schema):
            okay = IntegerField()

        class InnerTarget(Schema):
            goal = IntegerField()

        class Inner(Mapping):
            source_schema = InnerSource
            target_schema = InnerTarget

            goal = Get("okay")

        class OuterSource(Schema):
            nested = Subschema(InnerSource)

        class OuterTarget(Schema):
            inner = Subschema(InnerTarget)

        class Outer(Mapping):
            source_schema = OuterSource
            target_schema = OuterTarget

            inner = Submapping(Inner, Get("nested"))

        transformed = Outer().apply(source).serialize()
        self.assertEqual({"inner": {"goal": 3}}, transformed)

    def test_submap_handles_bad_input_well(self):
        """Submapping should handle nullish inputs well"""

        # With explicit source and target schemas
        class SourceSub(Schema):
            something = IntegerField(required=False)

        class Source(Schema):
            inner = Subschema(SourceSub, required=False)

        class TargetSub(Schema):
            wow = IntegerField(required=False)

        class Target(Schema):
            inner = Subschema(TargetSub, required=False)

        class Inner(Mapping):
            source_schema = SourceSub
            target_schema = TargetSub

            wow = Get('something')

        class Outer(Mapping):
            source_schema = Source
            target_schema = Target

            inner = Submapping(Inner, Get("inner"))

        # With implicit source and target schemas
        class InnerNoschema(Mapping):
            wow = Get('something')

        class OuterNoschema(Mapping):
            inner = Submapping(InnerNoschema, Get("inner"))

        source_good = {
            "inner": {"something": 1}
        }
        self.assertEqual({"inner": {"wow": 1}},
                         Outer().apply(source_good).serialize())
        self.assertEqual({"inner": {"wow": 1}},
                         OuterNoschema().apply(source_good).serialize())

        empties = [
            {"inner": {}},
            {"inner": None},
            {},
            None,
        ]
        for source in empties:
            self.assertEqual({}, Outer().apply(source).serialize(implicit_nulls=True))
            self.assertEqual({}, OuterNoschema().apply(source).serialize(implicit_nulls=True))


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
        assert result2 == {"wow": None}
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
        transformed = Simpler().apply(source).serialize(implicit_nulls=True)
        self.assertEqual(expected, transformed)

        source = {"wow": None}
        expected = {}
        transformed = Simpler().apply(source).serialize(implicit_nulls=True)
        self.assertEqual(expected, transformed)

    def test_many_submap(self):

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
        transformed = WithConst().apply(source).serialize(implicit_nulls=True)
        self.assertEqual(expected, transformed)

        class Deep(Mapping):
            nested = ManySubmap(Sub, Get("one", "two"))

        source = {
            "one": {
                "two": []
            }
        }
        expected = {}
        transformed = Deep().apply(source).serialize(implicit_nulls=True)
        self.assertEqual(expected, transformed)

        class HasNone(Mapping):
            inner = ManySubmap(Sub, Const(None))

        transformed = HasNone().apply({}).serialize(implicit_nulls=True)
        self.assertEqual({}, transformed)

