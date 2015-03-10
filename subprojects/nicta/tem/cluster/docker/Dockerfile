FROM fedora:latest

MAINTAINER Lolo Fernandez "lolo.fernandez@sirca.org.au"

RUN yum -y install git gsl

ADD data/downloads /downloads
RUN yum groupinstall -y "Development tools"
RUN yum install -y openssh-server openssh-devel zlib-devel bzip2-devel ncurses-devel wget curl tar tree which lynx telnet libcurl-devel
RUN yum install -y gcc-c++

# nlopt
RUN cd /downloads && \
    tar xzvf nlopt-2.4.2.tar.gz && \
    cd nlopt-2.4.2 && \
    ./configure --with-pic --enable-shared && \
    make install
    echo '/usr/local/lib' > /etc/ld.so.conf.d/nlopt.conf' && \
    source /sbin/ldconfig

# gls
RUN cd /downloads && \
    tar zxvf gsl-1.15.tar.gz && \
    cd gsl-1.15 && \
    ./configure && \
    make && \
    make install

# R
RUN yum install -y R
RUN R -e 'install.packages(c("Rcpp","R6","testthat","lhs","assertthat","numDeriv","deSolve","devtools","roxygen2","deldir","RcppArmadillo","digest"), repos="http://cran.csiro.au/", dependencies=TRUE)'

# Python
RUN yum install -y python-devel readline-devel
RUN /downloads/py27.sh

# Source code
ADD data/src /data/src

# Compile
RUN source /data/src/compile.sh

# Python requirements
RUN source ~/virtualenvs/py2.7/bin/activate && \
    pip install rpy2
