import redis
import time
import os

from simple_queue import redis_queue

REDIS_HOST=os.environ["REDIS_HOST"]
REDIS_PORT=6379
rq = redis_queue(redis_host = REDIS_HOST, redis_port=REDIS_PORT)

print "Qeue:"
wip_simulations = rq.q_get("queue")
for i in wip_simulations:
    item=rq.dict_get(i)
    print "{0} -> Params: p1={1}, p2={2}, traits={3} ...".format(
        i, item.get("p1"), item.get("p2"), item.get("traits")[:20])
    

print "WIP:"
wip_simulations = rq.q_get("wip")
for i in wip_simulations:
    item=rq.dict_get(i)
    print "{0} -> Params: p1={1}, p2={2}, traits={3} ... -> Server: {4}, ProcessId: {5}".format(
        i, item.get("p1"), item.get("p2"), item.get("traits")[:20], item.get("host"), item.get("pid"))

