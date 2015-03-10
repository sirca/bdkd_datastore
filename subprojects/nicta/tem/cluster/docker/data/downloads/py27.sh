#!/bin/bash
 
# Source: http://toomuchdata.com/2012/06/25/how-to-install-python-2-7-3-on-centos-6-2/
mkdir -p ~/src
cd ~/src
wget http://www.python.org/ftp/python/2.7.3/Python-2.7.3.tar.bz2
tar xf Python-2.7.3.tar.bz2 
cd Python-2.7.3
./configure --prefix=/usr/local
make && make altinstall

# Virtualenv
cd ~/src
set -o vi
wget http://pypi.python.org/packages/source/d/distribute/distribute-0.6.27.tar.gz  --no-check-certificate
tar xf distribute-0.6.27.tar.gz
cd distribute-0.6.27
python2.7 setup.py install
easy_install-2.7 virtualenv

mkdir ~/virtualenvs
cd ~/virtualenvs
virtualenv py2.7 --python=/usr/bin/python2.7
