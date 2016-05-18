from unittest import TestCase

import math

from bfh import Schema, Mapping, GenericSchema
from bfh.exceptions import Invalid
from bfh.fields import (
    ArrayField,
    IntegerField,
    NumberField,
    Subschema,
    UnicodeField
)
from bfh.transformations import (
    Const,
    Concat,
    Do,
    Get,
    Int,
    Str,
)


class Schema1(Schema):
    my_str = UnicodeField()
    my_int = IntegerField()
    another_str = UnicodeField()


class DefaultsSchema(Schema):
    not_defaulted = UnicodeField()
    defaulted = UnicodeField(default="testing")


class Schema2(Schema):
    peas = UnicodeField()
    carrots = IntegerField()
    beans = IntegerField()


class Person(Schema):
    first_name = UnicodeField()
    last_name = UnicodeField()


class Ship(Schema):
    name = UnicodeField()
    captain = Subschema(Person)


class Conversation(Schema):
    numbers = ArrayField(IntegerField())
    conversants = ArrayField(Subschema(Person))


class TestSchemas(TestCase):
    def test_can_make_empty_schema(self):
        s = Schema1()
        assert hasattr(s, 'my_str')
        assert hasattr(s, 'my_int')
        assert hasattr(s, 'another_str')
        assert s.my_str is None
        assert s.my_int is None
        assert s.another_str is None

    def test_can_assign_and_retrieve(self):
        s = Schema1()
        some_str = u'wow'
        some_int = 3
        another_str = u'ok'
        s.my_str = some_str
        s.my_int = some_int
        s.another_str = another_str
        assert s.my_str == some_str
        assert s.my_int == some_int
        assert s.another_str == another_str

    def test_can_initialize_names(self):
        some_str = u'woof'
        some_int = 9
        another_str = u'meow'
        s = Schema1(
            my_str=some_str,
            my_int=some_int,
            another_str=another_str
        )
        assert s.my_str == some_str
        assert s.my_int == some_int
        assert s.another_str == another_str

    def test_can_initialize_with_dict(self):
        my_dict = {
            "my_str": u"haha",
            "my_int": 1212,
            "another_str": "okok",
        }
        s = Schema1(my_dict)
        assert s.serialize() == my_dict

    def test_can_nest_subschema(self):
        s = Ship()
        shipname = "Titanic"
        firstname = "Edward"
        lastname = "Smith"
        s.name = shipname
        s.captain.first_name = firstname
        s.captain.last_name = lastname
        assert hasattr(s, 'name')
        assert hasattr(s, 'captain')
        assert s.name == shipname
        assert s.captain.first_name == firstname
        assert s.captain.last_name == lastname

    def test_can_initialize_subschema(self):
        shipname = "Lollipop"
        firstname = "James"
        lastname = "Dunn"
        s = Ship(
            name=shipname,
            captain={
                "first_name": firstname,
                "last_name": lastname
            }
        )
        assert s.name == shipname
        assert s.captain.first_name == firstname
        assert s.captain.last_name == lastname

    def test_can_init_subschemas_with_dict(self):
        my_ship = {
            "name": "Podunk",
            "captain": {
                "first_name": "Steamboat",
                "last_name": "Willie"
            }
        }
        s = Ship(my_ship)
        assert s.serialize() == my_ship

    def test_can_use_arrays(self):
        s = Conversation()
        s.numbers = [1, 2, 3]
        assert s.numbers[0] == 1

        firstname = "Marilyn"
        lastname = "Monroe"
        s.conversants = [Person(first_name=firstname, last_name=lastname)]
        assert s.conversants[0].first_name == firstname

    def test_can_initialize_array(self):
        numbers = [1, 2, 3]
        s = Conversation(
            numbers=[1, 2, 3],
            conversants=[
                Person(first_name="me", last_name="person"),
                Person(first_name="you", last_name="person")
            ])
        assert s.numbers == numbers
        assert s.conversants[0].first_name == 'me'

    def test_can_init_arrays_with_dict(self):
        my_convo = {
            "numbers": [1, 2, 3],
            "conversants": [
                {"first_name": "me", "last_name": "person"},
                {"first_name": "you", "last_name": "person"}
            ]
        }
        # TODO this is not going to validate the inner schema tho
        s = Conversation(my_convo)
        self.assertEqual(s.serialize(), my_convo)

    def test_implicit_nulls_True(self):
        """Implicit nulls when True"""
        result = Conversation().serialize(implicit_nulls=True)
        self.assertEqual({}, result)

        result = Conversation(numbers=[1, 2]).serialize(implicit_nulls=True)
        self.assertEqual({"numbers": [1, 2]}, result)

    def test_implicit_nulls_False(self):
        """Implicit nulls when False"""
        result = Conversation().serialize(implicit_nulls=False)
        self.assertEqual({"numbers": None, "conversants": None}, result)

        result = Conversation(numbers=[1, 2]).serialize(implicit_nulls=False)
        self.assertEqual({"numbers": [1, 2], "conversants": None}, result)

    def test_false_is_not_null(self):
        """We treat several things as null-ish, but False is not one of them"""
        result = Conversation(numbers=False).serialize(implicit_nulls=True)
        self.assertEqual({"numbers": False}, result)

    def test_subschema_implicit_nulls(self):
        """An empty subschema is an implicit null"""
        my_ship = {
            "name": "Podunk",
            "captain": {
                "first_name": "Steamboat",
                "last_name": None
            }
        }
        s = Ship(my_ship).serialize(implicit_nulls=False)
        self.assertEqual(my_ship, s)

        s = Ship(my_ship).serialize(implicit_nulls=True)
        expected = {
            "name": "Podunk",
            "captain": {
                "first_name": "Steamboat"
            }
        }
        self.assertEqual(expected, s)

        my_ship = {
            "name": "Podunk",
            "captain": {}
        }
        s = Ship(my_ship).serialize(implicit_nulls=True)

        expected = {"name": "Podunk"}
        self.assertEqual(expected, s)

        my_ship = {
            "name": "Podunk",
            "captain": Person(first_name=None,
                              last_name=None)
        }
        s = Ship(my_ship).serialize(implicit_nulls=True)

        expected = {"name": "Podunk"}
        self.assertEqual(expected, s)

    def test_schema_can_use_defaults(self):
        s = DefaultsSchema().serialize()
        self.assertEqual(s.get("defaulted"), "testing")
        s = DefaultsSchema(defaulted=None).serialize()
        self.assertEqual(s.get("defaulted"), "testing")


