from coralillo import Model, Engine
from coralillo.fields import Text, SetRelation, ForeignIdRelation


class Pet(Model):
    name = Text()
    owner = ForeignIdRelation('coralillo.tests.models.Person', inverse='pets')


class Person(Model):
    name = Text()
    pets = SetRelation(Pet, on_delete='cascade', inverse='owner')


# For many to many relations
class Driver(Model):
    name = Text()
    cars = SetRelation('coralillo.tests.models.Car', inverse='drivers')


class Car(Model):
    name = Text()
    drivers = SetRelation(Driver, inverse='cars')


class Employee(Model):
    name = Text()
    last_name = Text()
    office = ForeignIdRelation('coralillo.tests.models.Office', inverse='employees')


class Office(Model):
    name = Text()
    address = Text()
    employees = SetRelation(Employee, inverse='office')


def bound_models(eng):
    Pet.set_engine(eng)
    Person.set_engine(eng)
    Driver.set_engine(eng)
    Car.set_engine(eng)
    Employee.set_engine(eng)
    Office.set_engine(eng)
