"""
Transformations that can go on Mappings.

When you `apply` a mapping to an object, the transformations
filter that object into the form of the output schema.

- You can `Get` the value from a field and pass it somewhere.
- You can use `All` to pass the whole input object somewhere.
- You can coerce a value into a type with `Bool`, `Int`, `Num`, or `Str`.
- You can `Concat` some values together into one value.
- You can use `Many` to group some values into a list.
- You can pass a constant value with `Const` no matter what the input object
- You can `Do` arbitrary functions on input.
- You can nest mappings inside others with `Submapping` and `ManySubmap`

"""
from __future__ import absolute_import

from datetime import datetime

from dateutil.parser import parse as parse_date
import six

from itertools import chain

from .common import utc
from .exceptions import Missing
from .interfaces import TransformationInterface

try:
    unicode_type = unicode
except NameError:
    unicode_type = str

__all__ = [
    "All",
    "Bool",
    "Concat",
    "Const",
    "Do",
    "Get",
    "Int",
    "Many",
    "ManySubmap",
    "Num",
    "Str",
    "Submapping",
]


class All(TransformationInterface):
    """
    Get the *whole darn source object*

    Kwargs:
        strict (Bool) - If the object is a schema, drop any extra keys
                        that don't appear in the schema.

    Returns:
        If strict == False and called on a Schema instance, a GenericSchema
        Otherwise just the object.
    """
    def __init__(self, strict=False):
        self.strict = strict

    def __call__(self, source):
        return self.function(source)

    def function(self, source):
        if not self.strict and hasattr(source, '_raw'):
            return source._raw
        return source


class Get(TransformationInterface):
    """
    Gets a value from a dict or object

        value = Get("my_thing")({"my_thing": "get this"})
        value == "get this"

    Fetch values from complex objects by passing multiple arguments.

        value = Get("a", "b")({"a": {"b": 1}})
        value == 1

    Args:
        a series of names to follow into object and subobject.

    Kwargs:
        required (bool, default False) -- error if names missing

    Returns:
        fetched value or None if `required`

    Raises:
        Missing if `required` is false

    """
    def __init__(self, *args, **kwargs):
        """
        """
        self.path = args
        self.kwargs = kwargs
        self.required = kwargs.get('required', False)

    def __call__(self, source):
        return self.function(source)

    def _get_from_dict(self, source, path):
        if not self.required:
            return source.get(path)
        return source[path]

    def _get_from_obj(self, source, path):
        if not self.required:
            return getattr(source, path, None)
        return getattr(source, path)

    def _get(self, source, path):
        try:
            if isinstance(source, dict):
                return self._get_from_dict(source, path)
            return self._get_from_obj(source, path)
        except (KeyError, AttributeError) as e:
            raise Missing(e)

    def function(self, source, path=None):
        parts = path or self.path
        first, rest = parts[0], parts[1:]
        got = self._get(source, first)
        if rest:
            return self.function(got, rest)
        return got


