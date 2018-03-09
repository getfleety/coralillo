Validation
==========

Coralillo includes validation capabilities so you can check the data sent by a
request before creating an object.

Validation code is part of the :py:class:`coralillo.Form` class, which is parent
of the :py:class:`coralillo.Model` class.

Basic usage
-----------

In its simplest form, validation ensures that the data passed to the validation
function matches the field definition of the class:

.. testcode::

   from coralillo import Form, Engine, fields, errors

   eng = Engine()

   class MyForm(Form):
      field1 = fields.Text()
      field2 = fields.Text(required=False)

      class Meta:
         engine = eng

   try:
      MyForm.validate()
   except errors.ValidationErrors as ve:
      assert len(ve) == 1
      assert ve[0].field == 'field1'

   data = MyForm.validate(field1='querétaro', field2='chihuahua')

   assert data.field1 == 'querétaro'
   assert data.field2 == 'chihuahua'

Default validations
-------------------

Validation rules are built on field definition, here are some rules that are
automatically added in addition to ``required`` rule.

.. testcode::

   from coralillo import Model, Engine, fields, errors

   eng = Engine()

   class Base(Model):

      class Meta:
         engine = eng

   # Validate uniqueness of indexes
   class Uniqueness(Base):
      username = fields.Text(index=True)

   Uniqueness(username='foo').save()

   try:
      Uniqueness.validate(username='foo')
   except errors.ValidationErrors as ve:
      assert isinstance(ve[0], errors.NotUniqueFieldError)

   # Validate regexes
   class Regex(Base):
      css_color = fields.Text(regex=r'#[0-9a-f]{6}')

   try:
      Regex.validate(css_color='white')
   except errors.ValidationErrors as ve:
      assert isinstance(ve[0], errors.InvalidFieldError)

   # Validate forbidden values
   class Forbidden(Base):
      name = fields.Text(forbidden=['john'])

   try:
      Forbidden.validate(name='john')
   except errors.ValidationErrors as ve:
      assert isinstance(ve[0], errors.ReservedFieldError)

   # Validate allowed values
   class Allowed(Base):
      name = fields.Text(allowed=['john'])

   try:
      Allowed.validate(name='maría')
   except errors.ValidationErrors as ve:
      assert isinstance(ve[0], errors.InvalidFieldError)

Non fillable fields
-------------------

Sometimes you might want to prevent a field from being filled or validated using
the :py:func:`coralillo.Form.validate`, in that case the keyword argument
``fillable`` of a field will do the trick.

Custom rules
------------

You can add custom rules to your forms or models to make even more complicated
validation rules.
