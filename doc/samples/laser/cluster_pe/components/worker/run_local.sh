#!/bin/bash

set -e

function usage {
    echo "Run Worker container locally."
    echo "Usage: $0 -t tag"
    echo "    tag : Docker image tag"
}

tag=""

# Optional arguments
OPTIND=1
while getopts "t:h:" opt; do
	case $opt in
		t)
			tag=$OPTARG
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

amqp-declare-queue -u amqp://localhost:5672 -q myqueue

# Note that 172.17.42.1 is the host running the container (i.e. our 
# "localhost")
docker run -i -t -v "/tmp:/tmp" "$tag" bash -c \
	"/usr/local/bin/cluster_worker.sh -u amqp://172.17.42.1:5672 -q pe /usr/local/bin/pe_action.py"

exit 0
