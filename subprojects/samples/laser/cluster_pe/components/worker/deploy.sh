#!/bin/bash

set -e

function usage {
    echo "Deploy Worker application to cluster."
    echo "Usage: $0 -m host:port -t tag -q queue"
    echo "    host:port : Marathon REST API endpoint for discovery"
    echo "    tag       : Docker image tag"
    echo "    queue     : Name of AMQP queue for messages"
}

host_port=""
tag=""
queue=""

# Optional arguments
OPTIND=1
while getopts "m:t:q:h:" opt; do
	case $opt in
		m)
			host_port=$OPTARG
			;;
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

if [ -z "$host_port" ]; then
	echo "Marathon host:port not specified" >&2
	usage ; exit 1
fi

if [ -z "$tag" ]; then
	echo "Docker tag not specified" >&2
	usage ; exit 1
fi

if [ -z "$queue" ]; then
	echo "Queue name not specified" >&2
	usage ; exit 1
fi

sed "s/{{TAGNAME}}/$tag/" worker-app.json | \
	sed "s/{{HOST_PORT}}/$host_port/" | \
	sed "s/{{QUEUE}}/$queue/"         | \
	curl -X POST -H "Content-Type: application/json" "http://$host_port/v2/apps" -d@-