class TestReservedWords(TestCase):
    def test_can_dunder_reserved_words(self):
        class Fancy(Schema):
            # if = IntegerField()  # Ouch! SyntaxError!
            __if = IntegerField()

        # can init with dunder kwarg arg
        s = Fancy(__if=1)
        assert hasattr(s, '_Fancy__if')
        assert hasattr(s, 'if')
        assert s.serialize() == {"if": 1}

        # can init with non-dunder splat kwarg
        d2 = {"if": 2}
        s2 = Fancy(**d2)
        assert s2.serialize() == d2

        # or dunder splat kwarg
        d3 = {"__if": 3}
        s3 = Fancy(**d3)
        assert s3.serialize() == {"if": 3}  # magic!

        # or straight assignment
        s4 = Fancy()
        s4.__if = 4
        assert s4.__if == 4
        assert s4.serialize() == {"if": 4}

    def test_can_get_dunder(self):
        class In(Schema):
            __finally = UnicodeField()

        class Out(Schema):
            wow = UnicodeField()

        class Whoa(Schema):
            __lambda = UnicodeField()

        class InToOut(Mapping):
            source_schema = In
            target_schema = Out

            wow = Get("finally")

        class InToWhoa(Mapping):
            source_schema = In
            target_schema = Whoa

            __lambda = Get("finally")

        result = InToOut().apply({"finally": "it is here"})
        self.assertEqual(result.serialize(), {"wow": "it is here"})

        result = InToWhoa().apply({"finally": "it is here"})
        self.assertEqual(result.serialize(), {"lambda": "it is here"})


