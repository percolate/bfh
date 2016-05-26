"""
Fields that can go on Schemas

Included are the common data types you'll probably need, and a generic `Field`
class so you can implement your own if you want.
"""
from __future__ import absolute_import

import re
from datetime import datetime

from .common import nullish
from .exceptions import Invalid
from .interfaces import FieldInterface, SchemaInterface

try:
    string_type = unicode
except NameError:
    string_type = str


__all__ = [
    "ArrayField",
    "BooleanField",
    "DatetimeField",
    "Field",
    "IsoDateString",
    "IntegerField",
    "NumberField",
    "ObjectField",
    "Subschema",
    "UnicodeField",
]


class Field(FieldInterface):
    """
    Base class for a field.

    You can create custom fields if you inherit this and implement
    `serialize` and `validate` as desired:

        class AngryField(Field):
            def serialize(self, value, **kwargs):
                return "I HATE YOU"

            def validate(self, value):
                return False

    """
    def __init__(self, required=True, default=None):
        """
        Initialize the field.

        Args:
            required (Bool) - is this a required field in the schema?
        """
        self.required = required
        self.default = default

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        value = instance.__dict__.get(self.field_name)
        if value is not None:
            return value
        else:
            default = self.default
            instance.__dict__[self.field_name] = default
            return default

    def __set__(self, instance, value):
        instance.__dict__[self.field_name] = value

    def serialize(self, value, **kwargs):
        """
        Transform the value into whatever shape you'd like it to appear in a
        Python dict, ready for use in the outside world.

        """
        return value

    def validate(self, value):
        """
        Is the value valid in this kind of field?

        """
        if self.required and value is None:
            raise Invalid("%s: a value is required" % self.field_name)
        return True

    @property
    def field_name(self):
        return getattr(self, "_field_name", "unnamed")

    @field_name.setter
    def field_name(self, value):
        self._field_name = value

    @property
    def default(self):
        return self._default() if callable(self._default) else self._default

    @default.setter
    def default(self, value):
        self._default = value


class Subschema(Field):
    """
    A field that defines a subschema.

    Define one schema, then you can use this field to embed it in another:

        class Inner(Schema):
            # some fields

        class MySchema(Schema):
            inner = Subschema(Inner)
            # more fields

    """
    def __init__(self, subschema_class, *args, **kwargs):
        super(Subschema, self).__init__(*args, **kwargs)
        self.subschema_class = subschema_class

    def __set__(self, instance, value):
        if isinstance(value, dict):
            instance.__dict__[self.field_name] = self.subschema_class(**value)
        else:
            instance.__dict__[self.field_name] = value

    def serialize(self, value, implicit_nulls=True):
        """
        A Subschema serializes as a dict.

        Kwargs:
            implicit_nulls (bool): drop keys with falsey values
        """
        if hasattr(value, "serialize"):
            value = value.serialize(implicit_nulls=implicit_nulls)

        if value is None:
            value = {}

        if isinstance(value, dict) and implicit_nulls:
            if all(nullish(v) for v in value.values()):
                value = {}

        return value

    def validate(self, value):
        super(Subschema, self).validate(value)
        if not self.required:
            if nullish(value):
                return True
            if getattr(value, "is_empty", False):
                return True

        if not hasattr(value, 'validate'):
            value = self.subschema_class(value)

        value.validate()
        return True


class SimpleTypeField(Field):
    """
    Base class for fields that simply validate a type.

    Expects a class attribute 'field_type'.
    """
    def _valid(self, value):
        if value is None and not self.required:
            return True
        return isinstance(value, self.field_type)

    def validate(self, value):
        super(SimpleTypeField, self).validate(value)
        if not self._valid(value):
            raise Invalid("%s: %s is not a valid %s" % (self.field_name,
                                                        value,
                                                        self.field_type))
        return True


class BooleanField(SimpleTypeField):
    """
    A field that should contain a boolean.

    """
    field_type = bool


class IntegerField(SimpleTypeField):
    """
    A field that should contain an integer.

    """
    field_type = int


class NumberField(SimpleTypeField):
    """
    A field that should contain a floating-point number.

    """
    field_type = float


class DatetimeField(SimpleTypeField):
    """
    A field that should contain a Python datetime object.

    """
    field_type = datetime