class Transformation(TransformationInterface):
    """
    A callable thing that transforms an input.

    Base class for transformations; they should implement `function`.

    Kwargs:
        required (bool, default False) -- error if names missing
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        if kwargs.get('required') is None:
            self.required = False
        else:
            self.required = kwargs.get('required')

    def __call__(self, source=None):
        call_args = []
        for arg in self.args:
            if isinstance(arg, TransformationInterface):
                call_args.append(arg(source))
            else:
                call_args.append(arg)

        return self.function(source, *call_args)


class Submapping(Transformation):
    """
    Map a complex subobject into a subschema.

    Returns:
        result of applying submapping to the input
    """
    def __init__(self, submapping_class, *args):
        self.submapping_class = submapping_class
        self.args = args

    def function(self, source, *call_args):  # source ignored
        return self.submapping_class().apply(call_args[0])


def _many_items(call_args, drop_nones=True):
    """
    Helper function for array-ish transformations.

    """
    if drop_nones:
        call_args = [i for i in call_args if i is not None]

    if len(call_args) > 1:
        return call_args

    if len(call_args) == 1 and isinstance(call_args[0], (list, tuple)):
        return call_args[0]

    elif len(call_args) == 1:
        return [call_args[0]]

    else:
        return []


class ManySubmap(Submapping):
    """
    Map an array of complex objects onto a subschema.

    Returns:
        results of applying submapping to each item in the input
    """
    def function(self, source, *call_args):  # source ignored
        return [self.submapping_class().apply(item)
                for item in _many_items(call_args)]


class Many(Transformation):
    """
    Construct an array from a series of values.

    Args:
        subtrans (Transformation): transformation to apply to all input items

    Returns:
        results of applying subtransformation to each item in the input
    """
    def __init__(self, subtrans, *args, **kwargs):
        self.subtrans = subtrans  # Transformation
        self.args = args
        self.kwargs = kwargs

    def function(self, source, *call_args):
        if isinstance(self.subtrans, Submapping):
            raise ValueError("Can't Many(Submapping). Use Manymap instead.")

        return [self.subtrans(item, **self.kwargs)()
                for item in _many_items(call_args)]


class Const(Transformation):
    """
    Return a constant value.

    """
    def function(self, source, *call_args):  # source ignored
        return call_args[0]


class CoerceType(Transformation):
    """
    A base class for transformations that use basic Python type coercion

    """

    null_types = (None,)

    @property
    def target_type(self):
        raise NotImplementedError("Specify a type")

    def function(self, source, *call_args):  # source ignored
        value = call_args[0]
        if not self.required and value in self.null_types:
            return value
        return self.target_type(value)


class Int(CoerceType):
    """
    Coerce input to an integer

    """
    target_type = int


class Num(CoerceType):
    """
    Coerce input to a floating point number

    """
    target_type = float


class Str(CoerceType):
    """
    Coerce input to a unicode string

    """
    target_type = unicode_type

    null_types = (None, "")


class Bool(CoerceType):
    """
    Coerce input to a boolean

    """
    target_type = bool


class Concat(Transformation):
    """
    Concat some strings into a single string.

    """
    def __init__(self, *args, **kwargs):
        super(Concat, self).__init__(*args, **kwargs)
        self.strict = kwargs.get('strict', False)

    def function(self, source, *call_args):  # source ignored
        if not self.strict:
            call_args = [i for i in call_args if i]
        return "".join(call_args)


class Do(Transformation):
    """
    Do an arbitrary thing to something.

        class MyMapping(Mapping):
            four = Do(lambda x: x*x, Get('two'))

        MyMapping().apply({'two': 2}).serialize()
        # {'four': 4}

    Args:
        the first positional arg to the constructor should be a callable...
        this callable is applied to the input generated by the subsequent args
    """
    def function(self, source, *call_args):  # source ignored
        return call_args[0](*call_args[1:])


class Chain(Transformation):
    """Chain an arbitrary number of iterables."""
    def function(self, source, *call_args):
        return list(chain(*call_args))


class ParseDate(Transformation):
    """
    Parse a date-ish string into a datetime object.

    """
    DEFAULT_TIMEZONE = utc

    @property
    def tz(self):
        return self.kwargs.get("tz", self.DEFAULT_TIMEZONE)

    def function(self, source, *call_args):  # source ignored
        value = call_args[0]
        if isinstance(value, int):
            date = datetime.utcfromtimestamp(value)
        elif isinstance(value, six.string_types):
            date = parse_date(value)
        else:
            raise TypeError("Could not parse %s" % value)

        if date.tzinfo is None:
            date = date.replace(tzinfo=self.tz)

        return date


class DateToIsoString(Transformation):
    """
    Turn a datetime into an ISO 8601 formatted string.

    """
    def function(self, source, *call_args):  # source ignored
        try:
            return call_args[0].isoformat()
        except (IndexError, AttributeError):
            raise ValueError("Not a datetime: %s" % (
                call_args[0] if call_args else None))
