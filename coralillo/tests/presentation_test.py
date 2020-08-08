from .models import Office, Employee, A, B, C


def test_include_simplest(nrm):
    office = Office(
        name='Fleety',
        address='Springfield 132',
    ).save()

    assert office.to_json() == {
        'id': office.id,
        'name': office.name,
        'address': office.address,
        '_type': 'office',
    }

    assert office.to_json(include=['name']) == {
        'name': 'Fleety',
    }

    assert office.to_json(include=['id', 'name']) == {
        'id': office.id,
        'name': office.name,
    }

    assert office.to_json(include=['none']) == {}


def test_incude(nrm):
    office = Office(
        name='Fleety',
        address='Springfield 132',
    ).save()
    employee = Employee(
        name='Juan',
        last_name='Alduci',
    ).save()
    office.employees.set([employee])

    assert office.to_json(include=['id', 'employees']) == {
        'id': office.id,
        'employees': [employee.to_json()],
    }

    assert office.to_json(include=['id', 'employees.name']) == {
        'id': office.id,
        'employees': [employee.to_json(include=['name'])],
    }

    assert office.to_json(include=['id', 'employees.name', 'employees.id']) == {
        'id': office.id,
        'employees': [employee.to_json(include=['name', 'id'])],
    }


def test_include_foreignid_relation(nrm):
    office = Office(
        name='Fleety',
        address='Springfield 132',
    ).save()
    employee = Employee(
        name='Juan',
        last_name='Alduci',
    ).save()
    office.employees.set([employee])

    assert employee.to_json(include=['id', 'office']) == {
        'id': employee.id,
        'office': office.to_json(),
    }

    assert employee.to_json(include=['id', 'office.name']) == {
        'id': employee.id,
        'office': office.to_json(include=['name']),
    }

    assert employee.to_json(include=['id', 'office.name', 'office.id']) == {
        'id': employee.id,
        'office': office.to_json(include=['name', 'id']),
    }

    office.employees.remove(employee)

    assert employee.to_json(include=['id', 'office']) == {
        'id': employee.id,
        'office': None,
    }

    assert employee.to_json(include=['id', 'office.name']) == {
        'id': employee.id,
        'office': None,
    }

    assert employee.to_json(include=['id', 'office.name', 'office.id']) == {
        'id': employee.id,
        'office': None,
    }


def test_include_three_levels():
    a = A(attr='z').save()

    b = B(attr='z').save()
    b.a.set(a)

    c = C(attr='z').save()
    c.b.set(b)

    assert a.to_json(include=['attr', 'bs.cs']) == {
        'attr': 'z',
        'bs': [{
            'cs': [{
                '_type': 'c',
                'id': c.id,
                'attr': c.attr,
            }],
        }],
    }

    assert a.to_json(include=['attr', 'bs.cs.id']) == {
        'attr': 'z',
        'bs': [{
            'cs': [{
                'id': c.id,
            }],
        }],
    }


def test_include_asterisc():
    a = A(attr='z').save()

    b = B(attr='z').save()
    b.a.set(a)

    c = C(attr='z').save()
    c.b.set(b)

    assert a.to_json(include=['*', 'bs.cs.attr']) == {
        '_type': 'a',
        'id': a.id,
        'attr': 'z',
        'bs': [{
            'cs': [{
                'attr': c.attr,
            }],
        }],
    }
