from norm import Model, create_engine
from norm.fields import Text, SetRelation, ForeignIdRelation

nrm = create_engine()


# For one-many relations
class Pet(Model):
    name = Text()
    owner = ForeignIdRelation('norm.tests.models.Person', inverse='pets')

    class Meta:
        engine = nrm


class Person(Model):
    name = Text()
    pets = SetRelation(Pet, on_delete='cascade', inverse='owner')

    class Meta:
        engine = nrm


# For many to many relations
class Driver(Model):
    name = Text()
    cars = SetRelation('norm.tests.models.Car', inverse='drivers')

    class Meta:
        engine = nrm


class Car(Model):
    name = Text()
    drivers = SetRelation(Driver, inverse='cars')

    class Meta:
        engine = nrm
