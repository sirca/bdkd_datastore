#!/bin/sh
docker run -v /home:/home \
           -e "REDIS_HOST=`awk '/master/{print $1;}' /etc/hosts`" \
          localhost:5000/bdkd:tree_v5 bash \
           -c "/home/data/src/tree.assembly/scripts/simulate_parallel.sh"
