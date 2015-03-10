import redis
import time
import random
import json
import os

class redis_queue:
    redis_host = None
    r = None

    def __init__(self, redis_host = "localhost", redis_port=6379):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.r = redis.Redis(host=self.redis_host, port=self.redis_port)

    def q_push(self, q, item):
        ret = self.r.rpush(q, item)
        return ret

    def q_move(self, q_from, q_to):
        ret = self.r.rpoplpush(q_from, q_to)
        return ret

    def q_remove(self, q, item):
        ret = self.r.lrem(q,item,0)
        return ret

    def q_len(self, q):
        items = self.r.lrange(q, 0, -1)
        return len(items)

    def q_print(self, q):
        items = self.r.lrange(q, 0, -1)
        for i in items:
            print i,

    def q_get(self, q):
        items = self.r.lrange(q, 0, -1)
        indexes = []
        for i in items:
            indexes.append(i)
        return indexes

    def q_delete(self, q):
        ret = self.r.delete(q)
        return ret

    def dict_update(self, k,dict_key, dict_value):
        key_value = self.r.get(k)
        if not key_value:
            key_value = {"key": k}
        else:
            key_value = json.loads(key_value)
        key_value[dict_key] = dict_value
        ret = self.r.set(k, json.dumps(key_value))
        return ret

    def dict_get(self, k):
        key_value = self.r.get(k)
        key_value = {} if not key_value else json.loads(key_value)
        return key_value

    def dict_del(self, k):
        ret = self.r.delete(k)
        return ret

