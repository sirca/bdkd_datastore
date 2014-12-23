#!/bin/bash

# Submit all lines in a file to a queue.

function usage {
	echo "Submit all lines in file to the cluster queue."
	echo ""
	echo "Usage: $0 [[-m host:port -a appname] | [-u url]] -i input_file -q queue"
	echo "    host:port  : Marathon REST API endpoint for discovery"
	echo "    appname    : Marathon AMQP application name (e.g. 'amqp')"
	echo "                 (default: no discovery, local queue)"
	echo "    url        : Connect to specific AMQP URL"
	echo "    input_file : text file with one task per line"
	echo "    queue      : Name of AMQP queue for messages"
	echo ""
	echo "The default AMQP broker is local (i.e. 'amqp://localhost:5672')."
	echo "Alternatively either a specific broker can be specified (-u), or"
	echo "it can be discovered via a Marathon host:port (-m) and app name (-a)."
}

set -e

host_port=""
appname=""
url=""
queue=""
input_file=""
amqp="amqp://localhost:5672"

OPTIND=1
while getopts "m:a:u:i:q:h:" opt; do
	case $opt in
		m)
			host_port=$OPTARG
			;;
		a)
			appname=$OPTARG
			;;
		u)
			url=$OPTARG
			;;
		i)
			input_file=$OPTARG
			;;
		q)
			queue=$OPTARG
			;;
		h)
			usage ; exit 0
			;;
		\?)
			echo "Invalid option -$OPTARG" >&2
			usage ; exit 1
	esac
done


if [ -z "$input_file" -o ! -e "$input_file" ]; then
	echo "Need to specify input file" >&2
	usage ; exit 1
fi

if [ -z "$queue" ]; then
	echo "Need to specify queue name" >&2
	usage ; exit 1
fi

if [ ! -z "$url" ]; then
	amqp="$url"
else
	if [ ! -z "$host_port" -a ! -z "$appname"  ]; then
		amqp="amqp://$( scripts/marathon_app_hostport --host $host_port --app $appname )"
	fi
fi

# Before publishing ensure queue exists
amqp-declare-queue -u "$amqp" -q "$queue"

while read task_body; do
	echo -e "$task_body" | amqp-publish -u $amqp -r $queue
done < "$input_file"