class TestGenericSchema(TestCase):
    def test_can_make_a_generic_schema_from_dict(self):
        generic = GenericSchema(**{"foo": 1, "bar": 2, "baz": [3, 4, 5]})
        self.assertEqual(generic.foo, 1)
        self.assertEqual(generic.bar, 2)
        self.assertEqual(generic.baz, [3, 4, 5])
        self.assertIsNone(generic.qux)

    def test_can_make_generic_piecemeal(self):
        generic = GenericSchema()
        generic.foo = 1
        self.assertEqual(generic.foo, 1)
        self.assertIsNone(generic.qux)
        generic.qux = 'pah'
        self.assertEqual(generic.qux, 'pah')

    def test_generic_is_always_valid(self):
        generic1 = GenericSchema()
        assert generic1.validate()
        generic2 = GenericSchema(**{"foo": {}, "bar": "great"})
        assert generic2.validate()

    def test_can_serialize_generic(self):
        source = {"foo": 1, "bar": 2, "baz": [3, 4, 5]}
        generic = GenericSchema(**source)
        self.assertEqual(source, generic.serialize())

    def test_can_serialize_recursive(self):
        """
        When serializing, descend through arrays and subschemas.
        """
        class Some(Schema):
            wow = ArrayField()

        some_full = Some(wow=[1, 2])
        some_nullish = Some(wow=[])

        inner1 = GenericSchema()
        inner2 = GenericSchema(foo=["wow", inner1, some_full, some_nullish],
                               bar=inner1,
                               baz=[inner1, inner1])
        outer = GenericSchema(inner=inner2, cool="ok")
        expected_implicit_nulls = {
            "inner": {
                "foo": ["wow",
                        {"wow": [1, 2]}],
            },
            "cool": "ok"
        }
        expected_explicit_nulls = {
            "inner": {
                "foo": ["wow",
                        {},
                        {"wow": [1, 2]},
                        {"wow": []}],
                "bar": {},
                "baz": [{}, {}]
            },
            "cool": "ok"
        }
        self.assertEqual(expected_implicit_nulls,
                         outer.serialize(implicit_nulls=True))
        self.assertEqual(expected_explicit_nulls,
                         outer.serialize(implicit_nulls=False))


class OneToTwoBase(Mapping):
    peas = Get('my_str')
    carrots = Get('my_int')
    beans = Int(Get('another_str'))


class OneToTwo(OneToTwoBase):
    source_schema = Schema1
    target_schema = Schema2


class TwoToOne(Mapping):
    source_schema = Schema2
    target_schema = Schema1

    my_str = Get('peas')
    my_int = Get('carrots')
    another_str = Str(Get('beans'))


class TestMappings(TestCase):
    def setUp(self):
        self.original = {
            "my_str": u"woof",
            "my_int": 99,
            "another_str": u"123"
        }

        self.expected = {
            "peas": u"woof",
            "carrots": 99,
            "beans": 123
        }

    def test_simple_mapping(self):
        transformed = OneToTwo().apply(self.original).serialize()
        self.assertEqual(self.expected, transformed)

        back_again = TwoToOne().apply(transformed).serialize()
        self.assertEqual(self.original, back_again)

    def test_dont_even_need_schemas(self):
        """Schemas are really just to help you to keep your head straight"""
        transformed = OneToTwoBase().apply(self.original).serialize()
        self.assertEqual(self.expected, transformed)

    def test_constants_in_mapping(self):
        class Consistent(Mapping):
            one = Const(1)
            two = Const("two")
            three = Const(3.0)

        source = {
            "one": "doesn't",
            "two": "matter",
            "three": "what's here",
            "four": "amirite"
        }

        transformed = Consistent().apply(source).serialize()
        self.assertEqual({
            "one": 1,
            "two": "two",
            "three": 3.0,
        }, transformed)

    def test_empty_fields_serialize_as_none_valid_or_no(self):
        """We aren't making assumptions here. Call validate if you want it."""
        class FirstSchema(Schema):
            wow = IntegerField(required=True)
            umm = IntegerField(required=False)

        class OtherSchema(Schema):
            cool = IntegerField(required=True)
            bad = IntegerField(required=True)  # Uh oh

        class Mymap(Mapping):
            source_schema = FirstSchema
            target_schema = OtherSchema

            cool = Get('wow')
            bad = Get('umm')

        source = FirstSchema(wow=1)
        assert source.validate()

        transformed = Mymap().apply(source)
        with self.assertRaises(Invalid):
            transformed.validate()

        self.assertEqual({"cool": 1}, transformed.serialize(implicit_nulls=True))


