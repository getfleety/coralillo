from coralillo.errors import ValidationErrors
import pytest

from .models import MyForm, MyModel

def test_validate_with_custom_rules(nrm):
    with pytest.raises(ValidationErrors):
        MyForm.validate(
            field1 = 'po',
            field2 = 'llo',
        )

    with pytest.raises(ValidationErrors):
        MyForm.validate()

def test_can_have_many_uniques_with_null_value(nrm):
    m1 = MyModel.validate().save()
    assert m1.field1 is None

    m2 = MyModel.validate().save()
    assert m2.field1 is None
