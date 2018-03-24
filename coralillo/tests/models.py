from coralillo import Model, Engine
from coralillo.fields import Text, SetRelation, ForeignIdRelation

nrm = Engine()

class BaseModel(Model):
    class Meta:
        engine = nrm

# For one-many relations
class Pet(BaseModel):
    name = Text()
    owner = ForeignIdRelation('coralillo.tests.models.Person', inverse='pets')


class Person(BaseModel):
    name = Text()
    pets = SetRelation(Pet, on_delete='cascade', inverse='owner')


# For many to many relations
class Driver(BaseModel):
    name = Text()
    cars = SetRelation('coralillo.tests.models.Car', inverse='drivers')


class Car(BaseModel):
    name = Text()
    drivers = SetRelation(Driver, inverse='cars')


class Employee(BaseModel):
    name = Text()
    last_name = Text()
    office = ForeignIdRelation('coralillo.tests.models.Office', inverse='employees')


class Office(BaseModel):
    name = Text()
    address = Text()
    employees = SetRelation(Employee, inverse='office')
