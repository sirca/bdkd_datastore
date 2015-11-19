#!/bin/bash

# Deploy the Queue component to the cluster.

# This script will connect to the provided Marathon host:port location to 
# create the application.  The provided tag name will be filled into the 
# Marathon .json application specification.  This would be a tag that was 
# previously built with the build.sh script.

set -e

function usage {
    echo "Deploy Queue application to cluster."
    echo "Usage: $0 -m host:port -t tag"
    echo "    host:port : Marathon REST API endpoint for discovery"
    echo "    tag       : Docker image tag"
}

host_port=""
tag=""

# Optional arguments
OPTIND=1
while getopts "m:t:h:" opt; do
	case $opt in
		m)
			host_port=$OPTARG
			;;
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

# Remove optional arguments
shift $(($OPTIND - 1))

if [ -z "$host_port" ]; then
	echo "Marathon host:port not specified" >&2
	usage ; exit 1
fi


if [ -z "$tag" ]; then
	echo "Docker tag not specified" >&2
	usage ; exit 1
fi


sed "s/{{TAGNAME}}/$tag/" queue-app.json | \
	curl -X POST -H "Content-Type: application/json" "http://$host_port/v2/apps" -d@-
