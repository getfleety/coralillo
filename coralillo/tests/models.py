from coralillo import Model, Form, BoundedModel, Engine, fields

# for model testing
class Table(Model):
    name = fields.Text()

class Ship(Model):
    name = fields.Text()
    code = fields.Text(index=True)

class Tenanted(BoundedModel):
    name = fields.Text()

    @classmethod
    def prefix(cls):
        return 'testing'

class SideWalk(Model):
    name = fields.Text()

class House(Model):
    number = fields.Integer(required=False)

# for events test
class Something(Model):
    name = fields.Text()
    notify = True

# for fields test
class Subscription(Model):
    key_name = fields.TreeIndex()

class User(Model):
    password = fields.Hash()

class Truck(Model):
    last_position = fields.Location()

# for form testing
class ShipForm(Form):
    name = fields.Text()
    code = fields.Text()

# For testing relationships
class Pet(Model):
    name = fields.Text()
    owner = fields.ForeignIdRelation('coralillo.tests.models.Person', inverse='pets')


class Person(Model):
    name = fields.Text()
    pets = fields.SetRelation(Pet, on_delete='cascade', inverse='owner')


# For many to many relations
class Driver(Model):
    name = fields.Text()
    cars = fields.SetRelation('coralillo.tests.models.Car', inverse='drivers')


class Car(Model):
    name = fields.Text()
    drivers = fields.SetRelation(Driver, inverse='cars')


class Employee(Model):
    name = fields.Text()
    last_name = fields.Text()
    office = fields.ForeignIdRelation('coralillo.tests.models.Office', inverse='employees')


class Office(Model):
    name = fields.Text()
    address = fields.Text()
    employees = fields.SetRelation(Employee, inverse='office')

def bound_models(eng):
    Car.set_engine(eng)
    Driver.set_engine(eng)
    Employee.set_engine(eng)
    House.set_engine(eng)
    Office.set_engine(eng)
    Person.set_engine(eng)
    Pet.set_engine(eng)
    Ship.set_engine(eng)
    ShipForm.set_engine(eng)
    SideWalk.set_engine(eng)
    Something.set_engine(eng)
    Subscription.set_engine(eng)
    Table.set_engine(eng)
    Tenanted.set_engine(eng)
    User.set_engine(eng)
    Truck.set_engine(eng)
