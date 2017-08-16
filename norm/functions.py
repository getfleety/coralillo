from datetime import datetime, timedelta
from random import random

def current_timestamp():
    return datetime.now().replace(microsecond=0)

def random_location():
    return [random()*160-80, random()*360-180]
