from coralillo import Engine, Form, fields
import unittest

nrm = Engine()


class Ship(Form):
    name = fields.Text()
    code = fields.Text()

    class Meta:
        engine = nrm


class FormTestCase(unittest.TestCase):

    def test_init_form(self):
        obj = Ship()

        self.assertIsNone(obj.name)
        self.assertIsNone(obj.code)


if __name__ == '__main__':
    unittest.main()
