from coralillo import Engine
import pytest

from .models import bound_models

@pytest.fixture
def nrm():
    nrm = Engine()

    nrm.lua.drop(args=['*'])

    bound_models(nrm)

    return nrm
