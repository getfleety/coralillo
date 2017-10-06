from coralillo import Model, Engine
from coralillo.fields import Text, SetRelation, ForeignIdRelation

nrm = Engine()

class TestModel(Model):
    class Meta:
        engine = nrm

# For one-many relations
class Pet(TestModel):
    name = Text()
    owner = ForeignIdRelation('coralillo.tests.models.Person', inverse='pets')


class Person(TestModel):
    name = Text()
    pets = SetRelation(Pet, on_delete='cascade', inverse='owner')


# For many to many relations
class Driver(TestModel):
    name = Text()
    cars = SetRelation('coralillo.tests.models.Car', inverse='drivers')


class Car(TestModel):
    name = Text()
    drivers = SetRelation(Driver, inverse='cars')


class Employee(TestModel):
    name = Text()
    last_name = Text()
    office = ForeignIdRelation('coralillo.tests.models.Office', inverse='employees')


class Office(TestModel):
    name = Text()
    address = Text()
    employees = SetRelation(Employee, inverse='office')
