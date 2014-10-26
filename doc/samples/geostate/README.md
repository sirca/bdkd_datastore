Running Geostate on a compute cluster
=====================================

This document details how to run Geostate on a compute cluster using Mesos, Marathon and Docker.

The objective is to enable Geostate to be built away from the compute cluster and run without having to be installed in the cluster node images.


Build Geostate
--------------

Geostate can be built in an environment with Docker installed using the
provided Dockerfile.

Assumptions: that a Docker project directory is present with the checked-out
sources for Stateline and Geostate along with the Dockerfile, like so:

    build_dir/
        geostate/
        stateline/
        Dockerfile

The Docker build can be run and the resulting image tagged something like this, e.g.:

    cd build_dir/
    docker build -t geostate .


Push the Geostate image to a registry
-------------------------------------

Having a private Docker registry makes it convenient to ship images between
machines.  The image generated above could be added to a Docker registry like
this, e.g.:

    docker tag geostate 10.0.10.10:5000/geostate
    docker push 10.0.10.10:5000/geostate


Running the Geostate delegator
------------------------------

A delegator process can be run on a host with the following features:

* Docker is installed
* Access to the private registry where the image is stored
* Hosts in the compute cluster can communicate with the machine (so workers can do work for the delegator)

The delegator can be run as follows, e.g.:

    docker run -i -t -p 5555:5555 10.0.10.10:5000/geostate bash -c 'python /opt/geostate/tectonic/runfiniterotations.py'

This exposes port 5555 from the container back to the host machine.  You will
want to make a note of the host IP address and use it in the Marathon app (see
below).


Running Geostate workers on a cluster
-------------------------------------

Geostate workers can be run in a cluster by creating an app in Marathon.  The
included file "marathon-sample.json" is an example of an app definition.  You
would POST this to your Marathon service like this, e.g.:

    curl -X POST -H "Content-Type: application/json" http://10.0.0.20:8080/v2/apps -d@marathon-sample.json

