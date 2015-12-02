FROM centos:centos6

MAINTAINER Lolo Fernandez "lolo.fernandez@sirca.org.au"

RUN yum install -y epel-release
RUN yum install -y wget tar curl lynx telnet bzip2 git python-pip

RUN wget https://3230d63b5fc54e62148e-c95ac804525aac4b6dba79b00b39d1d3.ssl.cf1.rackcdn.com/Anaconda-2.2.0-Linux-x86_64.sh ;\
    /bin/bash Anaconda-2.2.0-Linux-x86_64.sh -b -p /root/anaconda ;\
    /root/anaconda/bin/conda create -y -n py27 python=2.7 anaconda
