Cluster application: laser permutation entropy
==============================================

Calculate permutation entropy for laser datasets on a compute cluster, for
various combinations of order and delay.

This code is based on the work of Dr Josh Toomey of Macquarie University.  It
contains a port of his MatLab code to calculate permutation entropy for laser
data, which is based on Shannon's permutation entropy algorigthm.

The expected input data consists of laser datasets, sharded into multiple HDF5
files read from S3.  Each cluster task involves reading the timeseries from a
shard file and calculating permutation entropies.  These are then written back
to a S3 results bucket, for subsequent combination back into a single result
set.


Structure
---------

This project is structured as a simple queue and workers model.  The user 
pushes all calculation tasks into a queue.  Workers running in the cluster 
consume these tasks, fetch raw data from S3, calculate results and put those 
results back into S3.  Also included is a helper script that can reduce the 
results.

The "worker" and "queue" components can be built into Docker containers and 
pushed to a private registry.

    components/
        queue/
	    Dockerfile
	worker/
	    home/
	    local_scripts/
	    scripts/
	    Dockerfile

The "queue" component is a simple AMQP messaging service running in a Docker 
container.

The "worker" consists of some installed scripts (in "scripts") and some local 
helper scripts (in "local\_scripts") to manage the process of submitting work.  
There is also a "home" directory -- this is used to put files into the 
container user's home directory (i.e. the appropriate ".s3cfg" file for use by 
`s3cmd`).  Usage is described in detail below.


Implementation
--------------

RabbitMQ provides the implementation of an AMQP message broker.  Queue 
interaction is done with the utilities provided by amqp\_tools.  These tools 
allow messages to be published to a queue and consumed using the command-line.

A script is provided to perform a primitive form of service discovery using 
Marathon's REST API.  Workers use this to look up the host:port where the queue 
is running.

The behaviour of the worker is implemented in the `pe_action.py` script, which 
is run by the worker.  This performs calculations in a number of steps:

 - Fetch the input raw data from S3 (if not fetched already)
 - Calculate permutation entropies for each timeseries
 - Write the results back to a different bucket.

The input to the action script is a tab-delimited line of parameters, 
containing:

 - Order (integer)
 - Delay (integer)
 - Source file to be read
 - Destination file to be written

The format of the destination file is comma-delimited text -- one line per 
permutation entropy calculation containing:

 - x index of timeseries (integer)
 - y index of timeseries (integer)
 - permuation entropy of timeseries (float)

A helper script called `pe_reduce.py` is also provided, which reduces a 
bucket/path full of result files into a single 2D matrix and appends it to a 
HDF5 file.


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

These instructions describe how to build and run the worker process -- a task
that performs PE calculations.


#### Preparation

For this setup we are using the `s3cmd` tool from within containers to interact
with S3.  For this to work, a valid .s3cfg configuration file needs to be
provided.  If you have `s3cmd` installed you can configure it with the
"--configure" option:

    s3cmd --configure

Follow the prompts, including providing an AWS access key and secret key.  You
should test that the credentials you have set have at least read-access to the
source S3 data and write access to the bucket where you want to store results.

Once you have a valid ".s3cfg" file place it in the worker's home/ directory.
When the worker image is built the files in home/ will be added.


#### Build and deploy

`cd` to the queue directory and use `build.sh` to build a Docker image 
implementing the worker.  Provide a tagname (-t) for the image, e.g.:

    ./build.sh -t pe:v1

To run a local instance of the worker (localhost) use `run_local.sh`, providing 
the tag name of a previously-built image, and the name of a queue to use e.g.:

    ./run_local.sh -t pe:v1 -q pe

This will launch a worker that will try to connect to a local queue (see above) 
and consume messages.

To deploy to the cluster use the `deploy.sh` script, providing the host:port 
where Marathon is running, the tag name of a previously-built image, and the 
name of the queue to use e.g.:

    ./deploy.sh -m 10.0.0.10:8080 -t pe:v1 -q pe


#### Performing calculations

There is a helper script `pe_tasks.sh` provided that takes as its input a
leading path and outputs a series of task lines that are in the right format to
be queued.  For example -- say that you had a set of shard files in a S3 bucket
starting with 's3://bdkd-laser-public/files/Optically
Injected/Experimental/raw\_shard', and you wanted to calculate permutation
entropy for order (-m) of 6, delay (-t) of 2.  We want the output (-o) results
written to a particular bucket/path.  The following command would generate all
the required tasks and output the list to a file "tasks-m06t02.txt":

    local_scripts/pe_tasks.sh -m6 -t2 -i 's3://bdkd-laser-public/files/Optically Injected/Experimental/raw_shard' -o 's3://bdkd-laser-tmp/results/m06t02' > tasks-m06t02.txt

If this is satisfactory the next step is to submit all these tasks to the
cluster.  There is a helper script for this called `submit_file.sh`.  This
script reads a text file as its input and sends each line to a queue.  For
example:

    local_scripts/submit_file.sh -i tasks-m06t02.txt -m 10.0.0.10:8080 -a amqp -q pe 

In this case, the input file (-i) is the list of tasks we generated previously.
The Marathon endpoint (-m) and application name (-a) options are used to
discover where the AMQP broker is running in the cluster.  (Note that
10.0.0.10:8080 is the host:port of Marathon -- not the message broker.)  We are
putting all the tasks into a queue (-q) called "pe".


#### Reducing results

After all the calculations are performed, all the results should be present as
text files (\*.txt) in the output path.  The next step is to "reduce" those
results back into a single 2D matrix and to append those results to a HDF5
file.  There is a helper script called `pe_reduce.py` provided for this.

Note that the reduce script is in the "scripts/" directory: it is installed
into the worker Docker image.  This is because the worker Docker image already
has all the required tools and libraries required to run it.  So we will do the
reduction step inside a Docker container.

Although we do the reduction from within a container, we want the results to be
kept *outside* the container so that we can use them (e.g. publish them
online).  For instance we might keep the final results in a file
/var/tmp/maps.hdf5 while we're working.  We can run the container as follows:

    docker run -it -v '/var/tmp:/var/tmp' pe:v1 /bin/bash

From within the container we can reduce a set of results and append it to a
maps file as follows:

    pe_reduce.py --results 's3://bdkd-laser-tmp/results/m06t02' --order 6 --delay 2 --tmpdir /tmp --outfile /var/tmp/maps.hdf5

This can be done multiple times to build up a set of PE maps inside the output
file.