class UnicodeField(SimpleTypeField):
    """
    A field that contains strings.

    Expect unicode. If it's not already unicode, assume it's utf-8 and
    transform it to unicode.
    """
    field_type = string_type

    def __init__(self, strict=False, encoding='utf-8', **kwargs):
        """
        Kwargs:
            strict (bool): don't coerce a non-unicode string to unicode
            encoding (str): default 'utf-8'
        """
        super(UnicodeField, self).__init__(**kwargs)
        self.strict = strict
        self.encoding = encoding

    def _coerce(self, value):
        if isinstance(value, string_type):
            return value
        try:
            return value.decode(self.encoding)
        except AttributeError:
            raise Invalid("%s: %s is not a string" % (self.field_name, value))

    def validate(self, value):
        if self.strict or (value is None and not self.required):
            return super(UnicodeField, self).validate(value)
        return super(UnicodeField, self).validate(self._coerce(value))

    def serialize(self, value, **kwargs):
        try:
            return self._coerce(value)
        except Invalid:  # we are not in the business of validation here
            return value


class IsoDateString(UnicodeField):
    """
    A string field that validates that it contains an ISO 8601 date string

    """
    ISO_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def validate(self, value):
        if not self.required and value is None:
            return True

        super(IsoDateString, self).validate(value)
        if not bool(self.ISO_REGEX.match(value)):
            raise Invalid("%s not an ISO 8601 date string")

        return True


class ObjectField(SimpleTypeField):
    """
    A field that can contain a schemaless dict or object.

    """
    field_type = (dict, SchemaInterface)

    def validate(self, value):
        super(ObjectField, self).validate(value)
        if hasattr(value, "validate"):
            value.validate()
        return True

    def serialize(self, value, implicit_nulls=True):
        """
        Kwargs:
            implicit_nulls (bool): drop keys with falsey values
        """
        if hasattr(value, "serialize"):
            value = value.serialize(implicit_nulls=implicit_nulls)

        if value is None:
            value = {}

        if isinstance(value, dict) and implicit_nulls:
            if all(nullish(v) for v in value.values()):
                value = {}

        return value


class ArrayField(SimpleTypeField):
    """
    A field that can contain an array of things of type `array_type`

        class Inner(Schema):
             wow = IntegerField()

        class MySchema(Schema):
             ints = ArrayField(int)
             inners = ArrayField(Inner)

    indicates an object that looks like so:

        {"ints": [1, 2, 3], "inners": [{"wow": 4}, {"wow": 5}]}

    """
    field_type = (list, tuple)

    def __init__(self, array_type=None, **kwargs):
        """
        Kwargs:
            array_type (type or Schema)
        """
        super(ArrayField, self).__init__(**kwargs)
        self.array_type = array_type

    def __set__(self, instance, value):
        # don't coerce or validate simple Python types here; under the current
        # regime those happen elsewhere. just set the value.
        if (self.array_type is None
                or not issubclass(self.array_type, SchemaInterface)
                or not isinstance(value, self.field_type)):
            instance.__dict__[self.field_name] = value
            return

        # when we have a schema array type, assume any dict
        # passed is trying to fit the schema.
        result = []
        for i in value:
            if isinstance(i, dict):
                result.append(self.array_type(**i))
            else:
                # could already be a Schema instance, or maybe it's not even
                # valid, but we don't care, we're not validating here
                result.append(i)
        instance.__dict__[self.field_name] = result

    def _flatten(self, value, implicit_nulls=True):
        if hasattr(value, 'serialize'):
            return value.serialize(implicit_nulls=implicit_nulls)
        return value

    @property
    def is_schema_type(self):
        return issubclass(self.array_type, SchemaInterface)

    def validate(self, items):
        # blech... it's not a validation lib. it's not a validation lib.
        super(ArrayField, self).validate(items)
        if not self.required and items in (None, [], tuple()):
            return True

        if self.is_schema_type:
            for val in items:
                if isinstance(val, self.array_type):
                    return val.validate()
                if isinstance(val, SchemaInterface):  # wrong schema
                    raise Invalid("%s is not a %s" % (val, self.array_type))

                # val is an object literal. see if it matches schema.
                in_schema = self.array_type(val)
                return in_schema.validate()

        elif self.array_type is not None and items is not None:
            for val in items:
                if not isinstance(val, self.array_type):
                    raise Invalid("%s is not a %s" % (val, self.array_type))

        return True

    def serialize(self, value, implicit_nulls=True):
        if isinstance(value, self.field_type):
            items = []
            for i in value:
                flat = self._flatten(i, implicit_nulls=implicit_nulls)
                if not nullish(flat, implicit_nulls=implicit_nulls):
                    items.append(flat)
            return items
        return value
