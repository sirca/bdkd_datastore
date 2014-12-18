#!/bin/bash

# Build a Docker image, tag it with the provided tag name and push it to the 
# private registry.

set -e

function usage {
    echo "Build and tag Queue image."
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

docker build -t "$tag" ./
docker tag "$tag" "localhost:5000/$tag"
docker push "localhost:5000/$tag"