class TestInheritance(TestCase):
    """Verify that the metaprogramming tricks didn't go awry"""
    def test_schemas_can_inherit(self):
        class SchemaA(Schema):
            peas = IntegerField()

        class SchemaB(SchemaA):
            turnips = IntegerField()

        assert isinstance(SchemaB.peas, IntegerField)
        assert isinstance(SchemaB.turnips, IntegerField)

        s = SchemaB()
        assert hasattr(s, "peas")
        assert "peas" in s._fields
        assert hasattr(s, "turnips")
        assert "turnips" in s._fields

    def test_mappings_can_inherit(self):
        class SchemaA(Schema):
            beans = IntegerField()
            carrots = IntegerField()

        class SchemaB(Schema):
            legumes = IntegerField()
            root_veg = IntegerField()

        class MappingA(Mapping):
            source_schema = SchemaA
            legumes = Get('beans')

        class MappingB(MappingA):
            target_schema = SchemaB
            root_veg = Get('carrots')

        assert isinstance(MappingB.legumes, Get)
        assert isinstance(MappingB.root_veg, Get)
        assert MappingB.source_schema is SchemaA
        assert MappingB.target_schema is SchemaB

        m = MappingB()
        assert hasattr(m, "legumes")
        assert "legumes" in m._fields
        assert hasattr(m, "root_veg")
        assert "root_veg" in m._fields
        assert m.source_schema is SchemaA
        assert m.target_schema is SchemaB

        source = {
            "beans": 1,
            "carrots": 2
        }
        expected = {"legumes": 1, "root_veg": 2}
        result = m.apply(source).serialize()
        self.assertEqual(expected, result)


class SquarePeg(Schema):
    id = IntegerField()
    name = UnicodeField()
    width = NumberField()


class RoundHole(Schema):
    id = UnicodeField()
    name = UnicodeField()
    diameter = NumberField()


def largest_square(width):
    return math.sqrt(2 * width**2)


class SquarePegToRoundHole(Mapping):
    source_schema = SquarePeg
    target_schema = RoundHole

    id = Concat('from_square', ':', Str(Get('id')))
    name = Get('name')
    diameter = Do(largest_square, Get('width'))


class ImpliesSchemas(Mapping):
    id = Concat('author', ':', Get('nom_de_plume'))
    name = Get('nom_de_plume')
    book = Get('best_known_for')


class TestReadmeExamples(TestCase):
    def test_square_peg(self):
        my_peg = SquarePeg(id=1, name="peggy", width=50)

        transformed = SquarePegToRoundHole().apply(my_peg).serialize()

        assert transformed['id'] == u'from_square:1'
        assert transformed['name'] == u'peggy'
        assert 70.71 < transformed['diameter'] < 70.72

    def test_implicit_schemas(self):
        source = {
            "nom_de_plume": "Mark Twain",
            "best_known_for": "Huckleberry Finn"
        }
        output = ImpliesSchemas().apply(source)

        assert type(output) == GenericSchema
        assert set(output.serialize().keys()) == {'book', 'id', 'name'}
