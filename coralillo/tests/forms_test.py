from .models import ShipForm

def test_init_form():
    obj = ShipForm()

    assert obj.name is None
    assert obj.code is None
