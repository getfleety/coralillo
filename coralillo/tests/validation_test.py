import unittest
from coralillo import Model, Form, Engine, fields
from coralillo.validation import validation_rule
from coralillo.errors import ValidationErrors, InvalidFieldError

nrm = Engine()


class TestForm(Form):
    field1 = fields.Text()
    field2 = fields.Text()

    @validation_rule
    def enforce_fields(data):
        if (data.field1 is None and data.field2 is None) or \
            (data.field1 is not None and data.field2 is not None):
            raise InvalidFieldError(field='field1')

    class Meta:
        engine = nrm


class TestModel(Model):
    field1 = fields.Text(index=True, required=False, private=True)

    class Meta:
        engine = nrm


class ValidationTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])

    def test_validate_with_custom_rules(self):
        with self.assertRaises(ValidationErrors):
            TestForm.validate(
                field1 = 'po',
                field2 = 'llo',
            )

        with self.assertRaises(ValidationErrors):
            TestForm.validate()

    def test_can_have_many_uniques_with_null_value(self):
        m1 = TestModel.validate().save()
        self.assertIsNone(m1.field1)

        m2 = TestModel.validate().save()
        self.assertIsNone(m2.field1)


if __name__ == '__main__':
    unittest.main()
