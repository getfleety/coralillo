from norm import Model
from norm.fields import Text, SetRelation, ForeignIdRelation

# For one-many relations
class Pet(Model):
    name = Text()
    owner = ForeignIdRelation('norm.tests.models.Person', inverse='pets')


class Person(Model):
    name = Text()
    pets = SetRelation(Pet, on_delete='cascade', inverse='owner')


# For many to many relations
class Driver(Model):
    name = Text()
    cars = SetRelation('norm.tests.models.Car', inverse='drivers')


class Car(Model):
    name = Text()
    drivers = SetRelation(Driver, inverse='cars')
