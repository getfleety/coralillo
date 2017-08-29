from redis.client import BasePipeline
import re

def to_pipeline(redis):
    if isinstance(redis, BasePipeline):
        return redis

    return redis.pipeline()

# from https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case
def snake_case(string):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', string)

    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def camelCase(string):
    return ''.join(s[0].upper()+s[1:] for s in string.split('_'))
