from .models import Office, Employee


def test_fields(nrm):
    office = Office(
        name = 'Fleety',
        address = 'Springfield 132',
    ).save()

    assert office.to_json() == {
        'id': office.id,
        'name': office.name,
        'address': office.address,
        '_type': 'office',
    }

    assert office.to_json(fields=['name']) == {
        'name': 'Fleety',
    }

    assert office.to_json(fields=['id', 'name']) == {
        'id': office.id,
        'name': office.name,
    }

    assert office.to_json(fields=['none']) == {}

def test_embed(nrm):
    office = Office(
        name = 'Fleety',
        address = 'Springfield 132',
    ).save()
    employee = Employee(
        name = 'Juan',
        last_name = 'Alduci',
    ).save()
    office.proxy.employees.set([employee])

    assert office.to_json(embed=['employees']) == {
        'id': office.id,
        'name': office.name,
        'address': office.address,
        'employees': [employee.to_json()],
        '_type': 'office',
    }

    assert office.to_json(embed=['employees.name']) == {
        'id': office.id,
        'name': office.name,
        'address': office.address,
        'employees': [employee.to_json(fields=['name'])],
        '_type': 'office',
    }

    assert office.to_json(embed=['employees.name', 'employees.id']) == {
        'id': office.id,
        'name': office.name,
        'address': office.address,
        'employees': [employee.to_json(fields=['name', 'id'])],
        '_type': 'office',
    }

def test_embed_foreignid_relation(nrm):
    office = Office(
        name = 'Fleety',
        address = 'Springfield 132',
    ).save()
    employee = Employee(
        name = 'Juan',
        last_name = 'Alduci',
    ).save()
    office.proxy.employees.set([employee])

    assert employee.to_json(embed=['office']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': office.to_json(),
    }

    assert employee.to_json(embed=['office.name']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': office.to_json(fields=['name']),
    }

    assert employee.to_json(embed=['office.name', 'office.id']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': office.to_json(fields=['name', 'id']),
    }

    office.proxy.employees.remove(employee)

    assert employee.to_json(embed=['office']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': None,
    }

    assert employee.to_json(embed=['office.name']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': None,
    }

    assert employee.to_json(embed=['office.name', 'office.id']) == {
        'id': employee.id,
        'name': employee.name,
        'last_name': employee.last_name,
        '_type': 'employee',
        'office': None,
    }
