# BDKD Datastore-Wrapper

Python library that allows programmatic access to some of the features of the [BDKD-datastore](../../datastore/README.md).

It assumes that the [BDKD-datastore](../../datastore/README.md) package is installed and available.

Requires Python 2.7.

The latest release is 0.1.7.

Currently under passive development.


## About

BDKD Datastore-Wrapper is being developed by [SIRCA](http://www.sirca.org.au/) as part of the Big Data Knowledge Discovery (BDKD) project funded by [SIEF](http://www.sief.org.au).


## Install

Check out the BDKD Datastore-Wrapper source and install from source.

It is best done in a Python [virtualenv](https://virtualenv.pypa.io/en/latest/).


    git clone https://<username>@github.com/sirca/bdkd_datastore.git
    cd datastore-wrapper/python
    python setup.py develop


Example code:

```python
import datastorewrapper

datastorewrapper.configure_datastore(my_config)
datastore = datastorewrapper.Datastore()

repos = datastore.list('my-repo')

print "\n".join(repos)
```

# Documentation

The wrapper uses [Sphinx](http://sphinx-doc.org/) to generate documentation. 

To generate HTML documentation, install Sphinx and do the following:

```
$ cd doc
$ make html
```
HTML documentation will be created under `doc/_build`


# Licensing
BDKD Datastore-Wrapper is available under the Apache License (2.0). See the LICENSE.md file.

Copyright NICTA 2015.

