import tree
import redis
import time
import socket
import os
from simple_queue import redis_queue
import logging

REDIS_HOST=os.environ["REDIS_HOST"]
REDIS_PORT=6379
rq = redis_queue(redis_host = REDIS_HOST, redis_port=REDIS_PORT)

# This is the job that simulates a particular forest
# NOTE: characteristic contains log(TD) and B4, so this needs to be scaled properly before we pass it to the simulator
# When we get the fitness, we need to log it again since our model is using log(fitness)
def wait_for_simulations():
    while True:
        if rq.q_len("queue") > 0 :
            # Get job
            i = rq.q_move("queue", "wip")
            if not i:
                time.sleep(5)
                continue

            item = rq.dict_get(i)
            p1 = item.get("p1")
            p2 = item.get("p2")
            traits = item.get("traits")
            virtualIndex = item.get("virtualIndex")

            # Update status
            rq.dict_update(i,"status","wip")
            rq.dict_update(i,"host",socket.gethostname())
            rq.dict_update(i,"pid",str(os.getpid()))
            LOGGER.info("{0},simulation:{1},virtualIndex:{2},started".format(socket.gethostname(), i, virtualIndex))

            try:
                # Working
                forest = tree.TreeModel(p1, p2)
                forest.evolve(100)
                fitness = forest.fitness(traits)
                yActual=np.log(fitness)

                # Update results
                rq.dict_update(i,"yActual",yActual)
                rq.dict_update(i,"virtualIndex",virtualIndex)
                rq.dict_update(i,"status","done")
                LOGGER.info("{0},simulation:{1},virtualIndex:{2},finished,yActual:{3}".format(socket.gethostname(), i, virtualIndex, yActual))

            except ValueError:
                rq.dict_update(i,"status","fail")
                LOGGER.info("{0},simulation:{1},virtualIndex:{2},failed".format(socket.gethostname(), i, virtualIndex))

        time.sleep(5)

if __name__ == "__main__":
    log_filename = "/home/data/logs/tree.log"
    LOGGER = logging.getLogger()
    syslog_format = (' %(levelname)s ' + '%(filename)s: %(message)s')
    logging.basicConfig(
        level=logging.INFO,
        filename=log_filename,
        format='%(asctime)s.%(msecs)d localhost ' + syslog_format,
        datefmt='%Y-%m-%dT%H:%M:%S')

    wait_for_simulations()

