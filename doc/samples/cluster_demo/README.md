Sample cluster application: worker and queue
============================================

This code sample illustrates a trivial sample application consisting of a work 
queue and workers.  When messages are placed into the queue, the workers 
consume those messages, passing them to a custom user script.

This sample application is similar to what could be used to parallelise a large 
amount of computation work on a cluster.


Structure
---------

The project consists of two components -- "queue" and "worker" -- each of which 
can be built to a Docker image and deployed to a private Docker registry.

    components/
        queue/
	    Dockerfile
	worker/
	    scripts/
	    Dockerfile

In the case of the "worker" this includes a scripts/ directory.  These scripts 
are copied to the worker and can be used to consume messages from an AMQP 
queue.


Implementation
--------------

RabbitMQ provides the implementation of an AMQP message broker.  Queue 
interaction is done with the utilities provided by amqp\_tools.  These tools 
allow messages to be published to a queue and consumed using the command-line.

A script is provided to perform a primitive form of service discovery using 
Marathon's REST API.  Workers use this to look up the host:port where the queue 
is running.

The actual behaviour of the worker is provided by the `myaction.r` script, 
which is a trivial program that writes files to /tmp.  For a real system, this 
script would be replaced by a more useful program.


Usage
-----

Each component has three control scripts available:

 - `build.sh`: Build a Docker image and push it to the private registry.
 - `deploy.sh`: Deploy a previously-built image to the compute cluster.
 - `run_local.sh`: Run the component on localhost.

`run_local.sh` enables a user to test the functionality of the images before 
deploying to a cluster.  In each case the component is run inside a container 
on localhost -- just as they would run on a cluster.  It is expected that a 
user could run the queue component locally first before running the worker.

To make the system do work, publish messages to the AMQP queue.  These will be 
consumed by the next available worker as-is (i.e. the message body content will 
be directed to the processing script's STDIN).

### Queue

`cd` to the queue directory and use `build.sh` to build a Docker image 
implementing the queue.  Provide a tagname (-t) for the image, e.g.:

    ./build.sh -t amqp:v1

To run a local instance of the queue (localhost) use `run_local.sh`, providing 
the tag name of a previously-built image e.g.:

    ./run_local.sh -t amqp:v1

(At this point the user might also want to run a local worker to test the 
system before deployment.  See below for more details.)

To deploy to the cluster use the `deploy.sh` script, providing the host:port 
where Marathon is running and the tag name of a previously-built image e.g.:

    ./deploy.sh -m 10.0.0.10:8080 -t amqp:v1

### Worker

`cd` to the queue directory and use `build.sh` to build a Docker image 
implementing the worker.  Provide a tagname (-t) for the image, e.g.:

    ./build.sh -t worker:v1

To run a local instance of the worker (localhost) use `run_local.sh`, providing 
the tag name of a previously-built image, and the name of a queue to use e.g.:

    ./run_local.sh -t worker:v1 -q myqueue

This will launch a worker that will try to connect to a local queue (see above) 
and consume messages.

To deploy to the cluster use the `deploy.sh` script, providing the host:port 
where Marathon is running, the tag name of a previously-built image, and the 
name of the queue to use e.g.:

    ./deploy.sh -m 10.0.0.10:8080 -t amqp:v1 -q myqueue

The user can interact with the queue using the standard AMQP tools.  For 
example, to send a message to a local queue the user could use a command such 
as this:

    amqp-publish -u amqp://localhost -r myqueue -b 'This is a test message'

To send messages to the cluster queue, we can make use of the same 
introspection script that the cluster worker uses to find the AMQP queue, e.g.

    amqp-publish -u amqp://$( ./scripts/marathon_app_hostport --host 10.0.0.10:8080 --app amqp ) -r myqueue -b 'This is a test message'

The command above uses the `marathon_app_hostport` script to find where the 
queue is running by consulting the Marathon REST API at 10.0.0.10:8080, looking 
for an application called "amqp".  (Note that the queue is not running on 
10.0.0.10:8080 -- it's running somewhere in the cluster.  We are using Marathon 
to find it.)


Customising worker actions
--------------------------

The action peformed by the worker is defined in the `worker-app.json` file.  In 
this example it is a R script called `myaction.r`.  The relevant section of 
`worker-app.json` is below:

    "cmd": "/usr/local/bin/cluster_worker.sh -m {{HOST_PORT}} -a amqp -q {{QUEUE}} /usr/local/bin/myaction.r"

Features of a worker action script:

 * It reads the body of messages from STDIN
 * It exits with 0 on success, non-0 on failure (standard for shell commands)

So customising the action of the worker is straightforward: simply provide a 
different action script/program that reads from STDIN, does some work and exits 
0.
