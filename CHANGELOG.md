# CHANGELOG

## 0.6.0

- Breaking change: When `ArrayField` declared with a Schema type as
  optional array type, coerce incoming dicts into that schema, just
  as we do with Subschema fields.

- Breaking change: in serialization, we are moving the default value of
  implicit_nulls from True to False. We judge that the more explicit
  behavior is the more general case, and implicit_nulls is the
  special case.

## 0.5.1

- Bugfix: `All` transformation works correctly with `GenericSchema`

## 0.5.0

- Bugfix: nullish data should not be dropped in transformations (All
  and ManySubmap transformations had this behavior); rather it is
  retained and a decision about whether to present it may be made upon
  serialization via `implicit_nulls` parameter.

- Breaking change: the `All` transformation on a Schema will return a
  Schema. Previously it would have returned a dict in this
  scenario. Similarly, `ManySubmap` will return a list of Schema where
  before it would have returned a list of dict. In both cases the
  post-serialization form will look the same, but nota bene if your
  code manipulates the return value of Mapping.apply() or otherwise
  uses these objects without serialization.


## 0.4.1

- Bugfix: state was incorrectly being stored on schema class rather
  than instances

## 0.4.0

- Add Chain transformation

## 0.3.0

- Syntax sugar to allow reserved words in schema.

## 0.2.0

- Python 3 compatibility

- Defaults on Fields

## 0.1.4

- Bugfix: Typeerror on null submapping

## 0.1.3

- Documentation and cleanup

## 0.1.2

- Fixes validation when IsoDateString is not a required field

## 0.1.1

- First public version
