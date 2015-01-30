# Create a Docker container for running a Worker.

FROM ubuntu:14.04

# Updates

RUN apt-get -y update && apt-get -y upgrade

# Install prerequisites

RUN apt-get -y install amqp-tools python r-base

# Copy scripts

COPY scripts /usr/local/bin
