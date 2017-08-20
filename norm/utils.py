from redis.client import BasePipeline

def to_pipeline(redis):
    if isinstance(redis, BasePipeline):
        return redis

    return redis.pipeline()
