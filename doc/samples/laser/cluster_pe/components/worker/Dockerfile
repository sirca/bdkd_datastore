# Create a Docker container with RabbitMQ

FROM ubuntu:14.04

# Updates

RUN apt-get -y update && apt-get -y upgrade

# Install prerequisites

RUN apt-get -y install amqp-tools hdf5-tools python python-h5py python-numpy s3cmd

# Copy scripts

COPY scripts /usr/local/bin

# Copy config files to home directory

COPY home /root
