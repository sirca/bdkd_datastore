#!/bin/bash

set -e

function usage {
    echo "Run Queue container locally."
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

docker run -d -p 5672:5672 "$tag" /usr/sbin/rabbitmq-server
