#!/bin/bash

# Run the Worker component locally.

# A Docker container implementing a Worker will be run locally.  It is assumed 
# that a Queue is also running locally, from which the Worker will consume 
# messages.

set -e

function usage {
    echo "Run Worker container locally."
    echo "Usage: $0 -t tag -q queue"
    echo "    tag   : Docker image tag"
    echo "    queue : Name of AMQP queue for messages"
}

tag=""
queue=""

# Optional arguments
OPTIND=1
while getopts "t:q:h:" opt; do
	case $opt in
		t)
			tag=$OPTARG
			;;
		q)
			queue=$OPTARG
			;;
		h)
			usage ; exit 0
			;;
		\?)
			echo "Invalid option: -$OPTARG" >&2
			usage ; exit 1
			;;
	esac
done

if [ -z "$tag" ]; then
	echo "Docker tag not specified" >&2
	usage ; exit 1
fi

if [ -z "$queue" ]; then
	echo "Queue name not specified" >&2
	usage ; exit 1
fi

amqp-declare-queue -u amqp://localhost:5672 -q "$queue"

# Note that 172.17.42.1 is the host running the container (i.e. our 
# "localhost")
docker run -i -t -v "/tmp:/tmp" "$tag" bash -c \
	"/usr/local/bin/cluster_worker.sh -u amqp://172.17.42.1:5672 -q $queue /usr/local/bin/myaction.r"

exit 0
