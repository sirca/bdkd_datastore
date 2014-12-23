#!/bin/bash

# Script that creates PE calculation tasks for an entire dataset stored in a S3 
# bucket.

# If a URL for an AMQP broker and a queue name are provided then each PE task 
# will be sent to that queue.

set -e

function usage {
	echo "Create PE calculation tasks."
	echo "Usage: $0 -m order -t delay -i input_prefix -o output_prefix"
	echo "    order        : PE order"
	echo "    delay        : PE delay"
	echo "    input_prefix : S3 object name prefix for input raw files"
	echo "    output_path  : Output path for JSON results file"
}

order=""
delay=""
input_prefix=""
output_path=""

OPTIND=1
while getopts "m:t:i:o:h:" opt; do
	case $opt in
		m)
			order=$OPTARG
			;;
		t)
			delay=$OPTARG
			;;
		i)
			input_prefix=$OPTARG
			;;
		o)
			output_path=$OPTARG
			;;
		h)
			usage ; exit 0
			;;
		\?)
			echo "Invalid option -$OPTARG" >&2
			usage ; exit 1
	esac
done

if [ -z "$order" -o -z "$delay" -o -z "$input_prefix" -o -z "$output_path" ]; then
	usage ; exit 1
fi

s3cmd ls "$input_prefix" | tr -s ' ' | cut -d ' ' -f 4- | while read in_path; do
	fn=$(echo $in_path | rev | cut -d/ -f 1 | rev)
	body="$order\t$delay\t$in_path\t$output_path/${fn}-pe.txt"
	echo -e "$body" 
done
