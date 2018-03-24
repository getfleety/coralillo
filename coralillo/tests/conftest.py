from coralillo import Engine, Model, fields
from coralillo.auth import PermissionHolder
import pytest

from .models import bound_models

@pytest.fixture
def nrm():
    nrm = Engine()

    nrm.lua.drop(args=['*'])

    bound_models(nrm)

    return nrm

@pytest.fixture
def user():
    class User(Model, PermissionHolder):
        name = fields.Text()

        class Meta:
            engine = nrm()

    return User(
        name      = 'juan',
    ).save()
