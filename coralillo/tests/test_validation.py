import unittest
from coralillo import Form, Engine, fields
from coralillo.validation import validation_rule
from coralillo.errors import ValidationErrors, InvalidFieldError

class TestForm(Form):
    field1 = fields.Text()
    field2 = fields.Text()

    @validation_rule
    def enforce_fields(data):
        if (data.field1 is None and data.field2 is None) or \
            (data.field1 is not None and data.field2 is not None):
            raise InvalidFieldError(field='field1')

    class Meta:
        engine = Engine()

class ValidationTestCase(unittest.TestCase):

    def test_validate_with_custom_rules(self):
        with self.assertRaises(ValidationErrors):
            TestForm.validate(
                field1 = 'po',
                field2 = 'llo',
            )

        with self.assertRaises(ValidationErrors):
            TestForm.validate()


if __name__ == '__main__':
    unittest.main()
