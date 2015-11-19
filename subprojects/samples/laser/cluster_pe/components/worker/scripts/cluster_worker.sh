#!/bin/bash

set -e

function usage {
    echo "Execute a worker application that consumes queue messages."
    echo "Usage: $0 [[-m host:port -a appname] | [-u url]] -q queue command [options]"
    echo "    host:port : Marathon REST API endpoint for discovery"
    echo "    appname   : Marathon AMQP application name (e.g. 'amqp')"
    echo "                (default: no discovery, local queue)"
    echo "    url       : Connect to specific AMQP URL"
    echo "    queue     : Name of AMQP queue for messages"
    echo "    command   : Shell command for worker to execute"
    echo "    options   : Options for shell command"
}

host_port=""
appname=""
url=""
queue=""
cmd=""
options=""
amqp="amqp://localhost:5672"

# Optional arguments
OPTIND=1
while getopts "m:a:u:q:h:" opt; do
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

# Remove optional arguments
shift $(($OPTIND - 1))

cmd="$1" ; shift
options="$@"

if [ -z "$queue" -o -z "$cmd" ]; then
	usage ; exit 1
fi

if [ ! -z "$url" ]; then
	amqp="$url"
else
	if [ ! -z "$host_port" -a ! -z "$appname"  ]; then
		amqp="amqp://$( marathon_app_hostport --host $host_port --app $appname )"
	fi
fi

echo "AMQP: $amqp"
echo "Queue: $queue"
echo "Command: $cmd"
echo "Options: $options"

# Before consuming ensure queue exists
amqp-declare-queue -u "$amqp" -q "$queue"

# Start consuming
amqp-consume -u "$amqp" -q "$queue" $cmd "$options"

exit 0
