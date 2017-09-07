from .models import *
import unittest


class PresentationTestCase(unittest.TestCase):

    def setUp(self):
        nrm.lua.drop(args=['*'])

    def test_fields(self):
        office = Office(
            name = 'Fleety',
            address = 'Springfield 132',
        ).save()

        self.assertDictEqual(office.to_json(), {
            'id': office.id,
            'name': office.name,
            'address': office.address,
            '_type': 'office',
        })

        self.assertDictEqual(office.to_json(fields=['name']), {
            'name': 'Fleety',
        })

        self.assertDictEqual(office.to_json(fields=['id', 'name']), {
            'id': office.id,
            'name': office.name,
        })

        self.assertDictEqual(office.to_json(fields=['none']), {})

    def test_embed(self):
        office = Office(
            name = 'Fleety',
            address = 'Springfield 132',
        ).save()
        employee = Employee(
            name = 'Juan',
            last_name = 'Alduci',
        ).save()
        office.proxy.employees.set([employee])

        self.assertDictEqual(office.to_json(embed=['employees']), {
            'id': office.id,
            'name': office.name,
            'address': office.address,
            'employees': [employee.to_json()],
            '_type': 'office',
        })

        self.assertDictEqual(office.to_json(embed=['employees.name']), {
            'id': office.id,
            'name': office.name,
            'address': office.address,
            'employees': [employee.to_json(fields=['name'])],
            '_type': 'office',
        })

        self.assertDictEqual(office.to_json(embed=['employees.name', 'employees.id']), {
            'id': office.id,
            'name': office.name,
            'address': office.address,
            'employees': [employee.to_json(fields=['name', 'id'])],
            '_type': 'office',
        })

    def test_embed_foreignid_relation(self):
        office = Office(
            name = 'Fleety',
            address = 'Springfield 132',
        ).save()
        employee = Employee(
            name = 'Juan',
            last_name = 'Alduci',
        ).save()
        office.proxy.employees.set([employee])

        self.assertDictEqual(employee.to_json(embed=['office']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': office.to_json(),
        })

        self.assertDictEqual(employee.to_json(embed=['office.name']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': office.to_json(fields=['name']),
        })

        self.assertDictEqual(employee.to_json(embed=['office.name', 'office.id']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': office.to_json(fields=['name', 'id']),
        })

        office.proxy.employees.remove(employee)

        self.assertDictEqual(employee.to_json(embed=['office']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': None,
        })

        self.assertDictEqual(employee.to_json(embed=['office.name']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': None,
        })

        self.assertDictEqual(employee.to_json(embed=['office.name', 'office.id']), {
            'id': employee.id,
            'name': employee.name,
            'last_name': employee.last_name,
            '_type': 'employee',
            'office': None,
        })
